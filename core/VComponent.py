import json
import re

from subprocess import Popen
from .Component import Component
from .Variable          import Wire,IOSig,IOGroup,Variable,Parameter,Reg,Output,Input,Inout,UInt,SInt,AnyConstant

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

    def get_width(self, type_string):
        struct_type = re.findall('struct packed{(.+)}\S+', type_string)
        if struct_type:
            return self.get_struct_width(struct_type[0])
        else:
            return self.get_vector_width(type_string)
        
    def get_struct_width(self, type_string):
        width = 0
        vectors = re.split(r'struct packed{[^{]*}\S+ \S+;', type_string)
        structs = re.findall(r'struct packed{([^{]*)}\S+ \S+;', type_string)
        for vec in vectors:
            if vec:
                vec_split = vec.split(';')
                for v in vec_split:
                    if v:
                        width += self.get_vector_width(v)
        for st in structs:
            if st:
                width += self.get_struct_width(st)
        return width

    def get_vector_width(self, type_string):
        width_res = re.search('\[([0-9]+)\:([0-9]+)\]', type_string)
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
        else:
            raise Exception()



class VComponent(Component):


    def __init__(self, filelist=None, top=None, file=None, slang_cmd='slang', slang_opts='--ignore-unknown-modules', **kwargs):
        super().__init__()
        self._module_name = top
        ast_json = "%s.ast.json" % top


        # Spell the parameter into the format needed by slang
        param_config = ''
        for k, v in kwargs.items():
            param_config = param_config + '-G %s=%s ' % (k,v)

        # Try slang
        p = Popen(f'{slang_cmd} --version', shell=True)
        p.communicate()
        if p.returncode != 0:
            raise Exception('Cannot call slang to import verilog.')


        # Call slang
        if file is not None:
            source = file
        else:
            source = f'-f {filelist}'
        cmd = f'{slang_cmd} {slang_opts} {source} -ast-json {ast_json} -top {top} {param_config}'
        p = Popen(cmd, shell=True)
        p.communicate()
        self.parse_ast(ast_json, top)


    def parse_ast(self, file, top_name):
        # parse json
        with open(file,'r') as f:
            data = json.loads(f.read())

        # get top instance
        top = None
        for member in data['members']:
            if member['name'] == top_name:
                top = member['body']
        if top is None:
            raise Exception()

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

    def _run_lint_single_lvl(self, lint, is_top=False):
        lint.info('Start to check VComponent module %s.' % self.module_name)

        # VComponent will only check input signal.
        # If VComp is a top module, nothing need to be checked.
        if not is_top:
            for lvalue in self.input_list:
                if lvalue.rvalue is None:
                    lint.unconnect(lvalue)


    @property
    def module_name(self):
        return self._module_name

    def create_this_vfile(self, path):
        pass