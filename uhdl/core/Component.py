import os, inspect, re, contextlib
from operator           import concat
from functools          import reduce
from collections.abc    import Iterable
from .Terminal          import Terminal
from .Root              import Root
from .Variable          import Mem,Wire,IOSig,IOGroup,Variable,Parameter,Reg,Output,Input,Inout,InputStructIO,OutputStructIO,InputEnumIO,OutputEnumIO,InputUnionIO,OutputUnionIO
from .Variable          import Constant, UInt
from .UHDLException     import ErrUHDLStr
from .                  import FileProcess
from .                  import SrcLoc

from .CustConfig        import ComponentConfig


UHDL_GLOBAL_PARAM_DICT = {}

class PARAM_CONTAINER(object): 

    def _caculate_name(self):
        self.UHDL_MODU_NAME_POST_FIX = self.__caculate_iterable_kv(self.__dict__)
        self.UHDL_MODU_NAME_POST_FIX = self.UHDL_MODU_NAME_POST_FIX[2:-2]

    def __caculate_iterable_kv(self,iterable_param):
        res = 'S'
        for k,v in iterable_param.items():
            # Expand values into a stable token string without Python reprs
            if isinstance(v, (int, float, bool, str)):
                res += '_%s_%s' % (k, v)
            elif isinstance(v, dict):
                # recursively expand nested dicts
                res += '_%s_%s' % (k, self.__caculate_iterable_kv(v))
            elif isinstance(v, Iterable):
                # expand lists/tuples/sets, etc.
                res += '_%s_%s' % (k, self.__caculate_iterable_varg(v))
            else:
                # fallback to a stable type token
                ID = id(v)
                if ID in UHDL_GLOBAL_PARAM_DICT:
                    seq = UHDL_GLOBAL_PARAM_DICT[ID]
                    UHDL_GLOBAL_PARAM_DICT[ID] = seq + 1
                else:
                    seq = 0
                    UHDL_GLOBAL_PARAM_DICT[ID] = 0
                res += '_%s_%s%s' % (k, type(v).__name__, str(seq))
        res = res + '_E'
        return res

    def __caculate_iterable_varg(self,iterable_param):
        res = 'S'
        for item in iterable_param:
            if    isinstance(item,(int,float,bool,str,)):
                res = res + '_' + str(item)
            elif  isinstance(item,(dict,)):
                res = res + '_%s' % self.__caculate_iterable_kv(item)
            elif  isinstance(item,Iterable): 
                res = res + '_%s' % self.__caculate_iterable_varg(item)
            else:
                ID = id(item)
                if ID in UHDL_GLOBAL_PARAM_DICT:
                    seq = UHDL_GLOBAL_PARAM_DICT[ID]
                    UHDL_GLOBAL_PARAM_DICT[ID] = seq + 1
                else:
                    seq = 0
                    UHDL_GLOBAL_PARAM_DICT[ID] = 0
                res = res + '_' + type(item).__name__ + str(seq)
        res = res + '_E'
        return res



def _ranges(bits):
    out, i = [], 0
    while i < len(bits):
        j = i
        while j + 1 < len(bits) and bits[j + 1] == bits[j] + 1:
            j += 1
        out.append(str(bits[i]) if i == j else '%d..%d' % (bits[i], bits[j]))
        i = j + 1
    return ', '.join(out)


def _width_of(w):
    return w.width if hasattr(w, 'fields') and hasattr(w, 'width') else w


class _Fsm:
    def __init__(self, comp, name, states, init):
        if len(set(states)) != len(states) or not states:
            raise ErrUHDLStr('fsm %s: states must be a non-empty list of distinct names.' % name)
        self.comp, self.states = comp, states
        self.code = {n: i for i, n in enumerate(states)}
        w = max(1, (len(states) - 1).bit_length())
        self.reg = comp.reg(name, w, init=self.code[init if init is not None else states[0]])

    def _c(self, n):
        if n not in self.code:
            raise ErrUHDLStr('fsm has no state "%s"; states are %s.' % (n, ', '.join(self.states)))
        return self.code[n]

    def is_(self, n):
        return self.reg.eq(self._c(n))

    def state(self, n):
        """`with fsm.state('IDLE'):` - the block applies while in that state."""
        return self.comp.when(self.is_(n))

    def goto(self, n):
        self.reg <<= self._c(n)


_HDL_KEYWORDS = frozenset('''alias always always_comb always_ff always_latch and assert assign assume automatic before begin bind bins binsof bit break buf bufif0 bufif1 byte case casex casez cell chandle checker class clocking cmos config const constraint context continue cover covergroup coverpoint cross deassign default defparam design disable dist do edge else end endcase endchecker endclass endclocking endconfig endfunction endgenerate endgroup endinterface endmodule endpackage endprimitive endprogram endproperty endspecify endsequence endtable endtask enum event eventually expect export extends extern final first_match for force foreach forever fork forkjoin function generate genvar global highz0 highz1 if iff ifnone ignore_bins illegal_bins implements implies import incdir include initial inout input inside instance int integer interconnect interface intersect join join_any join_none large let liblist library local localparam logic longint macromodule matches medium modport module nand negedge nettype new nexttime nmos nor noshowcancelled not notif0 notif1 null or output package packed parameter pmos posedge primitive priority program property protected pull0 pull1 pulldown pullup pulsestyle_ondetect pulsestyle_onevent pure rand randc randcase randsequence rcmos real realtime ref reg reject_on release repeat restrict return rnmos rpmos rtran rtranif0 rtranif1 s_always s_eventually s_nexttime s_until s_until_with scalared sequence shortint shortreal showcancelled signed small soft solve specify specparam static string strong strong0 strong1 struct super supply0 supply1 sync_accept_on sync_reject_on table tagged task this throughout time timeprecision timeunit tran tranif0 tranif1 tri tri0 tri1 triand trior trireg type typedef union unique unique0 unsigned until until_with untyped use uwire var vectored virtual void wait wait_order wand weak weak0 weak1 while wildcard wire with within wor xnor xor'''.split())


