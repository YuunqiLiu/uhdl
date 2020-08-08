
__all__ = ['assign','smart_assign','LCA','linkable',
           'join_name',
           'Component',
           'Input','Output','UInt','SInt','IOGroup','Parameter','Wire','Reg',
           'Combine','Equal','And','Or','LessEqual','GreaterEqual',
           'Circuit','get_circuit','set_circuit',
           'when']

from uhdl.Function  import assign,smart_assign,LCA,linkable
from uhdl.BasicFunction import join_name
from uhdl.Component import Component
from uhdl.Variable  import Input,Output,UInt,SInt,IOGroup,Parameter,Wire,Reg,Combine,Equal,IfExpression,And,Or,LessEqual,GreaterEqual
#from .Value     import Combine
#from .Expression import 
from uhdl.Root      import Root,get_circuit,set_circuit

Circuit = Root
when = IfExpression
