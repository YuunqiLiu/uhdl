import os
from operator       import concat
from functools      import reduce

from .Root          import Root
from .Variable      import Wire,IOSig,IOGroup,Variable,Parameter,Reg,Output,Input,Inout
from .              import FileProcess


class Component(Root):

    def __init__(self):
        super().__init__()
        #super(Component,self).__init__()
        self.set_father_type(Component)
        self.__vfile     = None
        self.output_path = './%s' % self.module_name

    @property
    def module_name(self):
        return type(self).__name__

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


    @property
    def param_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Parameter)]

    @property
    def var_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Variable)]

    @property
    def wire_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Wire,Reg,))]

    @property
    def io_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(IOSig,IOGroup))]

    @property
    def component_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Component) and k != '_father']

    @property
    def lvalue_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Wire,Reg,Output,))]

    @property
    def outer_lvalue_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Input,Inout,))] 

    @property
    def verilog_outer_def(self):
        return reduce(concat,[i.verilog_outer_def for i in self.io_list],[])

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
        str_list = ['module %s %s' % (self.module_name,'#(' if self.param_list else '(')]

        # parameter define
        if self.param_list:
            # pylint: disable=no-member
            str_list += self.__eol_append(reduce(concat,[i.verilog_def for i in self.param_list],[]),',','') + [')(']
            # pylint: enable=no-member

        # module io define
        str_list += self.__eol_append(self.__gen_aligned_signal_def([i.verilog_def_as_list for i in self.io_list]),',',');')

        # module wire define
        str_list += ['','\t//Wire define for this module.']
        str_list += self.__eol_append(self.__gen_aligned_signal_def([i.verilog_def_as_list for i in self.wire_list]),';',';')

        str_list += ['','\t//Wire define for sub module.']
        str_list += self.__eol_append(self.__gen_aligned_signal_def([i.verilog_outer_def_as_list for i in self.component_list]),';',';')

        # combine logic assignment
        str_list += ['','\t//Wire sub module connect to this module and inter module connect.']
        str_list += self.__eol_append(reduce(concat,[i.verilog_assignment for i in self.lvalue_list if i.verilog_assignment],[]),'')

        sub_io_list = reduce(concat,[i.outer_lvalue_list for i in self.component_list],[])
        str_list += ['','\t//Wire this module connect to sub module.']
        str_list += self.__eol_append(reduce(concat,[i.verilog_assignment for i in sub_io_list if i.verilog_assignment],[]),'')

        # component inst
        str_list += ['','\t//module inst.']
        str_list += self.__eol_append(reduce(concat,[i.verilog_inst for i in self.component_list],[]),'')

        str_list += ['','endmodule']
        return str_list


    @property
    def verilog_inst(self):
        param_assignment_list = reduce(concat,[i.verilog_assignment for i in self.param_list],[])
        
        str_list = ['%s %s %s' % (self.module_name,self.name,'#(' if param_assignment_list else '(')]

        if param_assignment_list:
            str_list += self.__eol_append(param_assignment_list,',','') + [')(']

        str_list += self.__eol_append(reduce(concat,[i.verilog_inst for i in self.io_list],[]),',',');')
        return str_list



    def create_this_vfile(self,path):
        FileProcess.create_file(os.path.join(path,'%s.v' % self.module_name),self.verilog_def)

    def create_all_vfile(self,path):
        self.create_this_vfile(path)
        for c in self.component_list:
            c.create_all_vfile(path)

    def generate_verilog(self,iteration=False):
        FileProcess.refresh_directory(self.output_path)
        if iteration:
            self.create_all_vfile(self.output_path)
        else:
            self.create_this_vfile(self.output_path)
            
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