class Component(Root):

    def __init__(self):
        super().__init__()
        #super(Component,self).__init__()
        self.set_father_type(Component)
        self.CFG                    = ComponentConfig()
        self.__vfile                = None
        self._PARAM                 = PARAM_CONTAINER()
        self.__subclass_init_param_get()
        self._lint                  = None
        self.output_dir             = '.'
        self._module_name_prefix    = ''
        self._module_name_override  = None
        self._unused_seq            = 0
        self._sub_instance_list     = []  # List to store all circuit instances belonging to this component
        self.circuit()
        self._uhdl_finalize()


    def circuit(self):
        pass


    @property
    def output_path(self):
        return '%s/%s' % (self.output_dir, self.module_name)

    def create(self, name, val):
        setattr(self, name, val)
        return getattr(self, name)

    # ------------------------------------------------------------------
    # Attaching to a parent: implicit clock/reset, connections given at construction
    # ------------------------------------------------------------------
    CLOCK_PORTS = (('clk', 'rst_n'),)

    def _setattr_hook(self):
        father = self.father
        if not isinstance(father, Component):
            return
        object.__setattr__(self, '_uhdl_attach_domain', father.__dict__.get('_uhdl_domain'))
        pend = self.__dict__.get('_uhdl_attach_connects')
        if pend:
            object.__setattr__(self, '_uhdl_attach_connects', [])
            for port, sig in pend:
                p = getattr(self, port)
                p += sig

    def _connect_on_attach(self, port, sig):
        '''Connect input `port` of this component to `sig` once it is placed in a parent.'''
        if sig is None:
            return
        self.__dict__.setdefault('_uhdl_attach_connects', []).append((port, sig))

    def _uhdl_finalize(self):
        '''Run after circuit(): implicit clocks, joined slice drivers, when-blocks.'''
        with SrcLoc.deferred():
            self._uhdl_finalize_body()

    def _uhdl_finalize_body(self):
        # 1. clock/reset of children that were left unconnected follow the domain active at attach time
        for child in self.component_list:
            dom = child.__dict__.get('_uhdl_attach_domain')
            for cname, rname in getattr(type(child), 'CLOCK_PORTS', ()):
                c, r = child.__dict__.get(cname), child.__dict__.get(rname)
                if not isinstance(c, Input):
                    continue
                c_open = c._rvalue is None
                r_open = isinstance(r, Input) and r._rvalue is None
                if isinstance(r, Input) and c_open != r_open:
                    raise ErrUHDLStr('%s: %s is connected but %s is not. Connect both, or neither to let '
                                     'them follow s.domain().' % (child.full_hier, rname if c_open else cname,
                                                                  cname if c_open else rname)).at(SrcLoc.decl(child))
                if c_open and dom:
                    c += dom[0]
                    if r_open:
                        if dom[1] is None:
                            raise ErrUHDLStr('%s.%s follows s.domain(), which has no reset.' % (child.full_hier, rname))
                        r += dom[1]
        # 2. signals driven slice by slice
        parts = self.__dict__.pop('_uhdl_parts', None)
        if parts:
            from .Operator import Combine
            for target, lst in parts.values():
                w = target.attribute.width
                lst = sorted(lst, key=lambda t: -t[1])
                bits = [0] * w
                locs = [loc for _, _, _, loc in lst]
                for h, l, _, _ in lst:
                    for b in range(l, h + 1):
                        bits[b] += 1
                over = [b for b in range(w) if bits[b] > 1]
                hole = [b for b in range(w) if bits[b] == 0]
                if over or hole:
                    raise ErrUHDLStr('%s is driven slice by slice, but %s.' % (target.full_hier, '; '.join(
                        x for x in ('bits %s are driven twice' % _ranges(over) if over else '',
                                    'bits %s are not driven' % _ranges(hole) if hole else '') if x))).at(
                        *locs, notes=[('declared', SrcLoc.decl(target))])
                vals = [v for _, _, v, _ in lst]
                with SrcLoc.assigned_at(locs), SrcLoc.errors_at(locs):
                    target += vals[0] if len(vals) == 1 else Combine(*vals)
        # 3. when-blocks
        blk = self.__dict__.pop('_uhdl_blk', None)
        if blk:
            if blk['stack']:
                raise ErrUHDLStr('A `with s.when(...)` block was not closed.')
            from .Variable import WhenExpression
            for target, recs in blk['records'].values():
                last_u = max((i for i, (c, _, _) in enumerate(recs) if c is None), default=None)
                default = recs[last_u][1] if last_u is not None else None
                conds = recs[last_u + 1:] if last_u is not None else recs
                used = ([recs[last_u][2]] if last_u is not None else []) + [loc for _, _, loc in conds]
                for _, v, l in recs:
                    a = getattr(v, 'attribute', None)
                    if a is not None and getattr(a, 'width', None) not in (None, target.attribute.width):
                        raise ErrUHDLStr('%s is %d bits but is assigned a %d-bit value with <<=.' % (
                            target.full_hier, target.attribute.width, a.width)).at(l, notes=[('declared', SrcLoc.decl(target))])
                if not conds:
                    with SrcLoc.assigned_at(used), SrcLoc.errors_at(used):
                        target += default
                    continue
                if default is None and not isinstance(target, Reg):
                    raise ErrUHDLStr('%s is only assigned inside when-blocks, so it would be a latch. Give it a '
                                     'default first: `%s <<= value` outside the blocks.' % (target.full_hier, target.name)
                                     ).at(*used, notes=[('declared', SrcLoc.decl(target))])
                with SrcLoc.errors_at(used):
                    ch = WhenExpression()
                    for c, v, _ in reversed(conds):         # the last assignment wins
                        ch.when(c).then(v)
                    if default is not None:
                        ch.otherwise(default)
                with SrcLoc.assigned_at(used), SrcLoc.errors_at(used):
                    target += ch

    def _add_part(self, target, h, l, value, loc=None):
        d = self.__dict__.setdefault('_uhdl_parts', {})
        d.setdefault(id(target), (target, []))[1].append((h, l, value, loc))

    # ------------------------------------------------------------------
    # when-blocks:  with s.when(c): a <<= x; b <<= y
    # ------------------------------------------------------------------
    def _blk(self):
        return self.__dict__.setdefault('_uhdl_blk', {'stack': [], 'last': {}, 'records': {}})

    def _blk_assign(self, target, value):
        b = self._blk()
        cond = b['stack'][-1] if b['stack'] else None
        if type(value).__name__ in ('StructView', '_FieldsView'):
            value = value.bits
        b['records'].setdefault(id(target), (target, []))[1].append((cond, value, SrcLoc.capture()))

    @contextlib.contextmanager
    def _blk_enter(self, kind, cond):
        from .Operator import Or
        b = self._blk()
        depth = len(b['stack'])
        prev = b['last'].get(depth)
        if kind != 'otherwise':
            if not hasattr(cond, 'attribute') or cond.attribute.width != 1:
                raise ErrUHDLStr('s.%s() needs a 1-bit condition.' % kind)
        if kind == 'when':
            chain, local = [cond], cond
        elif prev is None:
            raise ErrUHDLStr('s.%s() must directly follow a s.when()/s.elsewhen() block at the same level.' % kind)
        elif kind == 'elsewhen':
            chain, local = prev + [cond], cond & ~Or(*prev)
        else:
            chain, local = None, ~Or(*prev)
        total = local if depth == 0 else b['stack'][-1] & local
        for d in [d for d in b['last'] if d >= depth]:
            del b['last'][d]
        b['stack'].append(total)
        try:
            yield
        finally:
            b['stack'].pop()
            for d in [d for d in b['last'] if d > depth]:
                del b['last'][d]
            if chain is not None:
                b['last'][depth] = chain

    def when(self, cond):
        '''`with s.when(c):` - assignments with <<= inside apply when c is 1.'''
        return self._blk_enter('when', cond)

    def elsewhen(self, cond):
        return self._blk_enter('elsewhen', cond)

    def otherwise(self):
        return self._blk_enter('otherwise', None)

    def fsm(self, name, states, init=None):
        '''A state register with named states: fsm = s.fsm('st', ['IDLE', 'RUN']).
        Uses the current domain; resets to `init` (default: the first state).'''
        return _Fsm(self, name, list(states), init)

    # ------------------------------------------------------------------
    # Ports and streams with computed names
    # ------------------------------------------------------------------
    def input(self, name, width, domain=None):
        self._check_new_name(name)
        return self.create(name, Input(_width_of(width), domain=domain))

    def output(self, name, width, domain=None):
        self._check_new_name(name)
        return self.create(name, Output(_width_of(width), domain=domain))

    def _stream_ports(self, prefix, payload, fwd, bwd, domain, data='data'):
        from .Struct import Stream, Struct
        from collections import OrderedDict
        mk = lambda n, io, w: self.create(n, io(w, domain=domain) if io is not Wire else Wire(w))
        vld = mk(prefix + '_vld', fwd, 1)
        rdy = mk(prefix + '_rdy', bwd, 1)
        if isinstance(payload, Struct) and data is None:
            fields = OrderedDict((f, mk('%s_%s' % (prefix, f), fwd, payload.field_width(f))) for f in payload.fields)
            return Stream(vld, rdy, fields=fields, struct=payload)
        width = payload.width if isinstance(payload, Struct) else payload
        return Stream(vld, rdy, data=mk('%s_%s' % (prefix, data), fwd, width), struct=payload if isinstance(payload, Struct) else None)

    _PER_FIELD = object()

    def stream_in(self, prefix, payload, domain=None, data=_PER_FIELD):
        '''Input stream ports <prefix>_vld, <prefix>_rdy (out) and the payload. A Struct
        payload becomes one port per field (<prefix>_<field>) unless data='name' asks for
        one packed port <prefix>_<name>; an int payload is one port <prefix>_<data or "data">.'''
        return self._stream_ports(prefix, payload, Input, Output, domain, self._data_name(payload, data))

    def stream_out(self, prefix, payload, domain=None, data=_PER_FIELD):
        return self._stream_ports(prefix, payload, Output, Input, domain, self._data_name(payload, data))

    def stream_wire(self, prefix, payload, data=_PER_FIELD):
        return self._stream_ports(prefix, payload, Wire, Wire, None, self._data_name(payload, data))

    @staticmethod
    def _data_name(payload, data):
        from .Struct import Struct
        if data is Component._PER_FIELD:
            return None if isinstance(payload, Struct) else 'data'
        return data

    # ------------------------------------------------------------------
    # Compact declarations: name, type and driver in one call
    # ------------------------------------------------------------------
    _NO_ARG = object()

    def domain(self, clk, rst=None, **reg_opts):
        '''Set the default clock (and reset) for self.reg() / self.mem() below.
        reg_opts are passed to Reg: async_rst, rst_active_low, clk_active_neg.
        Call it again to switch domains for the declarations that follow.'''
        object.__setattr__(self, '_uhdl_domain', (clk, rst, dict(reg_opts)))
        return self

    def _domain_clk(self, what, clk):
        if clk is not None:
            return clk
        d = self.__dict__.get('_uhdl_domain')
        if d is None:
            raise ErrUHDLStr('%s: no clock given and no default clock; call self.domain(clk, rst_n) first, '
                             'or pass clk=.' % what)
        return d[0]

    def _check_new_name(self, name):
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            raise ErrUHDLStr('Invalid signal name %r.' % (name,))
        if name in self.__dict__:
            raise ErrUHDLStr('%s already has a member named "%s".' % (type(self).__name__, name))
        if name in _HDL_KEYWORDS:
            raise ErrUHDLStr('"%s" is a Verilog/SystemVerilog keyword and cannot be a signal name.' % name)

    def wire(self, name, expr, width=None):
        '''Declare a Wire, name it and drive it: w = self.wire('sum', a & b).
        The width comes from expr; pass width= when expr is a plain int or an
        int-only Mux/when chain.'''
        from .Variable import _lit, _known_attr, Wire
        self._check_new_name(name)
        if width is not None:
            expr = _lit(expr, UInt(width), 'wire %s' % name)
        attr = _known_attr(expr)
        if attr is None:
            raise ErrUHDLStr('wire "%s": cannot infer a width from %r; pass width=.' % (name, expr))
        if width is not None and attr.width != width:
            raise ErrUHDLStr('wire "%s": width=%d but the expression is %d bits.' % (name, width, attr.width))
        w = self.create(name, Wire(attr))
        w += expr
        return w

    def reg(self, name, width, init=0, clk=None, rst=_NO_ARG, **reg_opts):
        '''Declare a Reg on the default domain: r = self.reg('cnt', 4) (reset value 0).
        width may also be a constant template such as SInt(8, -1). Drive it with +=.'''
        from .Variable import Reg
        self._check_new_name(name)
        clk = self._domain_clk('reg "%s"' % name, clk)
        d = self.__dict__.get('_uhdl_domain')
        if rst is Component._NO_ARG:
            rst = d[1] if d is not None and d[0] is clk else None
        opts = dict(d[2]) if d is not None and d[0] is clk else {}
        opts.update(reg_opts)
        template = width if isinstance(width, Constant) else UInt(width, init)
        return self.create(name, Reg(template, clk, rst, **opts))

    def mem(self, name, width, depth, clk=None):
        '''Declare a Mem on the default clock: m = self.mem('ram', 8, 16).
        Write with m.write(en, addr, data); read with m[addr].'''
        from .Variable import Mem
        self._check_new_name(name)
        clk = self._domain_clk('mem "%s"' % name, clk)
        d = self.__dict__.get('_uhdl_domain')
        neg = bool(d and d[0] is clk and d[2].get('clk_active_neg', False))
        template = width if isinstance(width, Constant) else UInt(width)
        return self.create(name, Mem(template, depth, clk, clk_active_neg=neg))

    @property
    def PARAM(self):
        return self._PARAM

    def set_module_name_prefix(self, prefix):
        self._module_name_prefix = prefix

    @property
    def module_name_prefix(self):
        return self._module_name_prefix if self.father is None else self.father.module_name_prefix

    def set_module_name(self, name):
        '''Use exactly this module name instead of <Class>_<params>.
        A class can also set MODULE_NAME = 'name'. generate() raises an error
        if two different modules end up with the same name.'''
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', name):
            raise ValueError('Invalid Verilog module name: %r' % (name,))
        self._module_name_override = name
        return self

    @property
    def module_name(self):
        override = getattr(self, '_module_name_override', None) or getattr(type(self), 'MODULE_NAME', None)
        if override:
            prefix = self.module_name_prefix
            return '%s_%s' % (prefix, override) if prefix else override
        # This scheme attempts to unwrap any data type into a readable unique string, and form the instantiation name from this string
        return (self.module_name_prefix + '_' + type(self).__name__+'_'+self.PARAM.UHDL_MODU_NAME_POST_FIX).rstrip('_').lstrip('_')

    @property
    def vfile(self):
        return self.__vfile

    def get_io_list(self,iteration=False,has_self=True) -> list:
        #sub_list = [self.__dict__[k].get_io_list(iteration) for k in self.__dict__ if isinstance(self.__dict__[k],Component) and k != '_father'] if iteration else []
        sub_list = reduce(concat,[self.__dict__[k].get_io_list(iteration) for k in self.component_list] if iteration else [],[])
        return (self.io_list if has_self else []) + sub_list
        
    def get_component_list(self,iteration=False,has_self=True) -> list:
        sub_list = reduce(concat,[self.__dict__[k].get_component_list(iteration) for k in self.component_list] if iteration else [],[])
        return (self.component_list if has_self else []) + sub_list

    def get_circuit_list(self,iteration=False,has_self=True) -> list:
        return self.get_component_list(iteration,has_self) + self.get_io_list(iteration,has_self)

    def update_instance_tree(self):
        """
        Update the instance tree for this component and all sub-components.
        This method collects all circuit instances (storage + combinational logic) 
        that belong to this component and stores them in _sub_instance_list.
        Wire instances are excluded as they have no physical area.
        """
        # Clear the current instance list
        self._sub_instance_list = []
        
        # Add registers (have physical area, exclude wires)
        self._sub_instance_list.extend(self.reg_list)
        
        # Add all sub-components
        self._sub_instance_list.extend(self.component_list)
        
        # Collect all combinational logic expressions from lvalue drivers
        # Import here to avoid circular imports
        from .Variable import Expression
        
        processed_expressions = []
        
        def _contains_identity(lst, obj):
            """Check if object is already in list by identity (is operator)"""
            for o in lst:
                if o is obj:
                    return True
            return False
        
        for lvalue in self.lvalue_list:
            if lvalue._rvalue is not None and isinstance(lvalue._rvalue, Expression):
                if not _contains_identity(processed_expressions, lvalue._rvalue):
                    processed_expressions.append(lvalue._rvalue)
        
        # Add collected expressions to instance list
        self._sub_instance_list.extend(processed_expressions)
        
        # Recursively update sub-components
        for sub_component in self.component_list:
            sub_component.update_instance_tree()
    
    def get_area(self) -> float:
        """
        Get the normalized area of this component.
        Automatically calls update_instance_tree() if instance tree hasn't been built.
        
        Returns:
            float: The normalized area of this component
        """
        # Check if instance tree has been built, if not, build it
        if not hasattr(self, '_sub_instance_list') or not self._sub_instance_list:
            self.update_instance_tree()
            
        total_area = 0.0
        
        # Calculate area from all instances in this component
        # All objects in _sub_instance_list are guaranteed to have get_area() method
        for instance in self._sub_instance_list:
            total_area += instance.get_area()
        
        return total_area

    def _generate_area_table(self, indent=0, table_rows=None):
        """
        Generate a hierarchical area report in table format.
        Must call update_instance_tree() first to populate _sub_instance_list.
        
        Args:
            indent: Current indentation level for hierarchy display
            table_rows: List to accumulate table rows (used internally for recursion)
        
        Returns:
            list: List of table rows [instance_name, module_name, area]
        """
        if table_rows is None:
            table_rows = []
        
        prefix = "  " * indent
        total_area = self.get_area()
        
        # Add this component to the table
        # Use 'name' if available, otherwise use module_name, otherwise use class name
        if hasattr(self, 'name') and self.name is not None:
            display_name = self.name
        elif hasattr(self, 'module_name') and self.module_name is not None:
            display_name = self.module_name
        else:
            display_name = self.__class__.__name__
            
        instance_name = f"{prefix}{display_name}"
        table_rows.append([instance_name, self.module_name, f"{total_area:.3f}"])
        
        # Process all instances in this component
        from .Variable import Reg, Expression
        
        # Sort all instances by area (largest first)
        sorted_instances = sorted(self._sub_instance_list, key=lambda x: x.get_area(), reverse=True)
        
        for instance in sorted_instances:
            instance_area = instance.get_area()
            child_prefix = "  " * (indent + 1)
            if isinstance(instance, Reg):
                reg_name = getattr(instance, 'name', 'unnamed_reg')
                instance_name = f"{child_prefix}{reg_name}"
                width = getattr(instance.attribute, 'width', 'N/A')
                module_name = f"Reg[{width}]"
                table_rows.append([instance_name, module_name, f"{instance_area:.3f}"])
            elif isinstance(instance, Expression):
                if instance_area == 0.0:
                    continue  # Skip expressions with zero area
                expr_type = type(instance).__name__
                width = getattr(getattr(instance, 'attribute', None), 'width', 'N/A')
                # Expression instance_name is just type name (no suffix)
                instance_name = f"{child_prefix}{expr_type}"
                module_name = f"{expr_type}[{width}]"
                table_rows.append([instance_name, module_name, f"{instance_area:.3f}"])
            elif isinstance(instance, Component):
                instance._generate_area_table(indent + 1, table_rows)
        
        return table_rows

    def report_area(self):
        """
        Generate a hierarchical area report in table format as string.
        Automatically calls update_instance_tree() if instance tree hasn't been built.
        
        Returns:
            str: Formatted area report table as string
        """
        # Check if instance tree has been built, if not, build it
        if not hasattr(self, '_sub_instance_list') or not self._sub_instance_list:
            self.update_instance_tree()
        
        table_rows = self._generate_area_table()
        
        # Calculate column widths for proper alignment
        if not table_rows:
            return "No area data available."
        
        max_name_width = max(len(row[0]) for row in table_rows)
        max_module_width = max(len(row[1]) for row in table_rows)
        max_area_width = max(len(row[2]) for row in table_rows)
        
        # Ensure minimum column widths
        name_width = max(max_name_width, len("Instance Name"))
        module_width = max(max_module_width, len("Module Name"))
        area_width = max(max_area_width, len("Area"))
        
        # Build table header
        header = f"{'Instance Name':<{name_width}} | {'Module Name':<{module_width}} | {'Area':>{area_width}}"
        separator = "-" * len(header)
        
        # Build table rows
        result_lines = [header, separator]
        for instance_name, module_name, area in table_rows:
            result_lines.append(f"{instance_name:<{name_width}} | {module_name:<{module_width}} | {area:>{area_width}}")
        
        return "\n".join(result_lines)

    @property
    def inter_sig_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Wire,Reg,Mem))]

    @property
    def input_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Input, InputStructIO, InputEnumIO, InputUnionIO))]
    
    @property
    def inout_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Inout)]

    @property
    def output_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Output, OutputStructIO, OutputEnumIO, OutputUnionIO))]

    @property
    def param_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Parameter,))]

    @property
    def var_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Variable)]

    @property
    def wire_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Wire)]

    @property
    def reg_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Reg)]

    @property
    def io_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(IOSig,IOGroup))]
    
    @property
    def io_list_exclude_inout(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Input, Output, InputStructIO, OutputStructIO, InputEnumIO, OutputEnumIO, InputUnionIO, OutputUnionIO, IOGroup))]


    @property
    def component_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Component) and k != '_father']

    @property
    def lvalue_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Wire,Reg,Mem,Output,OutputStructIO,OutputEnumIO,OutputUnionIO))]
    
    @property
    def outer_lvalue_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Input, InputStructIO, InputEnumIO, InputUnionIO))] 

    @property
    def verilog_outer_def_as_list(self):
        # merge all outer def for this module.
        # check whehter an IO return "None" def.
        # This happens when a module direct connect to other io,
        # sometimes it doesn't need to create a new wire, but just direct connect to other io during inst.
        result = [i.verilog_outer_def_as_list_io for i in self.io_list_exclude_inout if i.verilog_outer_def_as_list_io != None]
        return result
    
    @property
    def verilog_inout_def_as_list(self):
        result = [i.verilog_outer_def_as_list_io for i in self.inout_list if i.verilog_outer_def_as_list_io != None]
        return result

    def _collect_struct_packages(self):
        """Collect all unique packages used in this component's IOs and sub-component IOs.
        
        Covers struct, enum, and union types that may need package imports.
        
        Returns:
            set: Set of package names that need to be imported
        """
        packages = set()
        
        from .Variable import (InputStructIO, OutputStructIO,
                               InputEnumIO, OutputEnumIO,
                               InputUnionIO, OutputUnionIO)
        
        typed_io_classes = (InputStructIO, OutputStructIO,
                           InputEnumIO, OutputEnumIO,
                           InputUnionIO, OutputUnionIO)
        
        # Check this component's IO ports
        for io in self.io_list:
            if isinstance(io, typed_io_classes):
                pkg = (getattr(io, '_struct_package', None) or
                       getattr(io, '_enum_package', None) or
                       getattr(io, '_union_package', None))
                if pkg:
                    packages.add(pkg)
        
        # Check sub-components' outer IO definitions (intermediate wires)
        for comp in self.component_list:
            for io in comp.io_list_exclude_inout:
                if isinstance(io, typed_io_classes):
                    pkg = (getattr(io, '_struct_package', None) or
                           getattr(io, '_enum_package', None) or
                           getattr(io, '_union_package', None))
                    if pkg:
                        packages.add(pkg)
        
        return packages

    def __gen_aligned_signal_def(self,io_para_list):
        max_prefix_length = 0
        max_width_length = 0
        max_name_length = 0
        for i,j,k in io_para_list:
            max_prefix_length = len(i) if len(i)>max_prefix_length else max_prefix_length
            max_width_length = len(j) if len(j)>max_width_length else max_width_length
            max_name_length = len(k) if len(k)>max_name_length else max_name_length
        
        template_str = '%%-%ds %%-%ds %%-%ds'%(max_prefix_length,max_width_length,max_name_length)
        return [template_str%(i,j,k) for i,j,k in io_para_list]

    @property
    def verilog_def(self):
        # Pre-create temporary wires for cut expressions before generating wire declarations
        self._ensure_temp_wires_for_cuts()
        
        # Collect required packages from StructIO signals
        required_packages = self._collect_struct_packages()
        
        # Generate module declaration with imports
        if required_packages:
            # Module with imports
            str_list = ['module %s' % self.module_name]
            for pkg in sorted(required_packages):  # Sort for deterministic output
                str_list.append('\timport %s::*;' % pkg)
            str_list.append('\t%s' % ('#(' if self.param_list else '('))
        else:
            # Module without imports (original format)
            str_list = ['module %s %s' % (self.module_name, '#(' if self.param_list else '(')]

        # parameter define
        if self.param_list:
            # pylint: disable=no-member
            str_list += self.__eol_append(reduce(concat,[i.verilog_def for i in self.param_list],[]),',','') + [')(']
            # pylint: enable=no-member

        # module io define
        if self.io_list == []: str_list.append(');')
        else: str_list += self._tag_decls(self.__eol_append(self.__gen_aligned_signal_def([i.verilog_def_as_list for i in self.io_list]),',',');'), self.io_list)

        # module wire define
        str_list += ['','\t//Wire define for this module.']
        str_list += self._tag_decls(self.__eol_append(self.__gen_aligned_signal_def([i.verilog_def_as_list for i in self.inter_sig_list]),';',';'), self.inter_sig_list)

        str_list += ['','\t//Wire define for sub module.']
        str_list += self.__eol_append(self.__gen_aligned_signal_def(reduce(concat,[i.verilog_outer_def_as_list for i in self.component_list],[])),';',';')

        # module wire define for inout
        str_list += ['','\t//Wire define for Inout.']
        str_list += self.__eol_append(self.__gen_aligned_signal_def(reduce(concat,[i.verilog_inout_def_as_list for i in self.component_list],[])),';',';')

        # combine logic assignment
        str_list += ['','\t//Wire sub module connect to this module and inter module connect.']
        str_list += self.__eol_append(reduce(concat,[SrcLoc.tag(i.verilog_assignment, i.__dict__.get('_rvalue_src')) +[''] for i in self.lvalue_list if i.verilog_assignment],[]),'')

        sub_io_list = reduce(concat,[i.outer_lvalue_list for i in self.component_list],[])
        str_list += ['','\t//Wire this module connect to sub module.']
        str_list += self.__eol_append(reduce(concat,[SrcLoc.tag(i.verilog_assignment, i.__dict__.get('_rvalue_src')) +[''] for i in sub_io_list if i.verilog_assignment],[]),'')

        # component inst
        str_list += ['','\t//module inst.']
        str_list += self.__eol_append(reduce(concat,[SrcLoc.tag(i.verilog_inst, [SrcLoc.decl(i)]) for i in self.component_list],[]),'')

        str_list += ['','endmodule']
        return str_list

    def _ensure_temp_wires_for_cuts(self):
        """Pre-create helper wires (Cut temps, inline Case/When temps) so they are
        declared before use. Rendering can create new wires whose own assignment
        creates more, so repeat until the set of internal signals is stable."""
        for _ in range(64):
            before = len(self.inter_sig_list)
            self._ensure_temp_wires_once()
            if len(self.inter_sig_list) == before:
                return

    def _ensure_temp_wires_once(self):
        # Pre-generate all assignments to trigger temporary wire creation
        temp_assignments = []
        
        # Generate assignments for this module's lvalue variables
        for var in self.lvalue_list:
            if var.verilog_assignment:
                temp_assignments.extend(var.verilog_assignment)
        
        # Generate assignments for sub-module connections
        for comp in self.component_list:
            for var in comp.outer_lvalue_list:
                if var.verilog_assignment:
                    temp_assignments.extend(var.verilog_assignment)
    @property
    def verilog_inst(self):
        param_assignment_list = reduce(concat,[i.verilog_assignment for i in self.param_list],[])

        if param_assignment_list:
            str_list = ['%s #(' % self.module_name]
            str_list += self.__eol_append(param_assignment_list,',',')')
            str_list += ['%s (' % self.name]
        else:
            str_list = ['%s %s (' % (self.module_name, self.name)]

        ports = [(i.verilog_inst, self._port_src(i)) for i in self.io_list]
        lines = self.__eol_append(reduce(concat,[p for p, _ in ports],[]),',',');')
        if SrcLoc.comments_on() and all(len(p) == 1 for p, _ in ports):
            lines = [SrcLoc.tag([l], locs)[0] for l, (_, locs) in zip(lines, ports)]
        str_list += lines
        return str_list

    @staticmethod
    def _tag_decls(lines, sigs):
        '''Declaration lines (one per signal) end with the Python line that declared the signal.'''
        if not SrcLoc.comments_on() or len(lines) != len(sigs):
            return lines
        return [SrcLoc.tag([l], [SrcLoc.decl(x)])[0] for l, x in zip(lines, sigs)]

    @staticmethod
    def _port_src(port):
        '''Where the parent connected a sub-component port: the input's driver, or for an
        output the assignment that reads it.'''
        if isinstance(port, Output):
            return tuple(l for x in port._lvalue_list for l in (x.__dict__.get('_rvalue_src') or ()))
        return port.__dict__.get('_rvalue_src') or ()

