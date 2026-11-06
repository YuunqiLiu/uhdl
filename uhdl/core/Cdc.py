"""Clock-domain crossing check on the UHDL object graph.

Every Reg and Mem knows its clock. A top-level port can be given one with
Input(w, domain=clk) / Output(w, domain=clk). check_cdc(top) walks the
combinational fan-in of every register, Mem write port and domain-annotated
output, back to the registers, Mems and ports that feed it, and reports:

  * a crossing from one clock domain to another that does not end inside a
    CDC cell (a Component whose class sets CDC_CELL = 'sync' | 'bus' | 'fifo');
  * combinational logic in front of a 'sync' cell (its input must come
    straight from a register or a port of the source domain);
  * reconvergence: two or more 'sync' cells carrying signals from the same
    source domain that meet in the same destination register's fan-in.
    Several bits that belong together must cross as one value (a 'bus' or
    'fifo' cell), or be combined in the source domain before one 'sync'.

Two clocks are the same domain when they are the same signal after following
plain connections (port to wire to port). Signals whose domain is unknown (an
unannotated top-level input, an output of an imported VComponent) are not
checked.
"""
import sys
from .Variable import (Variable, Value, Expression, Constant, Reg, Mem, MemReadExpression,
                       Input, Output, Inout, Wire, CutExpression)

sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))


def _component(obj):
    from .Component import Component
    return obj.father_until(Component) if hasattr(obj, 'father_until') else None


def cdc_cell_of(obj):
    """The innermost CDC cell that contains obj, or None."""
    from .Component import Component
    c = obj.father if isinstance(obj, Variable) else obj
    while c is not None:
        if isinstance(c, Component) and getattr(type(c), 'CDC_CELL', None):
            return c
        c = getattr(c, 'father', None)
    return None


def domain_root(clk):
    """Follow plain connections from a clock signal to the signal that defines it."""
    seen = set()
    while isinstance(clk, (Input, Output, Wire)) and id(clk) not in seen:
        seen.add(id(clk))
        r = clk._rvalue
        if isinstance(r, (Input, Output, Wire)):
            clk = r
        else:
            break
    return clk


def _name(obj):
    try:
        return obj.full_hier
    except Exception:
        return str(obj)


def _where(*items):
    """" [x: file:line; y: file:line]" naming the Python lines behind the objects of a message.
    Items are objects (their declaration) or (object, True) for where a sink was assigned."""
    from . import SrcLoc
    out = []
    for it in items:
        obj, assigned = it if isinstance(it, tuple) else (it, False)
        locs = SrcLoc.of(obj) if assigned else ()
        loc = locs[0] if locs else SrcLoc.decl(obj)
        if loc:
            out.append('%s %s' % (_name(obj), SrcLoc.fmt(loc, code=False)))
    return ' [%s]' % '; '.join(out) if out else ''


class _Cone:
    __slots__ = ('sources', 'syncs')

    def __init__(self):
        self.sources = {}      # id(src) -> (src, domain, via_logic)
        self.syncs = {}        # id(cell) -> cell


