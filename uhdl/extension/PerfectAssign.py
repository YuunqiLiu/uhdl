from .. import *
# from uhdl.uhdl.core.Variable import *
import warnings
import re
from ..core.Terminal import Terminal
import inspect,linecache


class axi_intf():
    io_list = [
        'axi_awid',     
        'axi_awaddr',   
        'axi_awlen',    
        'axi_awsize',   
        'axi_awburst',  
        'axi_awlock',   
        'axi_awcache',  
        'axi_awprot',   
        'axi_awqos',    
        'axi_awuser',   
        'axi_awvalid',  
        'axi_awready',  
        'axi_wdata',    
        'axi_wstrb',    
        'axi_wlast',    
        'axi_wuser',    
        'axi_wvalid',   
        'axi_wready',   
        'axi_bid',      
        'axi_bresp',    
        'axi_buser',    
        'axi_bvalid',   
        'axi_bready',   
        'axi_arid',  
        'axi_araddr',   
        'axi_arlen',    
        'axi_arsize',   
        'axi_arburst',  
        'axi_arlock',   
        'axi_arcache',  
        'axi_arprot',   
        'axi_arqos',    
        'Axi_aruser',   
        'axi_arvalid',  
        'axi_arready',  
        'axi_rid',      
        'axi_rdata',    
        'axi_rresp',    
        'axi_rlast',    
        'axi_ruser',    
        'axi_rvalid',   
        'axi_rready'  
        ]

    ignore_list = [
        'axi_awid',
        'axi_arid'
    ]
    def __init__(self) -> None:
        pass

def match_io(io_list, pattern, prefix, suffix):
    match_io_list=[]
    for io in io_list:
        io_name = io.name
        if io_name.startswith(prefix) and io_name.endswith(suffix) and pattern.casefold() in io_name.casefold():
            if len(io_name)==(len(prefix)+len(pattern)+len(suffix)):
                match_io_list.append(io)
    return match_io_list


def perfect_assign(src, dst, io_list, ignore_list=[], src_prefix='', dst_prefix='', src_suffix='', dst_suffix=''):
    for io in io_list:
        if io not in ignore_list:
            # src_list = src.get_io('(?i)'+io)
            # dst_list = dst.get_io('(?i)'+io)

            # src_pre_list = match_io(src_list, '^'+src_prefix+io)
            # dst_pre_list = match_io(dst_list, '^'+dst_prefix+io)

            # src_intf = match_io(src_pre_list, io+src_suffix+'$')
            # dst_intf = match_io(dst_pre_list, io+dst_suffix+'$')
            src_intf = match_io(src.io_list, io, src_prefix, src_suffix)
            dst_intf = match_io(dst.io_list, io, dst_prefix, dst_suffix)

            # if src_intf == [] : warnings.warn('Interface \'%s\' Was Not Found'% (src_prefix+io+src_suffix));continue
            if src_intf == [] :
                Terminal.error('Interface \'%s\' Was Not Found, %s'% (src_prefix+io+src_suffix, get_log_info()))
                continue
            elif dst_intf == [] : 
                Terminal.error('Interface \'%s\' Was Not Found, %s'% (dst_prefix+io+dst_suffix, get_log_info()))
                continue

            single_assign(src_intf, dst_intf)


def single_assign(op1, op2, outer=False):

    if isinstance(op1, Bundle) and isinstance(op2, Bundle):
        op1_list = op1.as_list()
        op2_list = op2.as_list()

        for opl, opr in zip(op1_list, op2_list):
            single_assign(opl, opr, outer)

    elif isinstance(op1, list) and isinstance(op2, list):
        for opl, opr in zip(op1, op2):
            single_assign(opl, opr, outer)

    else:
        single_assign_core(op1, op2, outer)