#################################################################################
# Verilog File Opeartion
#################################################################################

    def _create_this_vfile(self,path):
        FileProcess.create_file(os.path.join(path,'%s.v' % self.module_name),self.verilog_def)

    def _create_all_vfile(self,path):
        self._create_this_vfile(path)
        for c in self.component_list:
            c._create_all_vfile(path)

    def check_cdc(self):
        '''Return the clock-domain-crossing violations of this design (see uhdl.core.Cdc).'''
        from .Cdc import check_cdc
        return check_cdc(self)

    def generate(self, out_dir, filelist=True, clean=False, filelist_name='filelist.f', cdc_check=True,
                 src_comments=True):
        '''Write every UHDL-generated module of this design as <out_dir>/<module>.v
        (flat, one file per module, sub-modules first) and, by default,
        <out_dir>/filelist.f with absolute paths. Existing files in out_dir are
        kept unless clean=True. Raises ErrUHDLStr if two different modules share
        a name, or (unless cdc_check=False) if the design has an unsynchronized
        clock-domain crossing. With src_comments (default), the first line of each assign,
        always block and instance ends with `// file.py:line`, naming the Python code that wrote
        it. Returns the list of written .v paths.'''
        with SrcLoc.deferred():
            return self._generate(out_dir, filelist, clean, filelist_name, cdc_check, src_comments)

    def _generate(self, out_dir, filelist, clean, filelist_name, cdc_check, src_comments):
        from .UHDLException import ErrUHDLStr
        if cdc_check:
            v = self.check_cdc()
            if v:
                raise ErrUHDLStr('%d clock-domain crossing violation(s):\n  ' % len(v) + '\n  '.join(v))
        out_dir = os.path.abspath(out_dir)
        if clean:
            FileProcess.refresh_directory(out_dir)
        else:
            os.makedirs(out_dir, exist_ok=True)

        texts, order, extra_paths = {}, [], []

        def walk(comp):
            for sub in comp.component_list:
                walk(sub)
            if type(comp)._create_this_vfile is not Component._create_this_vfile:
                extra = comp._create_this_vfile(out_dir)   # VComponent / TemplateComponent keep their own handling
                if isinstance(extra, str) and extra not in extra_paths:
                    extra_paths.append(extra)                # e.g. a packed-port shim around an SV module
                return
            if src_comments:
                with SrcLoc.verilog_comments():
                    text = comp.verilog_def
            else:
                text = comp.verilog_def
            name = comp.module_name
            if name in texts:
                if texts[name] != text:
                    raise ErrUHDLStr('Two different modules are both named "%s". Give them distinct '
                                     'names with set_module_name()/MODULE_NAME.' % name)
                return
            texts[name] = text
            order.append(name)

        walk(self)
        paths = list(extra_paths)
        for name in order:
            path = os.path.join(out_dir, '%s.v' % name)
            FileProcess.create_file(path, texts[name])
            paths.append(path)
        if filelist:
            # plain text: tools read every non-comment line of a .f as a file name
            with open(os.path.join(out_dir, filelist_name), 'w') as f:
                f.write(''.join(p + '\n' for p in paths))
        return paths

    def mark_unused(self, *sigs):
        '''Tell lint that these signals are intentionally unused (e.g. unused
        input ports or dropped carry bits). Creates a wire named
        uhdl_unused_<n> driven by them; Verilator ignores *unused* signals
        and synthesis removes the wire.'''
        if not sigs:
            return None
        from .Operator import Combine
        width = sum(x.attribute.width for x in sigs)
        from .Variable import UInt as _UInt
        name = 'uhdl_unused_%d' % self._unused_seq
        self._unused_seq += 1
        w = self.create(name, Wire(_UInt(width)))
        w += Combine(*sigs)
        return w

    def generate_verilog(self,iteration=False):
        FileProcess.refresh_directory(self.output_path)
        if iteration:
            self._create_all_vfile(self.output_path)
        else:
            self._create_this_vfile(self.output_path)


    def _generate_filelist_core(self, prefix=''):
        """
        Generate filelist recursively, collecting .v files from this component and sub-components.
        
        Args:
            prefix: Path prefix for generated files
        
        Returns:
            List of file paths
        """
        # Add this component's .v file
        name_list = ["%s/%s.v" % (prefix, self.module_name)]
        
        # Recursively collect from sub-components
        for component in self.component_list:
            name_list += component._generate_filelist_core(prefix=prefix)
        
        return name_list


    def generate_filelist(self,abs_path=False,path='-',prefix='',name='filelist.f'):
        path = self.output_path if path == '-' else path

        self._flist_path = os.path.join(path,name)

        if abs_path is True:
            real_prefix = os.path.join(self.output_dir,self.module_name)
        else:
            real_prefix = os.path.join(prefix,self.module_name)

        file_list = self._generate_filelist_core(prefix=real_prefix)
        file_list.reverse()

        # remove duplicates
        new_file_list = list(set(file_list))
        new_file_list.sort(key=file_list.index)

        FileProcess.create_file( path = self._flist_path,
                                 text = new_file_list)

