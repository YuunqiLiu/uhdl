
__all__ = [ 'assign','smart_assign','LCA','linkable','Unpack',
            'Assign','SmartAssign','Linkable','Exclude',
            'join_name',
            'Component','VComponent','SvType',

            'Input','Output','Inout','InputStructIO','OutputStructIO','InputEnumIO','OutputEnumIO','InputUnionIO','OutputUnionIO','UInt','SInt','IOGroup','Parameter','Wire','Reg','AnyConstant',
            'StructType','StructConstant','StructFieldRef',
            'EnumType','EnumConstant',
            'UnionType','UnionConstant','UnionFieldRef',
            'And','Or','Greater','Less','GreaterEqual','LessEqual','NotEqual','Equal',
            'BitXnor','BitXor','BitAnd','BitOr',
            'Add','Sub','Mul','WrapAdd','WrapSub','Mem','Cat','If','Mux','Priority','CdcSync','CdcBus','AsyncFifo','check_cdc','Struct','Stream','import_sv_package',
            'SelfXnor','SelfXor','SelfAnd','SelfOr','Inverse','Not',
            'Combine','BitXnorList','BitXorList','BitOrList','BitAndList','OrList','AndList',

            'Cut','Case','When','EmptyWhen','Fanout','BitMask',
            'Circuit','get_circuit','set_circuit',
            'when','Bundle',

            'Config','UHDLException','MultiFileExec','MultiFileScope']

from .Component     import Component
from .VComponent    import VComponent, SvType
from .Function      import Assign,SmartAssign,LCA,Linkable,Unpack,BitMask,Exclude
from .BasicFunction import join_name

from .Variable      import Input,Output,Inout,InputStructIO,OutputStructIO,InputEnumIO,OutputEnumIO,InputUnionIO,OutputUnionIO,UInt,SInt,IOGroup,Parameter,Wire,Reg,AnyConstant
from .Variable      import StructType,StructConstant,StructFieldRef
from .Variable      import EnumType,EnumConstant
from .Variable      import UnionType,UnionConstant,UnionFieldRef
from .Operator      import And,Or,Greater,Less,GreaterEqual,LessEqual,NotEqual,Equal
from .Operator      import BitXnor,BitXor,BitAnd,BitOr
from .Operator      import Add,Sub,Mul,WrapAdd,WrapSub,Cat,If,Mux,Priority
from .Variable      import Mem
from .Operator      import SelfXnor,SelfXor,SelfAnd,SelfOr,Inverse,Not
from .Operator      import Combine,BitXnorList,BitXorList,BitOrList,BitAndList,OrList,AndList
from .Operator      import Case,Cut,When,EmptyWhen,Fanout
from .Variable      import Bundle
from .CdcCells      import CdcSync, CdcBus, AsyncFifo
from .Cdc           import check_cdc
from .Struct        import Struct, Stream, import_sv_package
from .              import Config
from .              import UHDLException
from .              import InternalTool
from .MultiFileCoop import MultiFileExec, MultiFileScope

from .Root          import Root,get_circuit,set_circuit

Circuit      = Root
when         = When
assign       = Assign
smart_assign = SmartAssign
linkable     = Linkable

from .UHDLException import *


def __getattr__(name):
    if name in ('TemplateIP', 'TemplateIPConfig', 'TemplateComponent'):
        raise ImportError('TemplateIP moved to the ip_builder repository: from ip_builder.uhdl_template_ip import TemplateIPConfig, TemplateComponent')
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
