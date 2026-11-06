import re
from collections import OrderedDict

from pyslang import (Driver, CommandLineOptions, SyntaxTree,
                     Compilation, CompilationOptions, CompilationFlags,
                     SymbolKind, Bag, ArgumentDirection)

from .Component import Component
from .Variable  import (Wire, IOSig, IOGroup, InputStructIO, OutputStructIO,
                        InputEnumIO, OutputEnumIO, InputUnionIO, OutputUnionIO,
                        Variable, Parameter, Reg, Output, Input, Inout,
                        UInt, SInt, AnyConstant, StructType, StructConstant,
                        EnumType, EnumConstant, UnionType, UnionConstant)
from .Terminal  import Terminal


class VParameter(object):
    """Wrapper for a pyslang parameter symbol."""

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
    """Port descriptor built directly from pyslang type symbols.

    Replaces the old JSON-based parser with direct pyslang type introspection,
    eliminating all regex-based type string parsing.
    """

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
        self.width = port_type.bitWidth
        self.signed = port_type.isSigned

        # Detect actual type (resolve alias)
        actual_type = port_type
        if port_type.isAlias:
            actual_type = port_type.canonicalType

        # ---------- Enum detection ----------
        if actual_type.isEnum:
            self.is_enum = True
            if port_type.isAlias:
                hier = port_type.hierarchicalPath
                if '::' in hier:
                    self._enum_package = hier.split('::')[0]
                    self._enum_type_name = hier
                else:
                    self._enum_type_name = hier
            # Extract enum members
            members = OrderedDict()
            for mem in actual_type:
                if mem.kind == SymbolKind.EnumValue:
                    members[mem.name] = self._parse_enum_value(str(mem.value))
            self._enum_type_obj = EnumType.get_or_create(
                self._enum_type_name, members, self.width, self.signed, self._enum_package
            )

        # ---------- Packed Union detection ----------
        elif actual_type.isPackedUnion:
            self.is_union = True
            if port_type.isAlias:
                hier = port_type.hierarchicalPath
                if '::' in hier:
                    self._union_package = hier.split('::')[0]
                    self._union_type_name = hier
                else:
                    self._union_type_name = hier
            # Extract union fields
            for field in actual_type:
                finfo = {
                    'name': field.name,
                    'width': field.type.bitWidth,
                    'signed': field.type.isSigned,
                }
                # Detect nested struct/enum in union fields
                ft = field.type
                ft_canon = ft.canonicalType if ft.isAlias else ft
                if ft_canon.isStruct:
                    nested_st = self._build_struct_type_from_pyslang(ft, ft_canon)
                    finfo['struct_type'] = nested_st
                self._union_fields.append(finfo)
            # Build UnionType
            field_info = OrderedDict()
            for f in self._union_fields:
                fi = {'width': f['width'], 'signed': f['signed']}
                if 'struct_type' in f:
                    fi['struct_type'] = f['struct_type']
                field_info[f['name']] = fi
            self._union_type_obj = UnionType.get_or_create(
                self._union_type_name, field_info, self._union_package
            )

        # ---------- Struct detection ----------
        elif actual_type.isStruct:
            self.is_struct = True
            # Extract struct name and package from the typedef alias
            if port_type.isAlias:
                hier = port_type.hierarchicalPath
                if '::' in hier:
                    self.struct_package = hier.split('::')[0]
                    self.struct_type_name = hier
                else:
                    self.struct_type_name = hier
            # Extract field information with nested type support
            for field in actual_type:
                finfo = {
                    'name': field.name,
                    'width': field.type.bitWidth,
                    'signed': field.type.isSigned,
                }
                # Detect nested struct fields
                ft = field.type
                ft_canon = ft.canonicalType if ft.isAlias else ft
                if ft_canon.isStruct:
                    nested_st = self._build_struct_type_from_pyslang(ft, ft_canon)
                    finfo['struct_type'] = nested_st
                self.struct_fields.append(finfo)
            # Build or retrieve StructType
            field_info = OrderedDict()
            for f in self.struct_fields:
                fi = {'width': f['width'], 'signed': f['signed']}
                if 'struct_type' in f:
                    fi['struct_type'] = f['struct_type']
                field_info[f['name']] = fi
            self._struct_type_obj = StructType.get_or_create(
                self.struct_type_name, field_info, self.struct_package
            )

    @staticmethod
    def _parse_enum_value(val_str):
        """Parse pyslang enum value string like "2'b0" or "-4'sd2" to int."""
        import re
        # Match patterns like: 2'b01, 3'h7, 32'd42, -4'sd2
        m = re.match(r"(-?\d+)'[sS]?([dDbBhHoO])(.*)", val_str)
        if m:
            sign = -1 if m.group(0).startswith('-') else 1
            base_char = m.group(2).lower()
            digits = m.group(3).strip()
            bases = {'b': 2, 'o': 8, 'd': 10, 'h': 16}
            base = bases.get(base_char, 10)
            try:
                return sign * int(digits, base)
            except ValueError:
                return 0
        # Fallback: try direct int parse
        try:
            return int(val_str)
        except ValueError:
            return 0

    @staticmethod
    def _build_struct_type_from_pyslang(alias_type, canon_type):
        """Build a StructType from pyslang types for nested struct fields."""
        nested_name = None
        nested_pkg = None
        if alias_type.isAlias:
            hier = alias_type.hierarchicalPath
            if '::' in hier:
                nested_pkg = hier.split('::')[0]
                nested_name = hier
            else:
                nested_name = hier
        nested_fields = OrderedDict()
        for sf in canon_type:
            sft = sf.type
            sft_canon = sft.canonicalType if sft.isAlias else sft
            fi = {'width': sft.bitWidth, 'signed': sft.isSigned}
            # Recursive: nested struct within nested struct
            if sft_canon.isStruct:
                fi['struct_type'] = VPort._build_struct_type_from_pyslang(sft, sft_canon)
            nested_fields[sf.name] = fi
        return StructType.get_or_create(nested_name, nested_fields, nested_pkg)

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

        # Build slang command line for pyslang Driver
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
            import tempfile, os
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

        # Parse and compile using pyslang Driver
        driver = Driver()
        driver.addStandardArgs()
        ok = driver.parseCommandLine(cmd, CommandLineOptions())
        if not ok:
            raise Exception(f'Slang failed to parse command line: {cmd}')
        driver.processOptions()
        driver.parseAllSources()
        comp = driver.createCompilation()

        # Find top instance and extract ports/parameters
        root = comp.getRoot()
        top_inst = None
        if wrap_file is not None:
            os.unlink(wrap_file)
            for inst in root.topInstances:
                if inst.name == '__uhdl_vwrap':
                    for m in inst.body:
                        if m.kind == SymbolKind.Instance and m.name == 'u':
                            top_inst = m
        for inst in ([] if top_inst is not None else root.topInstances):
            if inst.name == top:
                top_inst = inst
                break

        if top_inst is None:
            # If only one top instance, use it regardless of name
            instances = list(root.topInstances)
            if len(instances) == 1:
                top_inst = instances[0]
            else:
                raise Exception(f"Top instance '{top}' not found in compilation")

        self._vport_list = []
        self._vparam_list = []
        self._shim_text = None

        bad = [m.name for m in top_inst.body if m.kind == SymbolKind.Port and m.type.bitWidth == 0
               and not (m.type.canonicalType if m.type.isAlias else m.type).isUnpackedArray]
        bad += [m.name for m in top_inst.body if m.kind == SymbolKind.Port
                and (m.type.canonicalType if m.type.isAlias else m.type).isUnpackedArray and m.type.elementType.bitWidth == 0]
        if bad:
            raise ErrUHDLStr('VComponent %s: slang could not resolve the type of port(s) %s (width 0). A package '
                             'or macro is probably missing from the sources; for macros defined in another file '
                             "try slang_opts='--ignore-unknown-modules --single-unit'." % (top, ', '.join(bad)))

        # Unpacked-array ports cannot be connected from UHDL's flat vectors. If there are any,
        # wrap the module in a generated SV shim whose ports are all packed (an unpacked array
        # of N elements of W bits becomes one N*W-bit port, element lo+k at bits [k*W +: W]).
        ports = [m for m in top_inst.body if m.kind == SymbolKind.Port]
        if any((m.type.canonicalType if m.type.isAlias else m.type).isUnpackedArray for m in ports):
            self._build_flat_shim(top, ports, kwargs)
            return

        for member in top_inst.body:
            if member.kind == SymbolKind.Port:
                direction = member.direction.name  # "In", "Out", "InOut"
                vport = VPort(member.name, direction, member.type, struct_mode=self._struct_mode)
                self._vport_list.append(vport)
            elif member.kind == SymbolKind.Parameter and not member.isLocalParam:
                vparam = VParameter(member.name, str(member.value))
                self._vparam_list.append(vparam)
            elif member.kind == SymbolKind.TypeParameter and member.name in type_params:
                self._vparam_list.append(VParameter(member.name, str(type_params[member.name])))

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
            t = m.type.canonicalType if m.type.isAlias else m.type
            d = {'In': 'input', 'Out': 'output'}.get(m.direction.name)
            if d is None:
                raise ErrUHDLStr('VComponent %s: inout port %s is not supported with unpacked-array ports.' % (top, m.name))
            if t.isUnpackedArray:
                el = t.elementType
                if (el.canonicalType if el.isAlias else el).isUnpackedArray:
                    raise ErrUHDLStr('VComponent %s: port %s has more than one unpacked dimension.' % (top, m.name))
                ew, rg = el.bitWidth, t.fixedRange
                n, lo = abs(rg.left - rg.right) + 1, min(rg.left, rg.right)
                width = n * ew
                body.append('    logic [%d:0] %s__a [%d:%d];' % (ew - 1, m.name, rg.left, rg.right))
                for k in range(n):
                    if d == 'input':
                        body.append('    assign %s__a[%d] = %s[%d +: %d];' % (m.name, lo + k, m.name, k * ew, ew))
                    else:
                        body.append('    assign %s[%d +: %d] = %s__a[%d];' % (m.name, k * ew, ew, m.name, lo + k))
                conns.append('.%s(%s__a)' % (m.name, m.name))
            else:
                width = t.bitWidth
                conns.append('.%s(%s)' % (m.name, m.name))
            decl.append('    %s logic %s%s' % (d, '' if width == 1 else '[%d:0] ' % (width - 1), m.name))
            io = Input if d == 'input' else Output
            self.create(m.name, io(UInt(width)))
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
