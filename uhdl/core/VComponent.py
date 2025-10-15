import json
import re, os

from subprocess import Popen, PIPE
from .Component import Component
from .Variable  import Wire,IOSig,IOGroup,StructIOGroup,Variable,Parameter,Reg,Output,Input,Inout,UInt,SInt,AnyConstant
from .Terminal  import Terminal

class VParameter(object):


    def __init__(self, ast_dict):
        self.name = ast_dict['name']
        self.value = ast_dict['value']

    def create_uhdl_param(self):
        return Parameter(AnyConstant(self.value))

        if self.direction == "Out":
            if self.signed:
                return Output(SInt(self.width))
            else:
                return Output(UInt(self.width))
        elif self.direction == "In":
            if self.signed:
                return Input(SInt(self.width))
            else:
                return Input(UInt(self.width))
        elif self.direction == "InOut":
            if self.signed:
                return Inout(SInt(self.width))
            else:
                return Inout(UInt(self.width))
        else:
            raise Exception()



class VPort(object):

    def __init__(self, ast_dict, type_aliases=None, struct_mode: str = 'auto'):
        self.name = ast_dict['name']
        self.direction = ast_dict['direction']
        self._type_aliases = type_aliases or {}
        self._struct_mode = struct_mode
        
        type_string = ast_dict['type']
        # detect struct types via inline 'struct packed{' or typedef alias
        self.is_struct = self._is_struct_type(type_string)
        self.struct_fields = []
        if self.is_struct and self._struct_mode != 'packed':
            # try to parse fields for group modeling; fallback to width-only
            try:
                self.struct_fields = self._parse_struct_fields(type_string)
            except Exception:
                self.struct_fields = []
        self.width = self.get_width(type_string)

        sign_res = re.search('signed',type_string)
        if sign_res:
            self.signed = True
        else:
            self.signed = False

    def parse_type(self, type_string):
        type_string_list = list(type_string)
        parse_res = list()
        item = list()
        stack = list()
        op_log = list()
        start = 0
        for i,c in enumerate(type_string):
            if c == '{':
                stack.append(i)
                type_string_list[start:i+1] = ['' for i in range(i-start+1)]
                op_log.append([i, '{'])
                item.clear()
                start = i+1
            elif c == '}':
                start = stack.pop()
                iter_res = self.parse_type(''.join(type_string_list[start+1:i]))
                if iter_res != '':
                    parse_res.extend(iter_res)
                    type_string_list[start:i+1] = ['' for i in range(i-start+1)]
                op_log.append([i, '}'])
                item.clear()
                start = i+1
            elif c == ';':
                if not op_log or op_log[-1][1] != '}':
                    parse_res.append(''.join(item))
                op_log.append([i, ';'])
                type_string_list[start:i+1] = ['' for i in range(i-start+1)]
                item.clear()
                start = i+1
            else:
                item.append(c)
        if item and (not op_log or op_log[-1][1] != '}'):
            parse_res.append(''.join(item))
        return parse_res

    def get_width(self, type_string):
        # If this is a struct type, prefer summing parsed field widths
        if getattr(self, 'is_struct', False):
            fields = getattr(self, 'struct_fields', None)
            if not fields:
                # parse ad-hoc in case struct_mode prevented earlier parsing
                try:
                    fields = self._parse_struct_fields(type_string)
                except Exception:
                    fields = None
            if fields:
                return sum(int(f.get('width', 1)) for f in fields)
        # Fallback: sum vector widths for simple types
        width = 0
        type_list = self.parse_type(type_string)
        for t in type_list:
            width += self.get_vector_width(t)
        return width

    def get_enum_width(self, type_string):
        width = re.search(r"\S+=(\d+)'[bodh]\d+[,]*", type_string)
        return int(width.groups()[0])

    # def get_struct_width(self, type_string):
    #     width = 0
    #     vectors = re.split(  r'struct packed{[^{]*}\S+ \S+;', type_string)
    #     structs = re.findall(r'struct packed{([^{]*)}\S+ \S+;', type_string)
    #     # print(vectors)
    #     # print(structs)
    #     for vec in vectors:
    #         if vec:
    #             vec_split = vec.split(';')
    #             for v in vec_split:
    #                 if v:
    #                     width += self.get_vector_width(v)
    #     for st in structs:
    #         if st:
    #             width += self.get_struct_width(st)
    #     return width

    def get_vector_width(self, type_string):
        if '=' in type_string:
            return self.get_enum_width(type_string)
        else:
            width_res = re.search(r'\[([0-9]+):([0-9]+)\]', type_string)
            if width_res:
                high = int(width_res.groups()[0])
                low = int(width_res.groups()[1])
                return high-low+1
            else:
                return 1

    def _is_struct_type(self, type_string: str) -> bool:
        if 'struct packed' in type_string:
            return True
        # typedef alias case like pkg::my_struct_t or my_struct_t
        base = type_string.strip()
        # strip vector ranges
        base = re.sub(r'\[[^\]]+\]', '', base)
        # strip extra spaces
        base = re.sub(r'\s+', ' ', base).strip()
        # only a bare typename contains '::' or identifier
        if '::' in base or base.isidentifier():
            target = self._type_aliases.get(base)
            if isinstance(target, str) and 'struct packed' in target:
                return True
        return False

    def _parse_struct_fields(self, type_string: str):
        # inline struct
        target = None
        if 'struct packed' in type_string:
            target = type_string
        else:
            base = re.sub(r'\[[^\]]+\]', '', type_string).strip()
            base = re.sub(r'\s+', ' ', base)
            target = self._type_aliases.get(base)
        if not target:
            return []
        # extract body: struct packed{...}
        m = re.search(r'struct\s+packed\s*\{([^}]*)\}', target)
        if not m:
            return []
        body = m.group(1)
        # split by ';' and filter empties
        decls = [d.strip() for d in body.split(';') if d.strip()]
        fields = []
        for d in decls:
            # d like: logic [3:0] a  OR  pkg::enum_t state  OR  logic b
            parts = d.split()
            if not parts:
                continue
            name = parts[-1]
            ts = d[: d.rfind(name)].strip()
            signed = bool(re.search(r'\bsigned\b', ts))
            # width from vector or typedef/enum
            w = 1
            vec = re.search(r'\[([0-9]+):([0-9]+)\]', ts)
            if vec:
                hi, lo = int(vec.group(1)), int(vec.group(2))
                w = hi - lo + 1
            else:
                # typedef width via alias -> may use $bits registry in future
                alias_target = self._type_aliases.get(ts)
                if alias_target:
                    # best-effort parse enum width: look for N'b
                    m2 = re.search(r"(\d+)'[bodh]", alias_target)
                    if m2:
                        w = int(m2.group(1))
            fields.append({'name': name, 'width': w, 'signed': signed})
        return fields

    def create_uhdl_port(self):
        # struct -> StructIOGroup if enabled and fields parsed
        if getattr(self, 'is_struct', False) and self._struct_mode != 'packed' and self.struct_fields:
            g = StructIOGroup()
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
                    raise Exception()
                g.add_field(f['name'], sig)
            return g
        if self.direction == "Out":
            if self.signed:
                return Output(SInt(self.width))
            else:
                return Output(UInt(self.width))
        elif self.direction == "In":
            if self.signed:
                return Input(SInt(self.width))
            else:
                return Input(UInt(self.width))
        elif self.direction == "InOut":
            if self.signed:
                return Inout(SInt(self.width))
            else:
                return Inout(UInt(self.width))
        else:
            raise Exception()