def single_assign_core(op1, op2, outer):
    if isinstance(op1, Inout) and isinstance(op2, Inout):
        if op1 in op2._inout_connect_list:  pass
        else:                               op1 += op2

    elif isinstance(op1, (Input, Output)) and isinstance(op2, (Input, Output)):
        if isinstance(op1, Input) and op1.rvalue == op2:        pass
        elif isinstance(op1, Output) and op2.rvalue == op1:     pass
        else:                                                   smart_assign_core__(op1, op2, outer)
    
    elif isinstance(op1, (Input, Output)):
        if op1._rvalue != None and isinstance(op1, Input) and op1.rvalue.__dict__ == op2.__dict__ or \
           op2._rvalue != None and isinstance(op1, Output) and op2._rvalue.__dict__  == op1.__dict__ :
            pass
        else:
            op1_component = op1.father_until(Component)
            if isinstance(op1_component, VComponent):
                if isinstance(op1, Input):
                    op1 += op2
                else:
                    op2 += op1
            elif isinstance(op1_component, Component):
                if isinstance(op1, Input):
                    op2 += op1
                else:
                    op1 += op2
            else:
                Terminal.error("Hierachy Error, there is a bug with %s and %s, %s"% (op1.full_hier, op2.full_hier, get_log_info()))
        
    elif isinstance(op2, (Input, Output)):
        if op2._rvalue != None and isinstance(op2, Input) and op2.rvalue.__dict__ == op1.__dict__ or \
           op1._rvalue != None and isinstance(op2, Output) and op1.rvalue.__dict__ == op2.__dict__:
            pass
        else:
            op2_component = op2.father_until(Component)
            if isinstance(op2_component, VComponent):
                if isinstance(op2, Input):
                    op2 += op1
                else:
                    op1 += op2
            elif isinstance(op2_component, Component):
                if isinstance(op2, Input):
                    op1 += op2
                else:
                    op2 += op1 
            else:
                Terminal.error("Hierachy Error, there is a bug with %s and %s, %s"% (op1.full_hier, op2.full_hier, get_log_info()))
        
    else:
        Terminal.error("Both %s and %s are Wire or One op is not Inout, %s"% (op1.full_hier, op2.full_hier, get_log_info()))


def perfect_unconnect_port(component=None, object=None, io_list=[], prefix='', suffix=''):
    if io_list==[]:
        unconnect_port(component, object)
    elif isinstance(object, Component):
        for io in io_list:
            # expose_list = object.get_io('(?i)'+io)
            # expose_pre_list = match_io(expose_list, '^'+prefix)
            # expose_intf = match_io(expose_pre_list, suffix+'$')
            # print(io_list, io, prefix, suffix)
            expose_intf = match_io(object.io_list, io, prefix, suffix)
            unconnect_port(component, expose_intf)
    else:
        Terminal.error("[Unconnect Error] io_list exist, but %s is not component, %s"% (object, get_log_info()))


def unconnect_port(component, op1):
    if isinstance(op1, list):
        for io in op1:
            unconnect_port(component, io)
    elif isinstance(op1, core.Variable.Variable):
        op2 = component.set(f'{op1.name}_unconnect', Wire(UInt(op1.width)))
        single_assign(op1, op2)


def perfect_expose_io(component=None, object=None, io_list=[], prefix='',suffix='',has_prefix=True):
    print('Object is', isinstance(object, Component))
    if io_list == []:
        component.expose_io(object, has_prefix)
    elif isinstance(object, Component):
        for io in io_list:
            # expose_list = object.get_io('(?i)'+io)
            # expose_pre_list = match_io(expose_list, '^'+prefix)
            # expose_intf = match_io(expose_pre_list, suffix+'$')
            # print(io_list, io, prefix, suffix)
            expose_intf = match_io(object.io_list, io, prefix, suffix)
            component.expose_io(expose_intf, has_prefix)
    else:
        Terminal.error("[Expose Error] io_list exist, but %s is not component, %s"% (object, get_log_info()))


def expand_vector(component,vec):
    vec_list = []
    for i in range(getattr(component,vec).width):
        if not hasattr(component, f'{vec}_bit{i}'):
            setattr(component, f'{vec}_bit{i}', Wire(UInt(1))) 
            vec_list.append(getattr(component, f'{vec}_bit{i}'))
        else:   return -1

    Assign(component.intr_vec, Combine(*vec_list))