def isComponent(obj):
    return isinstance(obj,Component)


        #print(list_in)
        #if len(list_in) == 1:
        #    return list_in
        #else:

        # io_inst_str_list = reduce(concat,[i.verilog_inst for i in self.io_list])
        # 
        # for i in io_inst_str_list[0:-1]:
        #     str_list.append('\t%s,' % i )
        # str_list.append('\t%s);' % io_inst_str_list[-1])

        # comp_inst_str_list = reduce(concat,[i.verilog_inst for i in self.component_list],[])
        # for i in comp_inst_str_list:
        #     str_list.append('\t%s' % i)

        # sub_assign_str_list = reduce(concat,[i.verilog_assignment for i in sub_io_list if i.verilog_assignment],[])
        # for i in sub_assign_str_list:
        #     str_list.append('\t%s;' % i)

        # assign_str_list = reduce(concat,[i.verilog_assignment for i in self.lvalue_list if i.verilog_assignment is not None],[])
        # for i in assign_str_list:
        #     str_list.append('\t%s;' % i)

        # sub_wire_def_str_list = reduce(concat,[i.verilog_outer_def for i in self.component_list],[])
        # for i in sub_wire_def_str_list:
        #     str_list.append('\t%s;' % i)

        # wire_def_str_list = reduce(concat,[i.verilog_def for i in self.wire_list],[])
        # for i in wire_def_str_list:
        #     str_list.append('\t%s;' % i)

        #io_def_str_list = 
        # for i in io_def_str_list[0:-1]:
        #     str_list.append('\t%s,' % i )
        # str_list.append('\t%s);' % io_def_str_list[-1])



    #@property
    #def output_list(self) -> list:
    #    return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Output)]
    #@property
    #def lvalue_list(self):
    #    return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Value)]

        #self.circuit()
    #def __new__(cls):
    #    obj = object.__new__(cls)
    #    obj.init()    
    #    return obj