class VComponent(Component):


    def __init__(self, file=None, top=None, instance=None, slang_cmd='slang', slang_opts='--ignore-unknown-modules', struct_mode: str = 'auto', **kwargs):
        super().__init__()
        self.enable_filelist_generation = False
        self._module_name = top
        self._struct_mode = struct_mode
        ast_json = "%s.%s.ast.json" %(top, instance)

        # Try slang
        p = Popen(f'{slang_cmd} --version', shell=True, stdout=PIPE, stderr=PIPE)
        _out, _err = p.communicate()
        if p.returncode != 0:
            raise Exception(f'Cannot call slang to import verilog. stderr: {(_err or b"").decode(errors="ignore").strip()}')


        # Spell the parameter into the format needed by slang
        param_config = ''
        for k, v in kwargs.items():
            param_config = param_config + '-G %s=%s ' % (k,v)


        # Call slang
        if str(file).endswith('.f'):
            source = f'-f {file}'
        else:
            source = file
        
        cmd = f'{slang_cmd} {slang_opts} {source} -ast-json {ast_json} -top {top} {param_config}'
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        _out, _err = p.communicate()
        if p.returncode != 0:
            raise Exception(f'Slang failed to parse design. stderr: {(_err or b"").decode(errors="ignore").strip()}')


        # Parse AST
        self.parse_ast(ast_json, top)


        # delete slang output
        os.remove(ast_json)


    def parse_ast(self, file, top_name):
        # parse json
        with open(file,'r') as f:
            data = json.loads(f.read())

        # get top instance (support legacy and newer slang JSON shapes)
        top = None
        members = None
        if isinstance(data, dict):
            if 'members' in data and isinstance(data['members'], list):
                members = data['members']
            elif 'design' in data and isinstance(data['design'], dict) and isinstance(data['design'].get('members'), list):
                members = data['design']['members']
        if members is None:
            raise KeyError("Invalid AST JSON: cannot find 'members' at top or under 'design'.")
        for member in members:
            if member.get('name') == top_name:
                # some slang versions place instance body at 'body'
                top = member.get('body') or member
        if top is None:
            raise Exception(f"Top instance '{top_name}' not found in AST JSON")

        parameter_list = []
        port_list = []
        # Build type alias registry: map qualified/unqualified to target string
        type_aliases = {}

        # Walk all root members to collect TypeAlias with package context
        def collect_aliases(node, pkg=None):
            if isinstance(node, dict):
                kind = node.get('kind')
                name = node.get('name')
                if kind == 'Package':
                    for m in node.get('members', []):
                        collect_aliases(m, pkg=name)
                elif kind == 'TypeAlias':
                    target = node.get('target')
                    if name and target:
                        qname = f"{pkg}::{name}" if pkg else name
                        type_aliases[qname] = target
                        # also map unqualified (best-effort)
                        type_aliases[name] = target
                else:
                    for m in node.get('members', []) if isinstance(node.get('members'), list) else []:
                        collect_aliases(m, pkg)
        # gather from either top-level 'design' or 'members'
        roots = []
        if isinstance(data, dict) and 'design' in data and isinstance(data['design'], dict):
            roots = [data['design']]
        else:
            roots = [data]
        for r in roots:
            for m in r.get('members', []) if isinstance(r.get('members'), list) else []:
                collect_aliases(m, None)

        for member in top['members']:
            if member['kind'] == 'Parameter' and not member['isLocal']:
                parameter_list.append(member)
            if member['kind'] == 'Port':
                port_list.append(member)

        self._vport_list = [VPort(x, type_aliases=type_aliases, struct_mode=self._struct_mode) for x in port_list]
        self._vparam_list = [VParameter(x) for x in parameter_list]

        for vport in self._vport_list:
            self.create(vport.name, vport.create_uhdl_port())

        for vparam in self._vparam_list:
            #print(vparam.name)
            res = self.create(vparam.name, vparam.create_uhdl_param())
            #print(res)

    def _run_lint_single_lvl(self, is_top=False):
        Terminal.lint_info('Start to check VComponent module %s.' % self.module_name)

        # VComponent will only check input signal.
        # If VComp is a top module, nothing need to be checked.
        if not is_top:
            for lvalue in self.input_list:
                if lvalue.rvalue is None:
                    Terminal.lint_unconnect(lvalue)




    @property
    def module_name(self):
        return self._module_name

    def _create_this_vfile(self, path):
        pass


    def _generate_filelist_core(self, prefix=''):
        if self.enable_filelist_generation:
            return super()._generate_filelist_core(prefix)
        else:
            return []