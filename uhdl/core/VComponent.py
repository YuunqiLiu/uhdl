import json
import re, os

import subprocess
from .Component import Component
from .Variable  import Wire,IOSig,Bundle,Variable,Parameter,Reg,Output,Input,Inout,UInt,SInt,AnyConstant
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
        width = re.search("\S+=(\d+)'[bodh]\d+[,]*", type_string)
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
        self._file = file
        self._module_name = top
        ast_json = "%s.%s.ast.json" %(top, instance)

        # Try slang
        p = subprocess.Popen(f'{slang_cmd} --version', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate()
        stdout, stderr = p.communicate()

        output_str = stdout.decode('utf-8')
        error_str = stderr.decode('utf-8')

        if p.returncode != 0:
            print('slang verion check fail.')
            print('stdout: %s' % stdout)
            print('stderr: %s' % stderr)

            raise Exception('Cannot call slang to import verilog.')



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
        p = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()

        output_str = stdout.decode('utf-8')
        error_str = stderr.decode('utf-8')

        #if error_str != '':

        if p.returncode != 0:
            print('slang error detect.')
            print('stdout: %s' % stdout)
            print('stderr: %s' % stderr)

        # Parse AST
        self.parse_ast(ast_json, top)


        # delete slang output
        os.remove(ast_json)


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

    def _run_lint_single_lvl(self, is_top=False):
        Terminal.lint_info('Start to check VComponent module %s.' % self.module_name)

        # VComponent will only check input signal.
        # If VComp is a top module, nothing need to be checked.
        if not is_top:
            for lvalue in self.input_list:
                if lvalue.rvalue is None:
                    Terminal.lint_unconnect(lvalue)

    def _generate_filelist_core(self,prefix=''):
        if prefix != '':
            name_list = [os.path.abspath(self._file)]
        else:
            name_list = [self._file]
        #name_list = ["%s/%s.v" % (prefix,self.module_name)]
        #for component in self.component_list:
        #    name_list += component._generate_filelist_core(prefix=prefix)
        return name_list


    @property
    def module_name(self):
        return self._module_name

    def _create_this_vfile(self, path):
        pass
