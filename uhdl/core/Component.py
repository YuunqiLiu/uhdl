import os, inspect, re
from operator           import concat
from functools          import reduce
from collections.abc    import Iterable
from .Terminal          import Terminal
from .Root              import Root
from .Variable          import Wire,IOSig,IOGroup,Variable,Parameter,Reg,Output,Input,Inout
from .                  import FileProcess

from .CustConfig        import ComponentConfig


UHDL_GLOBAL_PARAM_DICT = {}

class PARAM_CONTAINER(object):

    def _caculate_name(self):
        self.UHDL_MODU_NAME_POST_FIX = self.__caculate_iterable_kv(self.__dict__)
        self.UHDL_MODU_NAME_POST_FIX = self.UHDL_MODU_NAME_POST_FIX[2:-2]

    def __caculate_iterable_kv(self,iterable_param):
        res = 'S'
        for k,v in iterable_param.items():
            #print(k, v)
            res += '_%s_%s' % (k, v)
            #if    isinstance(v,(int,float,bool,str,)):
            #    res = res + '_%s_%s' %(k,v)
            #elif  isinstance(v,(dict,)):
            #    res = res + '_%s_%s' %(k,self.__caculate_iterable_kv(v))
            #elif  isinstance(v,Iterable):
            #    res = res + '_%s_%s' %(k,self.__caculate_iterable_varg(v))
            #else:
            #ID = id(v)
            #if ID in UHDL_GLOBAL_PARAM_DICT:
            #    seq = UHDL_GLOBAL_PARAM_DICT[ID]
            #    UHDL_GLOBAL_PARAM_DICT[ID] = seq + 1
            #else:
            #    seq = 0
            #    UHDL_GLOBAL_PARAM_DICT[ID] = 0
            #    res = res + '_%s_%s%s' %(k,type(v).__name__,str(seq))
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
                res = res + '_' + type(item) + str(seq)
        res = res + '_E'
        return res



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
        self.circuit()


    def circuit(self):
        pass


    @property
    def output_path(self):
        return '%s/%s' % (self.output_dir, self.module_name)

    def create(self, name, val):
        setattr(self, name, val)
        return getattr(self, name)

    @property
    def PARAM(self):
        return self._PARAM

    def set_module_name_prefix(self, prefix):
        self._module_name_prefix = prefix

    @property
    def module_name_prefix(self):
        return self._module_name_prefix if self.father is None else self.father.module_name_prefix

    @property
    def module_name(self):
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

    @property
    def inter_sig_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Wire,Reg,))]

    @property
    def input_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Input)]
    
    @property
    def inout_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Inout)]

    @property
    def output_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Output)]

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
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Input, Output, IOGroup))]


    @property
    def component_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],Component) and k != '_father']

    @property
    def lvalue_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Wire,Reg,Output,))]

    @property
    def outer_lvalue_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],(Input,))] 

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
        str_list += self.__eol_append(self.__gen_aligned_signal_def([i.verilog_def_as_list for i in self.inter_sig_list]),';',';')

        str_list += ['','\t//Wire define for sub module.']
        str_list += self.__eol_append(self.__gen_aligned_signal_def(reduce(concat,[i.verilog_outer_def_as_list for i in self.component_list],[])),';',';')

        # module wire define for inout
        str_list += ['','\t//Wire define for Inout.']
        str_list += self.__eol_append(self.__gen_aligned_signal_def(reduce(concat,[i.verilog_inout_def_as_list for i in self.component_list],[])),';',';')

        # combine logic assignment
        str_list += ['','\t//Wire sub module connect to this module and inter module connect.']
        str_list += self.__eol_append(reduce(concat,[i.verilog_assignment +[''] for i in self.lvalue_list if i.verilog_assignment],[]),'')

        sub_io_list = reduce(concat,[i.outer_lvalue_list for i in self.component_list],[])
        str_list += ['','\t//Wire this module connect to sub module.']
        str_list += self.__eol_append(reduce(concat,[i.verilog_assignment +[''] for i in sub_io_list if i.verilog_assignment],[]),'')

        # component inst
        str_list += ['','\t//module inst.']
        str_list += self.__eol_append(reduce(concat,[i.verilog_inst for i in self.component_list],[]),'')

        str_list += ['','endmodule']
        return str_list


    @property
    def verilog_inst(self):
        param_assignment_list = reduce(concat,[i.verilog_assignment for i in self.param_list],[])

        if param_assignment_list:
            str_list = ['%s #(' % self.module_name]
            str_list += self.__eol_append(param_assignment_list,',',')')
            str_list += ['%s (' % self.name]
        else:
            str_list = ['%s %s (' % (self.module_name, self.name)]

        str_list += self.__eol_append(reduce(concat,[i.verilog_inst for i in self.io_list],[]),',',');')
        return str_list

#################################################################################
# Verilog File Opeartion
#################################################################################

    def _create_this_vfile(self,path):
        FileProcess.create_file(os.path.join(path,'%s.v' % self.module_name),self.verilog_def)

    def _create_all_vfile(self,path):
        self._create_this_vfile(path)
        for c in self.component_list:
            c._create_all_vfile(path)

    def generate_verilog(self,iteration=False):
        FileProcess.refresh_directory(self.output_path)
        if iteration:
            self._create_all_vfile(self.output_path)
        else:
            self._create_this_vfile(self.output_path)


    def _generate_filelist_core(self,prefix=''):
        name_list = ["%s/%s.v" % (prefix,self.module_name)]
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

    def _run_lint_core(self, is_top=False):
        for component in self.component_list:
            component._run_lint_core()
        self._run_lint_single_lvl(is_top=is_top)

    def run_lint(self):
        self._run_lint_core(is_top=True)


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
        cmd = 'slang -f %s' % self._flist_path
        print('Run command: %s' % cmd)
        slang_res = os.system(cmd)
        if slang_res != 0:
            raise Exception('Slang compile error.')

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

    def expose_io(self, io_list):
        for io in io_list:
            sub_inst = io._father
            if self != sub_inst._father:
                raise Exception()
            new_io_name = 'D_%s_%s' % (sub_inst.name, io.name)
            new_io = self.set(new_io_name, io.template())

            if isinstance(new_io, Input):
                io += new_io
            elif isinstance(new_io, Output):
                new_io += io
            elif isinstance(new_io, Inout):
                new_io += io
            else:
                raise Exception()

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






















    #def isComponent(obj):
    #    return isinstance(obj,Component)
    # def compile(self):
    #     self.run_undriven_check()

    #     pass

    # def run_undriven_check(self):
    #     undriven_check_list = self.wire_list + self.reg_list + self.output_list

    #     for i in undriven_check_list:
    #         if i.rvalue == None:
    #             raise Exception('%s is undriven' % i.name)


    # def run_struct_check(self):
    #     pass


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
    #             self.Component.new(**{name:item})
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