def cut_assign(component, opl, opr):
    if opl.attribute!=opr.attribute:
        Terminal.error("Left Value %s not equal Right Value %s, %s"% (opl,opr, get_log_info()))
    else:
        if isinstance(opl, core.Variable.CutExpression) and isinstance(opr, core.Variable.CutExpression):
            for i in range(opl.lbound, opl.hbound+1):
                if hasattr(component, f'{opl.op.name}_bit{i}'):
                    if getattr(component, f'{opl.op.name}_bit{i}').rvalue==None: Assign(getattr(component, f'{opl.op.name}_bit{i}'), getattr(component, f'{opr.op.name}')[opr.lbound+i-opl.lbound])
                    elif getattr(component, f'{opl.op.name}_bit{i}').rvalue.__dict__ == getattr(component, f'{opr.op.name}')[opr.lbound+i-opl.lbound].__dict__: pass
                    else: Terminal.error("%s has multi-driver , %s"% (f'{opl.op.full_hier}_bit{i}', get_log_info()))
                else:
                    Terminal.error("%s does not exist, %s"% (f'{opl.op.full_hier}_bit{i}', get_log_info()))
        elif isinstance(opl, core.Variable.CutExpression):
            for i in range(opl.lbound, opl.hbound+1):
                if hasattr(component, f'{opl.op.name}_bit{i}'):
                    if getattr(component, f'{opl.op.name}_bit{i}').rvalue==None: Assign(getattr(component, f'{opl.op.name}_bit{i}'), opr[i-opl.lbound])
                    elif getattr(component, f'{opl.op.name}_bit{i}').rvalue.__dict__ == opr[i-opl.lbound].__dict__: pass
                    else: Terminal.error("%s has multi-driver , %s"% (f'{opl.op.full_hier}_bit{i}', get_log_info()))
                else:
                    Terminal.error("%s does not exist in %s , %s"% (f'{opl.op.name}_bit{i}', component, get_log_info()))
        elif isinstance(opr, core.Variable.CutExpression):
            for i in range(opl.attribute.width):
                if hasattr(component, f'{opl.name}_bit{i}'):
                    if getattr(component, f'{opl.name}_bit{i}').rvalue==None: Assign(getattr(component, f'{opl.name}_bit{i}'), getattr(component, f'{opr.op.name}')[i])
                    elif getattr(component, f'{opl.name}_bit{i}').rvalue.__dict__==getattr(component, f'{opr.op.name}')[i].__dict__: pass
                    else: Terminal.error("%s has multi-driver , %s"% (f'{opl.full_hier}_bit{i}', get_log_info()))
                else:
                    Terminal.error("%s does not exist in %s , %s"% (f'{opl}_bit{i}', component, get_log_info()))  
        else:
            for i in range(opl.attribute.width):
                if hasattr(component, f'{opl.name}_bit{i}'):
                    if getattr(component, f'{opl.name}_bit{i}').rvalue==None: Assign(getattr(component, f'{opl.name}_bit{i}'), getattr(component, f'{opr.name}')[i])
                    elif getattr(component, f'{opl.name}_bit{i}').rvalue.__dict__==getattr(component, f'{opr.name}')[i].__dict__: pass
                    else: Terminal.error("%s has multi-driver , %s"% (f'{opl.full_hier}_bit{i}', get_log_info()))
                else:
                    Terminal.error("%s does not exist in %s , %s"% (f'{opl.name}_bit{i}', component, get_log_info())) 



def get_log_info(depth=1):
    current_frame = inspect.currentframe()
    for i in range(depth):
        if current_frame.f_back == None: break
        current_frame = current_frame.f_back
        caller_frame = inspect.getframeinfo(current_frame)
        filename = caller_frame.filename
    caller_frame = inspect.getframeinfo(current_frame)
    filename = caller_frame.filename
    
    while 'PerfectAssign.py' in filename:
        # inner case
        current_frame = current_frame.f_back
        caller_frame = inspect.getframeinfo(current_frame)
        filename     = caller_frame.filename

    if filename == '<string>':
        # dynamic exec case
        current_frame = current_frame.f_back
        caller_frame = inspect.getframeinfo(current_frame)
        filename     = caller_frame.filename

    if 'MultiFileCoop.py' in filename:
        # dynamic exec case
        caller_frame = inspect.getframeinfo(current_frame.f_back)
        filename     = caller_frame.filename
    

    if current_frame == None:
        return "cannot trace file"
    else:
        line_content = linecache.getline(filename, caller_frame.lineno)
        line_num = caller_frame.lineno

        message = 'maybe it can be fixed in file %s at line %s:\n%s'% (filename, line_num, line_content)
        return message
    