#################################################################################
# Lint
#################################################################################
    
    def _run_lint_single_lvl(self, is_top=False):
        Terminal.lint_info('Start to check module %s.' % self.module_name)
        if not is_top:
            for lvalue in self.input_list:
                if lvalue.rvalue is None:
                    Terminal.lint_unconnect(lvalue)
        
        for lvalue in self.lvalue_list:
            if lvalue.rvalue is None:
                Terminal.lint_unconnect(lvalue)

    def _run_lint_all_single_lvl(self, is_top=False):
        Terminal.lint_info('Start to check module %s.' % self.module_name)
        # input of top
        if is_top==True:
            for rvalue in self.input_list:
                if rvalue._lvalue_list==[]:
                    Terminal.lint_unconnect(rvalue, is_top)

            # output of top
            for lvalue in self.lvalue_list:
                if lvalue.rvalue is None:
                    Terminal.lint_unconnect(lvalue)
        
            # inout of top
            for inout in self.inout_list:
                if len(inout._inout_connect_list)<=1:
                    Terminal.lint_unconnect(inout)
        
        else:
            # input of sub
            for lvalue in self.input_list:
                if lvalue.rvalue is None:
                    Terminal.lint_unconnect(lvalue)

            # output of sub
            for rvalue in self.output_list:
                if rvalue._lvalue_list==[]:
                    Terminal.lint_unconnect(rvalue)

            # inout of sub
            for inout in self.inout_list:
                if len(inout._inout_connect_list)<=1:
                    Terminal.lint_unconnect(inout)


    def _run_lint_core(self, is_top=False, lint_all=False):
        for component in self.component_list:
            component._run_lint_core(lint_all=lint_all)
        if lint_all==False:
            self._run_lint_single_lvl(is_top=is_top)
        else:
            self._run_lint_all_single_lvl(is_top=is_top)


    def run_lint(self, lint_all=False):
        self._run_lint_core(is_top=True, lint_all=lint_all)


