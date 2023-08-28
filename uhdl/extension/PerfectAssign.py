from uhdl.uhdl import *
# from uhdl.uhdl.core.Variable import *
import warnings
import re

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
        'axi_aruser',   
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

def match_io(io_list, pattern):
    match_io_list=[]
    for io in io_list:
        if re.search(pattern, io.name):
                match_io_list.append(io)
    return match_io_list


def perfect_assign(src, dst, io_list, ignore_list=[], src_prefix='', dst_prefix='', src_suffix='', dst_suffix=''):
    for io in io_list:
        if io not in ignore_list:
            src_list = src.get_io('(?i)'+io)
            dst_list = dst.get_io('(?i)'+io)

            src_pre_list = match_io(src_list, '^'+src_prefix)
            dst_pre_list = match_io(dst_list, '^'+dst_prefix)

            src_intf = match_io(src_pre_list, src_suffix+'$')
            dst_intf = match_io(dst_pre_list, dst_suffix+'$')

            if src_intf == [] : warnings.warn('Interface \'%s\' Was Not Found'% (src_prefix+io+src_suffix));continue
            elif dst_intf == [] : warnings.warn('Interface \'%s\' Was Not Found'% (dst_prefix+io+dst_suffix));continue

            SmartAssign(src_intf, dst_intf)


def single_assign(op1, op2):
    if isinstance(op1, Inout) and isinstance(op2, Inout):
        op1 += op2
    elif isinstance(op1, (Input, Output)) and isinstance(op2, (Input, Output)):
        SmartAssign(op1, op2)
    
    elif isinstance(op1, (Input, Output)):
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
            raise Exception("Hierachy Error, there is a bug")
        
    elif isinstance(op2, (Input, Output)):
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
            raise Exception("Hierachy Error, there is a bug")
        
    else:
        raise Exception("Both op1 and op2 are Wire or One op is not Inout")


def unconnect_port(component, op1):
    if isinstance(op1, list):
        for io in op1:
            unconnect_port(component, io)
    elif isinstance(op1, core.Variable.Variable):
        op2 = component.set(f'{op1.name}_unconnect', Wire(UInt(op1.width)))
        op2 += op1


def perfect_expose_io(component=None, object=None, io_list=[], prefix='',suffix='',has_prefix=True):
    if io_list == []:
        component.expose_io(object, has_prefix)
    elif isinstance(object, Component):
        for io in io_list:
            print(io)
            expose_list = object.get_io('(?i)'+io)
            expose_pre_list = match_io(expose_list, '^'+prefix)
            expose_intf = match_io(expose_pre_list, suffix+'$')
            component.expose_io(expose_intf, has_prefix)
    else:
        raise Exception("io_list exist, but object is not component.")