def smart_assign_core__(op1, op2, outer=False):
    op1_component = op1.father_until(Component)
    op2_component = op2.father_until(Component)

    if isinstance(op1, (Input, Output)) and isinstance(op2, (Input, Output)):
        if op1_component.father is op2_component:
            # op1 in low level
            #    ----------------------
            #    |                    |
            #    |    ---------       |
            #    |    |       |       |
            #    |    |  (op1)-  (op2)|
            #    |    |       |       |
            #    |    ---------       |
            #    |                    |
            #    ----------------------
            #
            #   case1:
            #       op1 is Input, op1 should be lhs.
            #   case2:
            #       op1 is Output, op1 should be rhs.
            #
            if isinstance(op1, Input):
                op1 += op2
            elif isinstance(op1, Output):
                op2 += op1
            else:
                Terminal.error("op1 %s's father Component is in op2 %s's father Component, so op1 should be Input or Output, %s" % (op1.full_hier, op2.full_hier, get_log_info(depth=2)))

        elif op2_component.father is op1_component:
            # op2 in low level
            #    ----------------------
            #    |                    |
            #    |    ---------       |
            #    |    |       |       |
            #    |    |  (op2)-  (op1)|
            #    |    |       |       |
            #    |    ---------       |
            #    |                    |
            #    ----------------------
            #
            #   case1:
            #       op2 is Input, op2 should be lhs.
            #   case2:
            #       op2 is Output, op2 should be rhs.
            #
            if isinstance(op2, Input):
                op2 += op1
            elif isinstance(op2, Output):
                op1 += op2
            else:
                Terminal.error("op2 %s's father Component is in op1 %s's father Component, so op2 should be Input or Output, %s" % (op2.full_hier, op1.full_hier, get_log_info(depth=2)))

        elif op1_component is op2_component:
            if outer:
                # outer connection.
                #    -------------------
                #    |                 |
                #  ---(op1)-------(op2)---
                #  | |                 | |
                #  | ------------------- |
                #  |                     |
                #  -----------------------
                if isinstance(op1, Input) and isinstance(op2, Output):
                    op1 += op2
                elif isinstance(op2, Input) and isinstance(op1, Output):
                    op2 += op1
                else:
                    Terminal.error("op1 %s and op2 %s have same father Component, so op1 and op2 should have different direction, %s" % (op1.full_hier, op2.full_hier,get_log_info(depth=2)))

            else:
                # inter connection.
                #    -------------------
                #    |                 |
                #    -(op1)-------(op2)-
                #    |                 |
                #    -------------------
                if isinstance(op1, Input) and isinstance(op2, Output):
                    op2 += op1
                elif isinstance(op2, Input) and isinstance(op1, Output):
                    op1 += op2
                else:
                    Terminal.error("op1 %s and op2 %s have same father Component, so op1 and op2 should have different direction. %s" % (op1.full_hier, op2.full_hier, get_log_info(depth=2)))

        elif op1_component.father is op2_component.father:
            # same level connection.
            #    ------------------   ------------------
            #    |                |   |                |
            #    |           (op1)-   -(op2)           |
            #    |                |   |                |
            #    ------------------   ------------------
            if isinstance(op1, Input) and isinstance(op2, Output):
                op1 += op2
            elif isinstance(op2, Input) and isinstance(op1, Output):
                op2 += op1
            else:
                Terminal.error("op1 %s's father Component and op2 %s's father Component are in same Component, so op1 and op2 should have different direction, %s" % (op1.full_hier, op2.full_hier, get_log_info(depth=2)))

        else:
            # illegal hier.
            Terminal.error("The hier where op1 %s and op2 %s are located cannot be legally connected, %s" % (op1.full_hier, op2.full_hier, get_log_info(depth=2)))