#################################################################################
# UHDL Compile
#################################################################################

    def compile(self,output_dir='.'):
        self.output_dir = output_dir
        self.generate_verilog()
        self.generate_filelist()
        self.run_lint()

#################################################################################
# Third Party Compile
#################################################################################

    def run_slang_compile(self):
        from ._slang import Driver, CommandLineOptions, DiagnosticEngine, full_compilation

        driver = Driver()
        driver.addStandardArgs()
        ok = driver.parseCommandLine(f'slang -f {self._flist_path}', CommandLineOptions())
        if not ok:
            raise Exception('Slang compile error: failed to parse command line.')
        driver.processOptions()
        driver.parseAllSources()
        success = full_compilation(driver)
        if not success:
            comp = driver.createCompilation()
            diags = comp.getAllDiagnostics()
            details = ''
            if diags:
                details = '\n' + DiagnosticEngine.reportAll(comp.sourceManager, diags)
            raise Exception('Slang compile error.' + details)

    def run_verilator_compile(self):
        cmd = 'verilator --lint-only -f %s' % self._flist_path
        print('Run command: %s' % cmd)
        slang_res = os.system(cmd)
        if slang_res != 0:
            raise Exception('Verilator compile error.')



    def __eol_append(self,list_in,common_str,end_str=None):
        if end_str is None:
            end_str = common_str
        if list_in:
            result = []
            for i in list_in[0:-1]:
                result.append('\t%s%s' % (i,common_str) )
            result.append('\t%s%s' % (list_in[-1],end_str))
            return result
        else:
            return []



    def __subclass_init_param_get(self):
        # Get locals
        trace_num = self.__class__.__mro__.index(Component)
        frame = inspect.currentframe()
        for i in range(trace_num+1):
            frame = frame.f_back
        local = frame.f_locals

        # Get Var name
        argspec = inspect.getfullargspec(self.__init__)

        # Set Param
        args = argspec.args
        args.remove('self')

        for arg in args:
            setattr(self._PARAM,arg,local[arg])

        for arg in argspec.kwonlyargs:
            setattr(self._PARAM,arg,local[arg])

        if argspec.varargs != None:
            setattr(self._PARAM,argspec.varargs,local[argspec.varargs])

        if argspec.varkw != None:
            setattr(self._PARAM,argspec.varkw,local[argspec.varkw])

        self._PARAM._caculate_name()


