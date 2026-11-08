import os
import re
from collections import OrderedDict

from . import _slang                       # libuhdl_slang, loaded on first use

from .Component import Component
from .Variable  import (Wire, IOSig, IOGroup, InputStructIO, OutputStructIO,
                        InputEnumIO, OutputEnumIO, InputUnionIO, OutputUnionIO,
                        Variable, Parameter, Reg, Output, Input, Inout,
                        UInt, SInt, AnyConstant, StructType, StructConstant,
                        EnumType, EnumConstant, UnionType, UnionConstant)
from .Terminal  import Terminal


class VParameter(object):
    """A module parameter: name and value as slang prints it."""

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def create_uhdl_param(self):
        return Parameter(AnyConstant(self.value))


from .UHDLException import ErrUHDLStr
from .Variable import Input, Output, UInt


class SvType(str):
    '''A SystemVerilog type given as a parameter of a VComponent, for `parameter type`:
    VComponent(file, top='fcip_reg_slice', PLD_TYPE=SvType('logic [37:0]'), RS_TYPE=0).'''


class VPort(object):
    """Port descriptor built from the type description of libuhdl_slang (see core/_slang.py):
    {"w": width, "s": signed, "alias": "pkg::name" | None, "k": "scalar" | "struct" | "union"
     | "enum" | "unpacked", "fields": [{"n", "t"}], "values": [[name, int]], "elem", "left", "right"}."""

    def __init__(self, name, direction, port_type, struct_mode: str = 'auto'):
        self.name = name
        self.direction = direction          # "In" / "Out" / "InOut"
        self._struct_mode = struct_mode

        self.is_struct = False
        self.is_enum = False
        self.is_union = False
        self.struct_type_name = None
        self.struct_package = None
        self._struct_type_obj = None
        self.struct_fields = []
        self._enum_type_obj = None
        self._enum_type_name = None
        self._enum_package = None
        self._union_type_obj = None
        self._union_type_name = None
        self._union_package = None
        self._union_fields = []
        self.width = port_type['w']
        self.signed = port_type['s']
        kind = port_type['k']
        name_pkg = self._alias_name(port_type)

        if kind == 'enum':
            self.is_enum = True
            self._enum_type_name, self._enum_package = name_pkg
            members = OrderedDict((n, v) for n, v in port_type['values'])
            self._enum_type_obj = EnumType.get_or_create(
                self._enum_type_name, members, self.width, self.signed, self._enum_package
            )

        elif kind == 'union':
            self.is_union = True
            self._union_type_name, self._union_package = name_pkg
            self._union_fields = [self._field_info(f) for f in port_type['fields']]
            self._union_type_obj = UnionType.get_or_create(
                self._union_type_name, self._field_map(self._union_fields), self._union_package
            )

        elif kind == 'struct':
            self.is_struct = True
            self.struct_type_name, self.struct_package = name_pkg
            self.struct_fields = [self._field_info(f) for f in port_type['fields']]
            self._struct_type_obj = StructType.get_or_create(
                self.struct_type_name, self._field_map(self.struct_fields), self.struct_package
            )

    @staticmethod
    def _alias_name(t):
        """(type name, package) of a typedef'd type: ('pkg::t', 'pkg'), ('t', None) or (None, None)."""
        hier = t.get('alias')
        if not hier:
            return None, None
        return hier, (hier.split('::')[0] if '::' in hier else None)

    @staticmethod
    def _field_info(f):
        ft = f['t']
        info = {'name': f['n'], 'width': ft['w'], 'signed': ft['s']}
        if ft['k'] == 'struct':
            info['struct_type'] = VPort._build_struct_type(ft)
        return info

    @staticmethod
    def _field_map(fields):
        out = OrderedDict()
        for f in fields:
            fi = {'width': f['width'], 'signed': f['signed']}
            if 'struct_type' in f:
                fi['struct_type'] = f['struct_type']
            out[f['name']] = fi
        return out

    @staticmethod
    def _build_struct_type(t):
        """StructType of a (possibly nested) struct type description."""
        name, pkg = VPort._alias_name(t)
        fields = OrderedDict()
        for f in t['fields']:
            ft = f['t']
            fi = {'width': ft['w'], 'signed': ft['s']}
            if ft['k'] == 'struct':
                fi['struct_type'] = VPort._build_struct_type(ft)
            fields[f['n']] = fi
        return StructType.get_or_create(name, fields, pkg)

    def create_uhdl_port(self):
        """Create the appropriate UHDL port object from parsed port data."""

        # ---------- Enum port ----------
        if self.is_enum and self._struct_mode != 'packed':
            template = EnumConstant(self._enum_type_obj)
            if self.direction == 'Out':
                return OutputEnumIO(template, enum_name=self._enum_type_name,
                                   enum_package=self._enum_package, enum_type=self._enum_type_obj)
            elif self.direction == 'In':
                return InputEnumIO(template, enum_name=self._enum_type_name,
                                  enum_package=self._enum_package, enum_type=self._enum_type_obj)
            else:
                return InputEnumIO(template, enum_name=self._enum_type_name,
                                  enum_package=self._enum_package, enum_type=self._enum_type_obj)

        # ---------- Union port ----------
        if self.is_union and self._struct_mode != 'packed':
            fields = []
            for f in self._union_fields:
                width = f['width']
                signed = f['signed']
                if self.direction == 'Out':
                    sig = Output(SInt(width)) if signed else Output(UInt(width))
                elif self.direction == 'In':
                    sig = Input(SInt(width)) if signed else Input(UInt(width))
                elif self.direction == 'InOut':
                    sig = Inout(SInt(width)) if signed else Inout(UInt(width))
                else:
                    sig = Input(UInt(width))
                fields.append((f['name'], sig))
            template = UnionConstant(self._union_type_obj)
            if self.direction == 'Out':
                return OutputUnionIO(template, fields=fields, union_name=self._union_type_name,
                                    union_package=self._union_package, union_type=self._union_type_obj)
            elif self.direction == 'In':
                return InputUnionIO(template, fields=fields, union_name=self._union_type_name,
                                   union_package=self._union_package, union_type=self._union_type_obj)
            else:
                return InputUnionIO(template, fields=fields, union_name=self._union_type_name,
                                   union_package=self._union_package, union_type=self._union_type_obj)

        # ---------- Struct port ----------
        if self.is_struct and self._struct_mode != 'packed' and self.struct_fields:
            fields = []
            for f in self.struct_fields:
                width = f['width']
                signed = f['signed']
                if self.direction == 'Out':
                    sig = Output(SInt(width)) if signed else Output(UInt(width))
                elif self.direction == 'In':
                    sig = Input(SInt(width)) if signed else Input(UInt(width))
                elif self.direction == 'InOut':
                    sig = Inout(SInt(width)) if signed else Inout(UInt(width))
                else:
                    sig = Input(UInt(width))
                fields.append((f['name'], sig))
            template = StructConstant(self._struct_type_obj)
            struct_name = self.struct_type_name
            struct_package = self.struct_package
            if self.direction == 'Out':
                return OutputStructIO(template, fields=fields, struct_name=struct_name,
                                      struct_package=struct_package, struct_type=self._struct_type_obj)
            elif self.direction == 'In':
                return InputStructIO(template, fields=fields, struct_name=struct_name,
                                     struct_package=struct_package, struct_type=self._struct_type_obj)
            else:
                return InputStructIO(template, fields=fields, struct_name=struct_name,
                                     struct_package=struct_package, struct_type=self._struct_type_obj)

        # ---------- Non-composite port ----------
        if self.direction == "Out":
            return Output(SInt(self.width)) if self.signed else Output(UInt(self.width))
        elif self.direction == "In":
            return Input(SInt(self.width)) if self.signed else Input(UInt(self.width))
        elif self.direction == "InOut":
            return Inout(SInt(self.width)) if self.signed else Inout(UInt(self.width))
        else:
            raise Exception(f"Unknown port direction: {self.direction}")


