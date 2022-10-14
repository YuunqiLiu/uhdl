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
        width_res = re.search('\[([0-9]+)\:([0-9]+)\]',type_string)
        if width_res:
            high = int(width_res.groups()[0])
            low = int(width_res.groups()[1])
            self.width = high - low + 1
        else:
            self.width = 1

        sign_res = re.search('signed',type_string)
        if sign_res:
            self.signed = True
        else:
            self.signed = False

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


    def __init__(self, file, top):
        super().__init__()
        self._module_name = top
        ast_json = "%s.ast.json" % top
        p = Popen('slang -v %s -ast-json %s --top %s' % (file, ast_json, top), shell=True)
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
            if member['kind'] == 'Parameter':
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





    @property
    def module_name(self):
        return self._module_name

    def create_this_vfile(self, path):
        pass