##########################################################################################
# Syntax Sugar for Integration
##########################################################################################

    def expose_io(self, io_list, has_prefix=True):
        
        for io in io_list:
            sub_inst = io._father
            if self != sub_inst._father:
                raise Exception()
            if has_prefix==True:
                new_io_name = '%s_%s' % (sub_inst.name, io.name)
            else:
                new_io_name = '%s' % (io.name)
                self.io_name_list = [io.name for io in self.io_list]
                if new_io_name in self.io_name_list:
                    old_io = self.io_list[self.io_name_list.index(new_io_name)]
                    if isinstance(old_io, Inout) and isinstance(io, Inout):
                        Terminal.warning("Interface <%s> Existing, Please check interface <%s.%s>"% (old_io, sub_inst.name,new_io_name))
                    elif isinstance(old_io, Input) and isinstance(io, Input):
                        Terminal.warning("Interface <%s> Existing, Please check interface <%s.%s>"% (old_io, sub_inst.name,new_io_name))
                    else:
                        Terminal.error("Interface <%s> Existing, Please check interface <%s.%s>"% (old_io, sub_inst.name,new_io_name))
                        break

            new_io = self.set(new_io_name, io.template())

            if isinstance(new_io, Input):
                io += new_io
            elif isinstance(new_io, Output):
                new_io += io
            elif isinstance(new_io, Inout):
                new_io += io
            else:
                Terminal.error("Interface <%s.%s> is not Input/Output/Inout"% (sub_inst.name,new_io_name))

    def get_io(self, string):
        match_io_list = []
        for io in self.io_list:
            if re.search(string, io.name):
                match_io_list.append(io)
        return match_io_list
    
    def exclude_io(self, io_list, exclude_list):
        pattern = '|'.join(exclude_list)
        io_list_new=[]
        for io in io_list:
            if not re.search(pattern, io.name):
                io_list_new.append(io)
        return io_list_new