class VComponent(Component):

    def __init__(self, file=None, top=None, instance=None, slang_cmd='slang', slang_opts='--ignore-unknown-modules', struct_mode: str = 'auto', **kwargs):
        super().__init__()
        self.enable_filelist_generation = False
        self._module_name = top
        self._struct_mode = struct_mode

        # Build the slang command line
        # Handle file source: .f files use -f flag, others are passed directly
        if str(file).endswith('.f'):
            source = f'-f {file}'
        else:
            source = str(file)

        # Type parameters (SvType values) cannot be set with -G: elaborate the module inside a
        # small wrapper that overrides them, and read the ports of that instance instead.
        type_params = {k: v for k, v in kwargs.items() if isinstance(v, SvType)}
        wrap_file = None
        if type_params and struct_mode == 'auto':
            # ports typed by a type parameter have no package-qualified name to emit: keep them packed
            self._struct_mode = 'packed'
        if type_params:
            import tempfile
            ov = ', '.join('.%s(%s)' % (k, v) for k, v in kwargs.items())
            fd, wrap_file = tempfile.mkstemp(suffix='.sv', prefix='uhdl_vwrap_')
            with os.fdopen(fd, 'w') as f:
                f.write('module __uhdl_vwrap; %s #(%s) u (); endmodule\n' % (top, ov))
            cmd = f'slang {slang_opts} {source} {wrap_file} --top __uhdl_vwrap'.strip()
        else:
            # Build parameter overrides in slang -G format
            param_args = ''
            for k, v in kwargs.items():
                param_args += f'-G {k}={v} '
            cmd = f'slang {slang_opts} {source} --top {top} {param_args}'.strip()

        # Elaborate with slang (libuhdl_slang) and read the instance's ports and parameters
        try:
            info = _slang.module_info(cmd, '__uhdl_vwrap.u' if wrap_file is not None else top)
        except RuntimeError as e:
            raise Exception(str(e)) from None
        finally:
            if wrap_file is not None:
                os.unlink(wrap_file)

        self._vport_list = []
        self._vparam_list = []
        self._shim_text = None

        ports = [m for m in info['members'] if m['kind'] == 'port']
        bad = [m['name'] for m in ports if m['type']['w'] == 0 and m['type']['k'] != 'unpacked']
        bad += [m['name'] for m in ports if m['type']['k'] == 'unpacked'
                and (m['type'].get('elem') or {'w': 0})['w'] == 0]
        if bad:
            raise ErrUHDLStr('VComponent %s: slang could not resolve the type of port(s) %s (width 0). A package '
                             'or macro is probably missing from the sources; for macros defined in another file '
                             "try slang_opts='--ignore-unknown-modules --single-unit'." % (top, ', '.join(bad)))

        # Unpacked-array ports cannot be connected from UHDL's flat vectors. If there are any,
        # wrap the module in a generated SV shim whose ports are all packed (an unpacked array
        # of N elements of W bits becomes one N*W-bit port, element lo+k at bits [k*W +: W]).
        if any(m['type']['k'] == 'unpacked' for m in ports):
            self._build_flat_shim(top, ports, kwargs)
            return

        for member in info['members']:
            if member['kind'] == 'port':
                self._vport_list.append(VPort(member['name'], member['dir'], member['type'], struct_mode=self._struct_mode))
            elif member['kind'] == 'param' and not member['local']:
                self._vparam_list.append(VParameter(member['name'], member['value']))
            elif member['kind'] == 'type_param' and member['name'] in type_params:
                self._vparam_list.append(VParameter(member['name'], str(type_params[member['name']])))

        for vport in self._vport_list:
            self.create(vport.name, vport.create_uhdl_port())

        for vparam in self._vparam_list:
            self.create(vparam.name, vparam.create_uhdl_param())

    def _run_lint_single_lvl(self, is_top=False):
        Terminal.lint_info('Start to check VComponent module %s.' % self.module_name)

        # VComponent will only check input signal.
        # If VComp is a top module, nothing need to be checked.
        if not is_top:
            for lvalue in self.input_list:
                if lvalue.rvalue is None:
                    Terminal.lint_unconnect(lvalue)



    def _build_flat_shim(self, top, ports, params):
        import hashlib
        tag = hashlib.md5(repr((top, sorted((k, str(v)) for k, v in params.items()))).encode()).hexdigest()[:8]
        shim = '%s__uflat_%s' % (top, tag)
        decl, body, conns = [], [], []
        for m in ports:
            t = m['type']
            d = {'In': 'input', 'Out': 'output'}.get(m['dir'])
            if d is None:
                raise ErrUHDLStr('VComponent %s: inout port %s is not supported with unpacked-array ports.' % (top, m['name']))
            if t['k'] == 'unpacked':
                el = t['elem']
                if el['k'] == 'unpacked':
                    raise ErrUHDLStr('VComponent %s: port %s has more than one unpacked dimension.' % (top, m['name']))
                ew, left, right = el['w'], t['left'], t['right']
                n, lo = abs(left - right) + 1, min(left, right)
                width = n * ew
                body.append('    logic [%d:0] %s__a [%d:%d];' % (ew - 1, m['name'], left, right))
                for k in range(n):
                    if d == 'input':
                        body.append('    assign %s__a[%d] = %s[%d +: %d];' % (m['name'], lo + k, m['name'], k * ew, ew))
                    else:
                        body.append('    assign %s[%d +: %d] = %s__a[%d];' % (m['name'], k * ew, ew, m['name'], lo + k))
                conns.append('.%s(%s__a)' % (m['name'], m['name']))
            else:
                width = t['w']
                conns.append('.%s(%s)' % (m['name'], m['name']))
            decl.append('    %s logic %s%s' % (d, '' if width == 1 else '[%d:0] ' % (width - 1), m['name']))
            io = Input if d == 'input' else Output
            self.create(m['name'], io(UInt(width)))
        ov = ', '.join('.%s(%s)' % (k, v) for k, v in params.items())
        self._shim_text = '\n'.join(
            ['// Generated by UHDL: packed-port wrapper around %s.' % top,
             'module %s (' % shim, ',\n'.join(decl), ');'] + body +
            ['    %s %su (' % (top, '#(%s) ' % ov if ov else ''), '        ' + ',\n        '.join(conns), '    );', 'endmodule', ''])
        self._module_name = shim

    @property
    def module_name(self):
        return self._module_name

    def _create_this_vfile(self, path):
        if self._shim_text is None:
            return None
        import os
        f = os.path.join(path, '%s.sv' % self._module_name)
        with open(f, 'w') as fh:
            fh.write(self._shim_text)
        return f


    def _generate_filelist_core(self, prefix=''):
        if self.enable_filelist_generation:
            return super()._generate_filelist_core(prefix)
        else:
            return []