class CdcChecker:
    def __init__(self, top):
        self.top = top
        self.memo = {}
        self.violations = []

    # ---------------------------------------------------------------- traversal
    def _port_domain(self, port):
        d = getattr(port, '_cdc_domain', None)
        return domain_root(d) if d is not None else None

    def cone(self, node):
        key = id(node)
        if key in self.memo:
            return self.memo[key]
        c = _Cone()
        self.memo[key] = c                      # breaks combinational loops
        if isinstance(node, Reg):
            c.sources[key] = (node, domain_root(node._aclk), False)
        elif isinstance(node, MemReadExpression):
            c.sources[key] = (node, domain_root(node.mem._aclk), False)
            self._merge(c, self.cone(node.addr), True)
        elif isinstance(node, Constant):
            pass
        elif isinstance(node, Variable):
            cell = _component(node) if isinstance(node, Output) else None
            kind = getattr(type(cell), 'CDC_CELL', None) if cell is not None else None
            if kind and getattr(node, '_cdc_domain', None) is not None:
                # A CDC cell guarantees that its outputs are stable in the domain they declare.
                c.sources[key] = (node, self._port_domain(node), False)
                if kind == 'sync':
                    c.syncs[id(cell)] = cell
                return c
            r = getattr(node, '_rvalue', None)
            if r is None:
                if isinstance(node, (Input, Inout)) and node.father is self.top:
                    d = self._port_domain(node)
                    if d is not None:
                        c.sources[key] = (node, d, False)
            else:
                self._merge(c, self.cone(r), False)
        elif isinstance(node, Expression):
            logic = not isinstance(node, CutExpression)
            for f in node.fanin_list:
                if isinstance(f, (Value, Variable)):
                    self._merge(c, self.cone(f), logic)
        return c

    @staticmethod
    def _merge(dst, src, logic):
        for k, (s, d, v) in src.sources.items():
            old = dst.sources.get(k)
            dst.sources[k] = (s, d, v or logic or (old[2] if old else False))
        dst.syncs.update(src.syncs)

    # ---------------------------------------------------------------- rules
    def _sync_src_domains(self, cell):
        doms = {}
        for port in cell.input_list:
            if port is getattr(cell, 'clk', None) or port is getattr(cell, 'rst_n', None):
                continue
            for s, d, _ in self.cone(port).sources.values():
                doms[id(d)] = d
        return doms

    def check_sink(self, what, sink_name, dom, cone):
        if dom is None:
            return
        for s, d, via_logic in cone.sources.values():
            if d is None or d is dom:
                continue
            cell = cdc_cell_of(what) if what is not None else None
            if cell is None:
                self.violations.append(
                    'unsynchronized crossing: %s (clock %s) -> %s (clock %s). Use CdcSync (1 bit), '
                    'CdcBus (a multi-bit value) or AsyncFifo (a stream).'
                    % (_name(s), _name(d), sink_name, _name(dom)) + _where(s, (what, True)))
            elif type(cell).CDC_CELL == 'sync' and via_logic:
                self.violations.append(
                    'logic in front of a synchronizer: %s (clock %s) reaches %s through combinational '
                    'logic. Register the signal in its own domain, then synchronize the register.'
                    % (_name(s), _name(d), _name(cell)) + _where(s, cell))
        # reconvergence of synchronizers from one source domain
        if cone.syncs and len(cone.syncs) > 1 and (what is None or cdc_cell_of(what) is None):
            by_dom = {}
            for cell in cone.syncs.values():
                for k, d in self._sync_src_domains(cell).items():
                    by_dom.setdefault(k, (d, []))[1].append(cell)
            for d, cells in by_dom.values():
                if len(cells) > 1:
                    self.violations.append(
                        'reconvergent synchronizers: %s carry signals from clock %s and meet in the fan-in of %s. '
                        'Bits that belong together must cross as one value (CdcBus/AsyncFifo), or be combined '
                        'in the source domain before a single CdcSync.'
                        % (', '.join(sorted(_name(c) for c in cells)), _name(d), sink_name)
                        + _where(*sorted(cells, key=_name)))

    def run(self):
        from .Component import Component
        stack, comps = [self.top], []
        while stack:
            c = stack.pop()
            comps.append(c)
            stack.extend(x for x in c.__dict__.values() if isinstance(x, Component) and x is not c.father)
        for comp in comps:
            for v in comp.__dict__.values():
                if isinstance(v, Reg) and v._rvalue is not None:
                    self.check_sink(v, _name(v), domain_root(v._aclk), self.cone(v._rvalue))
                elif isinstance(v, Mem):
                    dom = domain_root(v._aclk)
                    for en, addr, data in v._write_ports:
                        for x in (en, addr, data):
                            self.check_sink(v, _name(v), dom, self.cone(x))
        for o in self.top.output_list:
            d = self._port_domain(o)
            if d is not None and o._rvalue is not None:
                self.check_sink(o, _name(o), d, self.cone(o._rvalue))
        seen, out = set(), []
        for v in self.violations:
            if v not in seen:
                seen.add(v); out.append(v)
        return out


def check_cdc(top):
    """Return the list of CDC violations in the design under `top` (empty if clean)."""
    return CdcChecker(top).run()