#    #def __init__(self):
#    #    print('233')

    #def init(self):
    #    super(type(self),self).__init__()


        #Entity.__init__(self)
        # self.set_name(module_name)
        #self.__port = PortContainer(Interface)
        #self.__com  = ComponentContainer(Component)
        #self.__link_manager = LinkManager()
        #self.set_father(self.__port)
        #self.set_father(self.__com)
        #self.set_father(self.__link_manager)

    #def set_father_to_sub(self):
    #    for l in self.lvalue_list:
    #        self.set_father(l)

    #     p_def = self.__port.gen_rtl_def()
    #     text  = ['module %s(' % self.module_name]
    #     text += ['    %s,' % t for t in p_def[0:-1]] + ['    %s'% p_def[-1]] if len(p_def)>1 else ['    %s'% p_def[-1]]
    #     text += [');','']
    #     text += ['    %s' % t for t in self.__com.gen_rtl_io()] + ['']
    #     text += ['    %s' % t for t in self.__link_manager.gen_rtl_link()] + ['']
    #     text += ['    %s' % t for t in self.__com.gen_rtl_inst()]
    #     text += ['endmodule']

    # def gen_rtl_def(self):
    #     p_def = self.__port.gen_rtl_def()
    #     text  = ['module %s(' % self.module_name]
    #     text += ['    %s,' % t for t in p_def[0:-1]] + ['    %s'% p_def[-1]] if len(p_def)>1 else ['    %s'% p_def[-1]]
    #     text += [');','']
    #     text += ['    %s' % t for t in self.__com.gen_rtl_io()] + ['']
    #     text += ['    %s' % t for t in self.__link_manager.gen_rtl_link()] + ['']
    #     text += ['    %s' % t for t in self.__com.gen_rtl_inst()]
    #     text += ['endmodule']
    #     return text

    #@property
    #def port(self):
        #return self.__port
    #    pass

    #@property
    #def component(self):
        #return self.__com
    #    pass

    # def new(self,**args):
    #     for name,item in args.items():
    #         if hasattr(self,name):
    #             raise NameError("The name '%s' has used in this Component." % name)
    #         elif isinstance(item,Component):
    #             self.component.new(**{name:item})
    #         elif isinstance(item,Interface):
    #             self.port.new(**{name:item})
    #         else:
    #             raise TypeError("The item new in a Component should be a Port or a Component,should not be a %s" % type(item))
    #         setattr(self,name,item)

    # def link(self,*args):
    #     self.__link_manager.link(*args)

    #=============================================================================================
    # RTL gen 
    #=============================================================================================

    # def gen_rtl_io(self):
    #     return self.__port.gen_rtl_io()
    # 
    # def gen_rtl_inst(self):
    #     p_inst = self.__port.gen_rtl_inst()
    #     text   = ['%s %s (' %(self.module_name,self.name)]
    #     text  += ['    %s,' % t for t in p_inst[0:-1]] + ['    %s);'% p_inst[-1]] if len(p_inst)>1 else ['    %s);'% p_inst[-1]]
    #     #text  += [');']
    #     return text
    # 
    # def gen_rtl_def(self):
    #     p_def = self.__port.gen_rtl_def()
    #     text  = ['module %s(' % self.module_name]
    #     text += ['    %s,' % t for t in p_def[0:-1]] + ['    %s'% p_def[-1]] if len(p_def)>1 else ['    %s'% p_def[-1]]
    #     text += [');','']
    #     text += ['    %s' % t for t in self.__com.gen_rtl_io()] + ['']
    #     text += ['    %s' % t for t in self.__link_manager.gen_rtl_link()] + ['']
    #     text += ['    %s' % t for t in self.__com.gen_rtl_inst()]
    #     text += ['endmodule']
    #     return text

    #=============================================================================================
    # output verilog/file list generate
    #=============================================================================================

    #def check_vfile(self,func):



    #    return vfile

    #@FileProcess.check_vfile
    # def gen_vfile(self,path='-',recursion=True):
    #     path = self.output_path if path == '-' else path
    #     
    #     sub_vfile   = self.__com.gen_vfile(path=path,recursion=recursion)
    #     top_path    = FileProcess.create_file(  path = os.path.join(path,self.module_name+'.v'),
    #                                             text = self.gen_rtl_def())
    #     file_list   = FileProcess.file_list_dedup(reduce(concat,[p.file_list for p in sub_vfile],[]) + [top_path])
    #     
    #     #self.__vfile = VFile(path = path,top_path = top_path,file_list = file_list)
    #     #return self.__vfile
    #     return VFile(path = path,top_path = top_path,file_list = file_list)
    # 
    # 
    # def gen_flist(self,abs_path=False,path='-'):
    #     path = self.output_path if path == '-' else path
    #     FileProcess.create_file( path = os.path.join(path,'flist.f'),
    #                              text = [os.path.abspath(f) if abs_path else './'+os.path.relpath(f,path) for f in self.__vfile.file_list] )
    # 
    # 
    # def generate(self,abs_path=False,path='-',recursion=True):
    #     path = self.output_path if path == '-' else path
    # 
    #     FileProcess.refresh_directory(path)
    # 
    #     self.__vfile = self.gen_vfile(path=path,recursion=recursion)
    #     self.gen_flist(abs_path=abs_path,path=path)



        #if os.path.exists(path):
        #    shutil.rmtree(path)
            #os.remove(path)

        #file_list   = self.__file_list_process(reduce(concat,[p.file_list for p in sub_vfile],[]) + [top_path])
        #top_path    = self.__gen_file(path=path)


    #def __file_list_process(self,file_list):
    #    new_list=list(set(file_list))
    #    new_list.sort(key=file_list.index)
    #    return new_list 

        # if not os.path.exists(path):
        #     os.makedirs(path)
# 
        # f  = os.path.join(path,'flist.f')
        # if os.path.exists(f):
        #     os.remove(f)
# 
# 
        # 
# 
        # fp = open(f,'w')
        # #print(path)
        # #for f in self.__vfile.file_list:
        # #    print(f)
        # fp.write('\n'.join([os.path.abspath(f) if abs_path else './'+os.path.relpath(f,path) for f in self.__vfile.file_list]))
        # fp.close()


    #def __gen_file(self,path='./'):
    #    if not os.path.exists(path):
    #        os.makedirs(path)
#
    #    f  = os.path.join(path,'%s.v' % self.module_name)
    #    if os.path.exists(f):
    #        os.remove(f)
    #        
    #    fp = open(f,'w')
    #    fp.write('\n'.join(self.gen_rtl_def()))
    #    fp.close()
    #    
    #    return f 