import json
import re, os

from subprocess import Popen, PIPE
from .Component import Component
from .Variable  import Wire,IOSig,IOGroup,Variable,Parameter,Reg,Output,Input,Inout,UInt,SInt,AnyConstant
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

    def __init__(self, ast_dict):
        self.name = ast_dict['name']
        self.direction = ast_dict['direction']
        
        type_string = ast_dict['type']        
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

    def create_uhdl_port(self):
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


    def __init__(self, file=None, top=None, instance=None, slang_cmd='slang', slang_opts='--ignore-unknown-modules', **kwargs):
        super().__init__()
        self.enable_filelist_generation = False
        self._module_name = top
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

        for member in top['members']:
            if member['kind'] == 'Parameter' and not member['isLocal']:
                parameter_list.append(member)
            if member['kind'] == 'Port':
                port_list.append(member)

        self._vport_list = [VPort(x) for x in port_list]
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