import re

from functools  import reduce
from operator   import concat
from copy       import copy
import string
from collections import OrderedDict
from .Root      import Root
from .AreaCalculator import get_area_for_object

from .UHDLException import *
from .InternalTool  import *

from .types import (TypeKernel, TypedConstant,
                    StructType, StructConstant,
                    EnumType, EnumConstant,
                    UnionType, UnionConstant)

def simplified_connection_naming_judgment(lvalue_obj, rvalue_obj):
    lvalue_comp_name = lvalue_obj.father_until_component().name
    rvalue_comp_name = rvalue_obj.father_until_component().name
    sig_name         = lvalue_obj.name_before_component
    return "%s_TO_%s_SIG_%s" % (lvalue_comp_name, rvalue_comp_name, sig_name)

def low_to_high_connection(low, high):
    return True if low.father_until_component().father == high.father_until_component() else False

def same_level_connection(a, b):
    return True if a.father_until_component().father == b.father_until_component().father else False

def same_module_connection(a, b):
    return True if a.father_until_component() == b.father_until_component() else False

def is_input_port(sig):
    """Check if a signal is an input-type port (Input, InputStructIO, InputEnumIO, or InputUnionIO)."""
    try:
        return isinstance(sig, (Input, InputStructIO, InputEnumIO, InputUnionIO))
    except NameError:
        return type(sig).__name__ in ('Input', 'InputStructIO', 'InputEnumIO', 'InputUnionIO')

def is_output_port(sig):
    """Check if a signal is an output-type port (Output, OutputStructIO, OutputEnumIO, or OutputUnionIO)."""
    try:
        return isinstance(sig, (Output, OutputStructIO, OutputEnumIO, OutputUnionIO))
    except NameError:
        return type(sig).__name__ in ('Output', 'OutputStructIO', 'OutputEnumIO', 'OutputUnionIO')
#   Root
#       Variable
#       Bundle
#   ValueRoot
#       Value
#           Expression
#               Constant
#                   Bits
#                       UInt
#                       SInt
#       Value, Variable
#           SingleVar
#               WireSig
#                   IOSig
#                       Input
#                       Output
#                       Inout
#                   Wire
#               Reg


class Variable(Root):

    def __init__(self):
        super().__init__()
        self._rvalue = None
        #self._des_lvalue = None
        self._lvalue_list = []

    @property
    def rvalue(self):
        return self._rvalue

    @property
    def lvalue(self):
        return self._lvalue_list[0]
    
    @property
    def _des_lvalue(self):
        return None if self._lvalue_list == [] else self._lvalue_list[0]

    def add_lvalue(self,lvalue):
        self._lvalue_list.append(lvalue)

    @property
    def single_connection(self):
        return True if len(self._lvalue_list) <= 1 else False



    @property
    def name_until_component(self):
        from .Component import Component
        return self.name_until(Component)

    @property
    def name_before_component(self):
        from .Component import Component
        return self.name_before(Component)
    
    def __str__(self):
        return "%s - %s(%s)" % (self.name_before(None), self.__class__.__name__, self.attribute)

    @property
    def attribute(self):
        raise NotImplementedError

    def get_area(self) -> float:
        """
        Get the normalized area of this variable/circuit element.
        Base implementation returns area based on signal width.
        
        Returns:
            float: The normalized area of this circuit element
        """
        if hasattr(self, 'attribute') and hasattr(self.attribute, 'width'):
            width = self.attribute.width
            return width * 0.01  # Base area per bit
        else:
            return 0.01  # Default minimal area

    @property
    def var_name(self):
        return self.__class__.__name__

    # += as circuit assignment
    def __iadd__(self,rvalue):
        from .Component import Component
        # check whether variable used in Assign belongs to component.
        # rvalue may be expression, so it's no need to check them.
        if not isinstance(self.father, Component):
            raise_ErrVarNotBelongComponent(self)
        if not isinstance(rvalue,Value):                        
            raise_ErrAssignTypeWrong(self,rvalue)
        if self.attribute != rvalue.attribute:  
            self_full_hier = self.full_hier if hasattr(self, 'full_hier') else 'NoneType'
            rvalue_full_hier = rvalue.full_hier if hasattr(rvalue, 'full_hier') else 'NoneType'
            raise_ErrAttrMismatch('%s is expected to be connected by a Rvalue with same attribute,but the current attribute does not match: %s, %s' % (self.var_name, self_full_hier, rvalue_full_hier), self, rvalue)
        
        # check io first:
        #TODO: for inout assign
        if isinstance(self, Output) and isinstance(rvalue, Inout):
            self_module = self.father_until(Component)
            rvalue_module = rvalue.father_until(Component)
            if rvalue_module is not None and (self_module is rvalue_module or self_module is rvalue_module.father):
                rvalue._need_assign = [self]
            
        elif isinstance(self, Inout) or isinstance(rvalue, Inout):
            updated_list = list(set(self._inout_connect_list + rvalue._inout_connect_list))
            for item in updated_list:
                item._inout_connect_list = updated_list


        if self._rvalue != None:
            existing_driver = self._rvalue.full_hier if hasattr(self._rvalue, 'full_hier') else str(self._rvalue)
            new_driver = rvalue.full_hier if hasattr(rvalue, 'full_hier') else str(rvalue)
            Terminal.error(f'Error: {self.full_hier} has multi-driver\n'
                          f'  Existing driver: {existing_driver}\n'
                          f'  New driver:      {new_driver}')
        object.__setattr__(self, '_rvalue', rvalue)
        rvalue.add_lvalue(self)

        self_module = self.father_until(Component)
        # Determine the module context of RHS for legality checks.
        # - Pure Expressions have no owning component context (treat as None)
        # - CutExpression may wrap either a Variable/Value (has component) or another Expression (no component)
        if isinstance(rvalue, Expression):
            if isinstance(rvalue, CutExpression):
                r_op = rvalue.op
                # If cutting an Expression, treat as expression (no module)
                if isinstance(r_op, Expression) or not hasattr(r_op, 'father_until'):
                    rvalue_module = None
                else:
                    rvalue_module = r_op.father_until(Component)
            else:
                rvalue_module = None
        else:
            rvalue_module = rvalue.father_until(Component)

        if isinstance(self, Inout) and isinstance(rvalue, Inout):
            # inout connection, give up all check.
            pass
        elif isinstance(self, Output) and isinstance(rvalue, Inout):
            #TODO: add two case
            if rvalue_module is not None:
                if self_module is rvalue_module:
                    pass 
                elif self_module is rvalue_module.father:
                    pass
                else: 
                    raise ErrUHDLStr("Inout connect error, The hier where lhs %s and rhs %s are located cannot be legally connected." % (self.full_hier, rvalue.full_hier))
            else:
                raise ErrUHDLStr("Inout connect error, rhs %s Componet is None." % (rvalue.full_hier))
                    
        elif (isinstance(self, Inout) and not isinstance(rvalue, Inout)) or\
           (not isinstance(self, Inout) and isinstance(rvalue, Inout)):
            # inout connect to other type, error.
            raise Exception('inout signal %s connect to other type'% (self.full_hier))
        
        elif isinstance(rvalue, Expression):
            # rvalue is expression, lvalue can be all signal.
            pass
        elif rvalue_module is not None:
            if self_module is rvalue_module:
                # internal connection.
                #    -------------------
                #    |                 |
                #    |  (lhs)  (rhs)   |
                #    |                 |
                #    -------------------
                if isinstance(self, Input):
                    # raise ErrUHDLStr("lhs %s and rhs %s have same father Component %s, bus lhs is Input, it\'s illegal." % (self.full_hier, rvalue.full_hier, self_module))
                    pass
            elif self_module.father is rvalue_module.father:
                # same level connection.
                #    ------------------   ------------------
                #    |                |   |                |
                #    |          (lhs)<-   <-(rhs)          |
                #    |                |   |                |
                #    ------------------   ------------------
                if not is_input_port(self):
                    raise ErrUHDLStr("lhs %s's father Component and rhs %s's father Component are in same Component, so lhs should be Input." % (self.full_hier, rvalue.full_hier))
            elif self_module.father is rvalue_module:
                # lhs in low level
                #    ----------------------
                #    |                    |
                #    |    ---------       |
                #    |    |       |       |
                #    |    | (lhs)<-  (rhs)|
                #    |    |       |       |
                #    |    ---------       |
                #    |                    |
                #    ----------------------
                if not is_input_port(self):
                    raise ErrUHDLStr("lhs %s's father Component is in rhs %s's father Component, so lhs should be Input." % (self.full_hier, rvalue.full_hier))
            elif self_module is rvalue_module.father:
                # rhs in low level
                #    ----------------------
                #    |                    |
                #    |    ---------       |
                #    |    |       |       |
                #    |    | (rhs)->  (lhs)|
                #    |    |       |       |
                #    |    ---------       |
                #    |                    |
                #    ----------------------
                if not is_output_port(rvalue):
                    raise ErrUHDLStr("rhs %s's father Component is in lhs %s's father Component, so rhs should be Output." % (self.full_hier, rvalue.full_hier))
                if is_input_port(self):
                    raise ErrUHDLStr("rhs %s's father Component is in lhs %s's father Component, so lhs should not be Input." % (self.full_hier, rvalue.full_hier))
            else:
                # illegal hier.
                raise ErrUHDLStr("The hier where lhs %s and rhs %s are located cannot be legally connected." % (self.full_hier, rvalue.full_hier))
        else:
            # rvalue is a unregsitered signal.
            raise ErrUHDLStr("rhs %s does not have a legal component father, it may not be registered into a component." % rvalue.full_hier)
        return self


    @property
    def _need_always(self):
        return (self._rvalue and isinstance(self._rvalue, AlwaysCombExpression)) or isinstance(self, Reg)


    @property
    def verilog_assignment(self) -> str:
        if not hasattr(self, '_rvalue') or self._rvalue is None:
            return []
        # a tmp hack
        
        if isinstance(self, IOSig) and isinstance(self._rvalue, IOSig):
            if not self._rvalue.single_connection:
                if low_to_high_connection(self, self._rvalue): 
                    return []
                else: 
                    pass
            #TODO: for inout assign
            elif is_output_port(self) and isinstance(self._rvalue, Inout):
                if self.father_until_component() == self._rvalue.father_until_component().father:
                    if len(self._rvalue._inout_connect_list)<=1:    return [] 
                    else:                                           pass
                elif self.father_until_component() == self._rvalue.father_until_component():
                    pass
                else:
                    return []
            elif is_output_port(self) and is_input_port(self._rvalue) and\
            self.father_until_component() == self._rvalue.father_until_component():
                pass
            elif is_output_port(self._rvalue) and\
            self.father_until_component() == self._rvalue.father_until_component() and not self.single_connection:
                pass
            else:
                return []
        elif (is_input_port(self) and isinstance(self._rvalue, Wire)) or \
             (isinstance(self, Wire) and is_output_port(self._rvalue)):
                if is_input_port(self) and self._rvalue._rvalue==None:
                    return [] # for input unconnect port
                elif isinstance(self, Wire) and self._lvalue_list==[]:
                    if self._rvalue.single_connection:
                        return [] # for output unconnect port
                    else:
                         Terminal.error('output %s has unconnect port, but connect to other signal'% self._rvalue.full_hier)
                else:
                    pass
        
        # TODO: inout
        sig_name = None
        if isinstance(self._rvalue, Inout):
            min_lvl_var = self._rvalue._inout_connect_list[0]
            for var in self._rvalue._inout_connect_list:
                if var.level_until_root() < min_lvl_var.level_until_root():
                    min_lvl_var = var
            
            # all signal in same level.
            # if min_lvl_var.level_until_root() == self._inout_connect_list[0].level_until_root() and len(self._inout_connect_list)>1:
            if len(self._rvalue._inout_connect_list)>1:
                sig_name = min_lvl_var.name_until_component
            # has high level io.
            else:
                sig_name = self._rvalue.name_before_component
        
        if self._need_always:
            str_list    = self._rvalue.bstring(self,"=")
            str_list[0] = "always @(*) %s" % str_list[0]
            return str_list
        else:
            # For certain RHS forms, emit via a temporary wire for better Verilog compatibility.
            rv = self._rvalue
            # If slicing an expression (e.g., (a+b)[h:l] or (a*b)[h:l]), create a temp wire:
            #   tmp = (expr);
            #   assign lhs = tmp[h:l];
            # This avoids tools rejecting part-selects on expressions and preserves widened widths.
            from .Component import Component

            if isinstance(rv, CutExpression) and isinstance(rv.op, Expression):
                comp = self.father_until(Component)
                # Build a stable, unique temp name per LHS
                base_tmp = f"{self.name_before_component}_cut_tmp"
                tmp_name = base_tmp
                # Avoid collision if the name already exists with a different width
                idx = 0
                while hasattr(comp, tmp_name):
                    exist = getattr(comp, tmp_name)
                    if isinstance(exist, Wire) and getattr(exist, 'attribute', None) == rv.op.attribute:
                        tmp_wire = exist
                        break
                    idx += 1
                    tmp_name = f"{base_tmp}_{idx}"
                else:
                    tmp_wire = comp.create(tmp_name, Wire(rv.op.attribute))
                    # Connect temp wire to the expression
                    tmp_wire += rv.op

                if rv.hbound == rv.lbound:
                    rhs_str = f"{tmp_wire.name_before_component}[{rv.lbound}]"
                else:
                    rhs_str = f"{tmp_wire.name_before_component}[{rv.hbound}:{rv.lbound}]"
                return ['assign ' + str(self.lstring) + ' = ' + rhs_str + ';']

            # Default simple assign path
            if sig_name == None:
                return ['assign ' + str(self.lstring) + ' = ' + str(self._rvalue.rstring(self)) + ';']
            else:
                return ['assign ' + str(self.lstring) + ' = ' + str(sig_name) + ';']

class Bundle(Root):


    def __init__(self):
        super().__init__()
        self._rvalue = None
        self._var_list = []

    @property
    def rvalue(self):
        return self._rvalue

    @property
    def name_until_component(self):
        return self.name_until_not(Bundle)

    @property
    def name_before_component(self):
        return self.name_before_not(Bundle)

    @property
    def attribute(self):
        raise NotImplementedError

    def __setattr__(self, name, value):
        if not hasattr(self, "_var_list") or value not in self._var_list:
            if isinstance(value, (Bundle, Variable)):
                self._var_list.append(value)
            super().__setattr__(name, value)

    def _setattr_hook(self):
        from .Component import Component
        component_father = self.father_until(Component)
        for value in self._var_list:
            setattr(component_father, value.name_before(Component), value)

    @property
    def io_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],IOSig)]



    def reverse(self):
        reverse = Bundle()
        for i in self.io_list:
            if self.name is None:
                setattr(reverse, i.name, i.reverse())
            else:
                prefix = '%s_'%self.name
                if i.name.startswith(prefix):
                    result = i.name[len(prefix):]
                else:
                    result = i.name
                setattr(reverse, result, i.reverse())
        return reverse




    def as_list(self, exclude=None):
        exclude_list = [] if exclude is None else exclude
        res_list = []


        exclude_list = ['%s_%s' % (self.name, item) for item in exclude_list]
        for var in self._var_list:
            if var.name not in exclude_list:
                res_list.append(var)
        return res_list


    def connect(self, other):
        pass

    def exclude(self, *args):
        result = copy(self)
        for a in args:
            delattr(result, a)
        return result

class ValueRoot():
    pass

class Value(ValueRoot):

    def __init__(self):
        super().__init__()
        self._rvalue     = None

    def __str__(self):
        return "%s - %s" % (self.__class__.__name__,self.attribute)


    def check_rvalue(self, op: ValueRoot):
        '''This function is used to check the validity of rvalue, rvalue must be of type ValueRoot or its subclass.'''
        if not isinstance(op, ValueRoot):
            raise ErrExpInTypeWrong('', self, op)
        op.add_lvalue(self)


    def __getitem__(self, s:slice):
        if isinstance(s, slice):
            return CutExpression(self, s.start, s.stop)
        elif isinstance(s, int):
            return CutExpression(self, s, s)
        else:
            raise Exception()
            return None

    #def Cut(self, hbound:int, lbound:int):
    #    return CutExpression(self, hbound, lbound)

    def __add__(self, rhs):
        return AddExpression(self, rhs)

    def __sub__(self, rhs):
        return SubExpression(self, rhs)

    def __mul__(self, rhs):
        return MulExpression(self, rhs)

    def __and__(self, rhs):
        return BitAndExpression(self, rhs)

    def __or__(self, rhs):
        return BitOrExpression(self, rhs)

    def __xor__(self, rhs):
        return BitXorExpression(self, rhs)

    def __invert__(self):
        return InverseExpression(self)

    def __lshift__(self, rhs):
        return LeftShift(self, rhs)

    def __rshift__(self, rhs):
        return RightShift(self, rhs)


    # Redefining comparison-related operators can lead to logical abnormalities such as sorting

    # def __lt__(self,rhs):
    #     return Less(self,rhs)

    # def __le__(self,rhs):
    #     return LessEqual(self,rhs)
 
    # def __gt__(self,rhs):
    #     return Greater(self,rhs)
 
    # def __ge__(self,rhs):
    #     return GreaterEqual(self,rhs)
 
    # def __eq__(self,rhs):
    #     return Equal(self,rhs)
 
    # def __ne__(self,rhs):
    #     return NotEqual(self,rhs)

    @property
    def lstring(self):
        raise NotImplementedError

    #@property
    def rstring(self, lvalue):
        raise NotImplementedError

    def bstring(self, lvalue, assign_method) -> str:
        return [" ".join([lvalue.lstring, assign_method, self.rstring(lvalue)]) + ";"]

    @property
    def attribute(self):
        raise NotImplementedError


    @property
    def des_connect(self):
        return self._des_lvalue

    @property
    def src_connect(self):
        return self._rvalue


    def father_until_component(self):
        return None


    def add_lvalue(self,dontcare):
        pass

class SingleVar(Variable, Value):

    def __init__(self,template):
        super().__init__()
        if not isinstance(template, (Constant, StructConstant, EnumConstant, UnionConstant)): raise ErrAttrTypeWrong(self, template)
        object.__setattr__(self, '_template', template)
        #self.__template = template

    @property
    def width(self):
        return self._template.width

    @property
    def lstring(self):
        return self.name_before_component #self.__name

    def rstring(self, lvalue):
        return self.name_before_component #self.__name

    @property
    def attribute(self):
        return self._template

class WireSig(SingleVar):
    pass

class Reg(SingleVar):
    '''
    Reg is used to define a register in Component in UHDL. 

        UInt/SInt T          - type template
        rhs       C          - UInt(1)
        rhs       R          - UInt(1) (default=None)
        bool      asyncrst   - True for aysnc reset,False for sync reset. (default=True)
        bool      rstactive  - True for low active,False for high acitve. (default=False)
        bool      clkactive  - True for negedge trigger,False for posedge trigger. (default=False)

    Reg needs a UHDL constant as a template to declare its type. 
    Its type will be consistent with the constants they use as templates.

    Reg needs a signal as its clock.

    Reg needs a signal as its reset.

    Reg also requires 3 Boolean variables to determine the effective level of reset, reset mode, and clock trigger edge.

    A typical example is

            Reg(UInt(32),clk,rst)

    This example describes a register whose clock is clk, reset is rst, and the type is an unsigned 32-bit integer.
    And this register is triggered on the rising edge of the clock, using low level asynchronous reset.

    Another example is

            Reg(SInt(16),clk,rst,False,True,True)

    This example describes a register whose clock is clk, reset is rst, and the type is an signed 16-bit integer.
    And this register is triggered on the falling edge of the clock, using high level synchronous reset.

    '''
    def __init__(self,template,clk:SingleVar,rst:SingleVar=None,async_rst:bool=True,rst_active_low:bool=True,clk_active_neg:bool=False):
        super().__init__(template=template)
        # input value check
        self.check_rvalue(clk)
        if rst is not None: self.check_rvalue(rst)
        if not isinstance(async_rst     ,bool): raise ErrNeedBool('Reg\'s input async_rst need a bool value,bug get a %s'      % async_rst.__class__.__name__)
        if not isinstance(rst_active_low,bool): raise ErrNeedBool('Reg\'s input rst_active_low need a bool value,bug get a %s' % rst_active_low.__class__.__name__)
        if not isinstance(clk_active_neg,bool): raise ErrNeedBool('Reg\'s input clk_active_neg need a bool value,bug get a %s' % clk_active_neg.__class__.__name__)
        self._aclk           = None
        self._rst            = None
        self._async_rst      = None
        self._rst_active_low = None
        self._clk_active_neg = None
        object.__setattr__(self,'_aclk',clk)
        object.__setattr__(self,'_rst',rst)
        object.__setattr__(self,'_async_rst',async_rst)
        object.__setattr__(self,'_rst_active_low',rst_active_low)
        object.__setattr__(self,'_clk_active_neg',clk_active_neg)

    @property
    def verilog_assignment(self) -> str:
        if not hasattr(self,'_rvalue') or self._rvalue is None:
            return []
        else:
            sensitivity_list = [("negedge" if self._clk_active_neg else "posedge") + " " + self._aclk.rstring(self)]
            if self._rst and self._async_rst:
                sensitivity_list += [("negedge" if self._rst_active_low else "posedge") + " " + self._rst.rstring(self)]

            str_list = ['always @(%s) begin' %(" or ".join(sensitivity_list))]

            if self._rst:
                str_list += ['    if(%s%s) %s <= %s;' % ('~' if self._rst_active_low else '',self._rst.rstring(self), self.lstring,self.attribute.rstring(self))] 
                tmp_str_list = self._rvalue.bstring(self,'<=')
                tmp_str_list[0] = '    else %s' % tmp_str_list[0]
                tmp_str_list[1:] = ['    %s' % x for x in tmp_str_list[1:]]
                str_list += tmp_str_list
            else:
                tmp_str_list = self._rvalue.bstring(self,'<=')
                tmp_str_list[0] = '    %s' % tmp_str_list[0]
                tmp_str_list[1:] = ['    %s' % x for x in tmp_str_list[1:0]]
                str_list += tmp_str_list
            str_list += ['end']
            return str_list

    @property
    def verilog_def(self):
        '''生成端口定义的RTL'''
        return ['reg [%s:0] %s' % ((self.attribute.width-1),self.name_before_component)]
    
    @property
    def verilog_def_as_list(self):
        return ['reg','[%s:0]'%((self.attribute.width-1)),self.name_before_component]

    def get_area(self) -> float:
        """
        Get the normalized area of this register.
        Uses the unified area calculation system.
        
        Returns:
            float: The normalized area of this register
        """
        return get_area_for_object(self)

class Wire(WireSig):
    '''
    Wire is used to declare an internal signal wire in Component in UHDL.

    Wire needs a UHDL constant as a template to declare its type. 
    Its type will be consistent with the constants they use as templates.

    A typical example is

            Wire(UInt(32))

    The type of Wire in this example will be consistent with UInt(32), 
    that is, it is a 32-bit unsigned integer.
    '''
    #=============================================================================================
    # RTL gen 
    #=============================================================================================

    # @property
    # def verilog_inst(self):
    #     '''生成端口实例化的RTL'''
    #     return [".%s(%s)" %(self.name_before(Component),self.name_until(Component))]

    @property
    def verilog_def(self):
        '''生成端口定义的RTL'''
        def_keyword = 'reg' if self._need_always else 'wire'
        return ['%s [%s:0] %s' % (def_keyword,(self.attribute.width-1),self.name_before_component)]
    
    @property
    def verilog_def_as_list(self):
        def_keyword = 'reg' if self._need_always else 'wire'
        return [def_keyword,'[%s:0]'%(self.attribute.width-1),self.name_before_component]

    def get_area(self) -> float:
        """
        Get the normalized area of this wire.
        Wires are just connections and have no physical area.
        
        Returns:
            float: Always 0.0 for wires
        """
        return 0.0

class IOSig(WireSig):

    @property
    def verilog_inst(self):
        '''生成端口实例化的RTL'''
        #if self.father_until_component().father == self._rvalue.father_until_component().father:
        #    return [".%s(pre_fix_%s)" %(self.name_before_component, self._rvalue.name_until_component)]
        #if self.father_until_component().father == self._rvalue.father_until_component():
        #    return [".%s(%s)" %(self.name_before_component,self._rvalue.name_until_component)]
        #elif self.father_until_component().father == self._des_lvalue.father_until_component():
        #    return [".%s(%s)" %(self.name_before_component,self._des_lvalue.name_until_component)]
        #else:
        return [".%s(%s)" %(self.name_before_component,self.name_until_component)]

    @property
    def verilog_outer_def(self):
        '''生成信号声明的RTL'''
        return ["wire %s %s" %('' if self.attribute.width==1 else '[%s:0]' % (self.attribute.width-1),self.name_until_component)]
    
    @property
    def verilog_outer_def_as_list_io(self):
        raise NotImplementedError()

    @property
    def _iosig_type_prefix(self):
        raise NotImplementedError

    @property
    def verilog_def(self):
        return ['%s %s %s' % (self._iosig_type_prefix,'' if self.attribute.width==1 else '[%s:0]' %(self.attribute.width-1),self.name_before_component)]
    
    @property
    def verilog_def_as_list(self):
        return [self._iosig_type_prefix,
                '' if self.attribute.width==1 else '[%s:0]' %(self.attribute.width-1),
                self.name_before_component]

class InputLikeMixin:
    """Shared logic for all input-type IO ports (Input, InputStructIO, InputEnumIO, InputUnionIO)."""

    @property
    def lstring(self):
        return self.name_until_component

    def rstring(self, lvalue):
        if lvalue.father_until_component() is self.father_until_component() or \
           lvalue.father_until_component().father is self.father_until_component():
            return self.name_before_component
        elif self._rvalue is not None:
            return self.name_until_component
        else:
            return self.name_before_component

    @property
    def _iosig_type_prefix(self):
        return 'input'

    @property
    def verilog_inst(self):
        if isinstance(self._rvalue, IOSig) and self._rvalue.single_connection:
            if low_to_high_connection(self, self._rvalue):
                rvalue_sig_name = self._rvalue.name_before_component
            elif same_level_connection(self, self._rvalue):
                rvalue_sig_name = simplified_connection_naming_judgment(self._rvalue, self)
        elif isinstance(self._rvalue, IOSig) and not self._rvalue.single_connection:
            if low_to_high_connection(self, self._rvalue):
                rvalue_sig_name = self._rvalue.name_before_component
            elif same_level_connection(self, self._rvalue):
                rvalue_sig_name = self.name_until_component
        else:
            if self._rvalue == None:
                rvalue_sig_name = ''
            elif isinstance(self._rvalue, Wire) and self._rvalue._rvalue == None:
                rvalue_sig_name = self._rvalue.name_before_component
            else:
                rvalue_sig_name = self.name_until_component
        return [".%s(%s)" % (self.name_before_component, rvalue_sig_name)]

    @property
    def verilog_outer_def_as_list_io(self):
        normal_res, normal_reg_res = self._make_outer_def_res()

        if isinstance(self._rvalue, IOSig):
            if same_level_connection(self, self._rvalue):
                if not self._rvalue.single_connection:
                    res = normal_res
                else:
                    res = self._make_simplified_res(self._rvalue)
            elif low_to_high_connection(self, self._rvalue):
                res = None
            else:
                res = normal_res
        else:
            if self._rvalue == None:
                res = None
            elif isinstance(self._rvalue, Wire) and self._rvalue._rvalue == None:
                res = None
            else:
                if self._need_always:
                    res = normal_reg_res
                else:
                    res = normal_res
        return res

    def _make_outer_def_res(self):
        normal_res = ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        normal_reg_res = ["reg", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        return normal_res, normal_reg_res

    def _make_simplified_res(self, other_sig):
        return ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), simplified_connection_naming_judgment(other_sig, self)]


class OutputLikeMixin:
    """Shared logic for all output-type IO ports (Output, OutputStructIO, OutputEnumIO, OutputUnionIO)."""

    @property
    def lstring(self):
        return self.name_before_component

    def rstring(self, lvalue):
        if (lvalue.father_until_component() is self.father_until_component()) and not is_input_port(lvalue):
            return self.name_before_component
        else:
            return self.name_until_component

    @property
    def _iosig_type_prefix(self):
        return 'output reg' if self._need_always else 'output'

    @property
    def verilog_inst(self):
        if isinstance(self._des_lvalue, IOSig) and self.single_connection:
            if low_to_high_connection(self, self._des_lvalue):
                rvalue_sig_name = self._des_lvalue.name_before_component
            elif same_level_connection(self, self._des_lvalue):
                rvalue_sig_name = simplified_connection_naming_judgment(self, self._des_lvalue)
            else:
                rvalue_sig_name = self.name_until_component
        else:
            if self._des_lvalue == None:
                rvalue_sig_name = ''
            elif isinstance(self.lvalue, Wire) and self.lvalue._lvalue_list == [] and self.single_connection:
                rvalue_sig_name = self._des_lvalue.name_before_component
            else:
                rvalue_sig_name = self.name_until_component
        return [".%s(%s)" % (self.name_before_component, rvalue_sig_name)]

    @property
    def verilog_outer_def_as_list_io(self):
        normal_res, _ = self._make_outer_def_res()

        if not self.single_connection:
            return normal_res
        elif isinstance(self._des_lvalue, IOSig):
            if same_level_connection(self, self._des_lvalue):
                return None
            elif low_to_high_connection(self, self._des_lvalue):
                return None
            else:
                return normal_res
        else:
            if self._des_lvalue == None:
                return None
            elif isinstance(self.lvalue, Wire) and self.lvalue._lvalue_list == []:
                return None
            else:
                return normal_res

    def _make_outer_def_res(self):
        normal_res = ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        normal_reg_res = ["reg", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        return normal_res, normal_reg_res

    def _make_simplified_res(self, other_sig):
        return ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), simplified_connection_naming_judgment(self, other_sig)]

class Input(InputLikeMixin, IOSig):
    '''
    Input is used to declare an input port for Component in UHDL.

    Input needs a UHDL constant as a template to declare its type. 
    Its type will be consistent with the constants they use as templates.

    A typical example is

            Input(UInt(32))

    The type of Input in this example will be consistent with UInt(32), 
    that is, it is a 32-bit unsigned integer.
    '''
    def reverse(self):
        return Output(self.attribute)

    def template(self):
        return Input(self.attribute)
class Output(OutputLikeMixin, IOSig):
    '''
    Output is used to declare an output port for Component in UHDL.

    Output needs a UHDL constant as a template to declare its type. 
    Its type will be consistent with the constants they use as templates.

    A typical example is

            Output(UInt(32))

    The type of Output in this example will be consistent with UInt(32), 
    that is, it is a 32-bit unsigned integer.
    '''

    def reverse(self):
        return Input(self.attribute)

    def template(self):
        return Output(self.attribute)
class Inout(IOSig):


    def __init__(self,template):
        super().__init__(template)
        self._inout_connect_list = [self]
        self._need_assign = None

    @property
    def _iosig_type_prefix(self):
        return 'inout'

    def reverse(self):
        return Inout(self.attribute)

    def template(self):
        return Inout(self.attribute)



    @property
    def verilog_inst(self):
        from .Component import Component
        # For inout port instantiation, we need to find the signal that is 
        # visible in the parent module (the module that instantiates this component).
        # The parent module is self's father's father.
        
        self_component = self.father_until(Component)
        parent_component = self_component.father if self_component else None
        
        if len(self._inout_connect_list) > 1:
            # Find the signal that belongs to the parent module's scope
            # Priority: 1. parent module's own IO, 2. sibling component's IO
            target_var = None
            
            for var in self._inout_connect_list:
                var_component = var.father_until(Component)
                if var_component is parent_component:
                    # This var belongs to the parent module - best choice
                    target_var = var
                    break
            
            if target_var is None:
                # Fallback: find a var that is a sibling (same parent)
                for var in self._inout_connect_list:
                    var_component = var.father_until(Component)
                    if var_component and var_component.father is parent_component and var_component is not self_component:
                        target_var = var
                        break
            
            if target_var is None:
                # Last fallback: use the original logic (min level)
                target_var = self._inout_connect_list[0]
                for var in self._inout_connect_list:
                    if var.level_until_root() < target_var.level_until_root():
                        target_var = var
            
            # Use name_before_component because target_var is an IO of parent_component,
            # and within the parent module, the signal is referenced by its own name.
            return [".%s(%s)" %(self.name_before_component, target_var.name_before_component)]
        else:
            if self._need_assign is not None:
                return [".%s(%s)" %(self.name_before_component, self._need_assign[0].name_before_component)]
            else:
                return [".%s(%s)" %(self.name_before_component, '')]



    @property
    def verilog_outer_def_as_list_io(self):
        # check whether a io need outer def.
        min_lvl_var = self._inout_connect_list[0]
        for var in self._inout_connect_list:
            if var.level_until_root() < min_lvl_var.level_until_root():
                min_lvl_var = var
        
        
        if min_lvl_var.level_until_root() == self._inout_connect_list[0].level_until_root() and len(self._inout_connect_list)>1:
            if not self is self._inout_connect_list[0]:
                return None
            else:
                return ["wire",
                '' if self.attribute.width==1 else '[%s:0]' % (self.attribute.width-1),
                min_lvl_var.name_until_component]
        else:
            return None

class StructFieldRef(Value):
    """A reference to one field within a StructIO port.

    Acts as an rvalue / lvalue that maps to ``port_name.field_name`` in Verilog
    and carries the correct per-field attribute (UInt/SInt of field width).

    Created lazily by ``StructIO.__getattr__`` when a field name is accessed.
    """

    def __init__(self, parent_struct_io, field_name, field_info):
        super().__init__()
        self._parent = parent_struct_io
        self._field_name = field_name
        self._field_info = field_info
        # Build attribute from field info
        w = field_info['width']
        s = field_info.get('signed', False)
        self._nested_struct_type = field_info.get('struct_type', None)
        if self._nested_struct_type is not None:
            self._attr = StructConstant(self._nested_struct_type)
        else:
            self._attr = SInt(w) if s else UInt(w)

    def __getattr__(self, name):
        """Support nested struct field access: parent.field.subfield."""
        if name.startswith('_'):
            raise AttributeError(name)
        nested = object.__getattribute__(self, '_nested_struct_type')
        if nested is not None and name in nested.fields:
            finfo = nested.fields[name]
            return StructFieldRef(self, name, finfo)
        raise AttributeError(f"StructFieldRef '{self._field_name}' has no sub-field '{name}'")

    @property
    def attribute(self):
        return self._attr

    @property
    def lstring(self):
        # For nested refs (parent is also StructFieldRef), chain lstrings
        if isinstance(self._parent, StructFieldRef):
            return "%s.%s" % (self._parent.lstring, self._field_name)
        return "%s.%s" % (self._parent.name_before_component, self._field_name)

    def rstring(self, lvalue):
        # For nested refs, chain rstrings
        if isinstance(self._parent, StructFieldRef):
            return "%s.%s" % (self._parent.rstring(lvalue), self._field_name)
        return "%s.%s" % (self._parent.rstring(lvalue) if hasattr(self._parent, 'rstring') else self._parent.name_before_component, self._field_name)

    def father_until_component(self):
        return self._parent.father_until_component()

    def father_until(self, T):
        """Delegate to parent's father_until for hierarchy resolution."""
        return self._parent.father_until(T)

    @property
    def name(self):
        return "%s_%s" % (self._parent.name if self._parent.name else '', self._field_name)

    @property
    def full_hier(self):
        return "%s.%s" % (self._parent.full_hier if hasattr(self._parent, 'full_hier') else str(self._parent), self._field_name)

    def add_lvalue(self, dontcare):
        pass


class StructIO(IOSig):
    """Base class for structured IO ports.

    StructIO is a single port with structured fields, treated as a whole unit
    rather than a group of separate signals. It inherits from IOSig like Input/Output.

    Now carries a ``StructType`` for strict type identity checking and supports
    field access via dot notation (``port.field_name`` returns a ``StructFieldRef``).

    Attributes:
        _field_order: list of field names in declaration order
        _fields: dict mapping field name to IOSig instance
        _struct_name: optional name of the struct type
        _struct_type: StructType instance (the type kernel)
    """

    def __init__(self, template, fields=None, struct_name=None, struct_package=None, struct_type=None):
        """Initialize a StructIO port.

        Args:
            template: Type template (Constant like UInt, or StructConstant)
            fields: OrderedDict or list of (name, IOSig) tuples for struct fields
            struct_name: Optional name of the struct typedef (e.g., 'pkg::my_struct_t')
            struct_package: Optional package name if the struct is scoped (e.g., 'pkg')
            struct_type: Optional StructType instance. If provided, fields/struct_name
                         are derived from it (unless also explicitly given).
        """
        super().__init__(template)
        self._field_order = []
        self._fields = {}  # name -> IOSig mapping
        self._struct_name = struct_name
        self._struct_package = struct_package
        self._struct_type = struct_type  # StructType instance

        # Derive from StructType if provided
        if struct_type is not None:
            if struct_name is None and struct_type.name:
                self._struct_name = struct_type.name
            if struct_package is None and struct_type.package:
                self._struct_package = struct_type.package

        if fields:
            if isinstance(fields, dict):
                for name, iosig in fields.items():
                    self.add_field(name, iosig)
            elif isinstance(fields, list):
                for name, iosig in fields:
                    self.add_field(name, iosig)

    def add_field(self, name, iosig):
        """Add a field to this struct port."""
        if not isinstance(iosig, IOSig):
            raise TypeError(f"Field {name} must be an IOSig, got {type(iosig)}")
        self._fields[name] = iosig
        if name not in self._field_order:
            self._field_order.append(name)

    # ---------- dot-access for field references ----------
    def __getattr__(self, name):
        # Avoid recursion on internal attributes
        if name.startswith('_'):
            raise AttributeError(name)
        # Check if it's a struct field
        _fields = object.__getattribute__(self, '_fields') if '_fields' in self.__dict__ else {}
        _struct_type = object.__getattribute__(self, '_struct_type') if '_struct_type' in self.__dict__ else None
        if name in _fields:
            # Get field info from struct_type if available
            if _struct_type and name in _struct_type.fields:
                finfo = _struct_type.fields[name]
            else:
                # Build field info from the IOSig
                field_iosig = _fields[name]
                finfo = {'width': field_iosig.attribute.width,
                         'signed': isinstance(field_iosig.attribute, SInt)}
            return StructFieldRef(self, name, finfo)
        raise ErrStructFieldNotFound(self, name, list(_fields.keys()))

    @property
    def struct_type(self):
        """Return the StructType for this port, or None."""
        return self._struct_type

    @property
    def _iosig_type_prefix(self):
        raise NotImplementedError("StructIO subclasses must implement _iosig_type_prefix")

    @property
    def lstring(self):
        raise NotImplementedError("StructIO subclasses must implement lstring")

    def rstring(self, lvalue):
        raise NotImplementedError("StructIO subclasses must implement rstring")

    def reverse(self):
        raise NotImplementedError("StructIO subclasses must implement reverse")

    def reverse(self):
        raise NotImplementedError("StructIO subclasses must implement reverse")

    def template(self):
        raise NotImplementedError("StructIO subclasses must implement template")

    @property
    def verilog_def(self):
        """Generate port definition using struct type name."""
        if self._struct_name:
            return ['%s %s %s' % (self._iosig_type_prefix, self._struct_name, self.name_before_component)]
        else:
            return super().verilog_def

    @property
    def verilog_def_as_list(self):
        if self._struct_name:
            return [self._iosig_type_prefix, self._struct_name, self.name_before_component]
        else:
            return super().verilog_def_as_list
class InputStructIO(InputLikeMixin, StructIO):
    """Input struct port - behaves like Input but for structured types."""
    
    def reverse(self):
        """Create an OutputStructIO with reversed fields."""
        reversed_fields = [(name, self._fields[name].reverse()) for name in self._field_order]
        return OutputStructIO(self.attribute, fields=reversed_fields, struct_name=self._struct_name, struct_package=self._struct_package, struct_type=self._struct_type)
    
    def template(self):
        """Create a template InputStructIO with same structure."""
        template_fields = [(name, self._fields[name].template()) for name in self._field_order]
        return InputStructIO(self.attribute, fields=template_fields, struct_name=self._struct_name, struct_package=self._struct_package, struct_type=self._struct_type)

    def _make_outer_def_res(self):
        if self._struct_name:
            normal_res = [self._struct_name, '', self.name_until_component]
            normal_reg_res = [self._struct_name, '', self.name_until_component]
        else:
            normal_res = ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
            normal_reg_res = ["reg", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        return normal_res, normal_reg_res

    def _make_simplified_res(self, other_sig):
        if self._struct_name:
            return [self._struct_name, '', simplified_connection_naming_judgment(other_sig, self)]
        else:
            return ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), simplified_connection_naming_judgment(other_sig, self)]
class OutputStructIO(OutputLikeMixin, StructIO):
    """Output struct port - behaves like Output but for structured types."""
    
    def reverse(self):
        """Create an InputStructIO with reversed fields."""
        reversed_fields = [(name, self._fields[name].reverse()) for name in self._field_order]
        return InputStructIO(self.attribute, fields=reversed_fields, struct_name=self._struct_name, struct_package=self._struct_package, struct_type=self._struct_type)
    
    def template(self):
        """Create a template OutputStructIO with same structure."""
        template_fields = [(name, self._fields[name].template()) for name in self._field_order]
        return OutputStructIO(self.attribute, fields=template_fields, struct_name=self._struct_name, struct_package=self._struct_package, struct_type=self._struct_type)

    def _make_outer_def_res(self):
        if self._struct_name:
            normal_res = [self._struct_name, '', self.name_until_component]
            normal_reg_res = [self._struct_name, '', self.name_until_component]
        else:
            normal_res = ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
            normal_reg_res = ["reg", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        return normal_res, normal_reg_res

    def _make_simplified_res(self, other_sig):
        if self._struct_name:
            return [self._struct_name, '', simplified_connection_naming_judgment(self, other_sig)]
        else:
            return ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), simplified_connection_naming_judgment(self, other_sig)]
################################################################################################################
#
#   EnumIO – IO port classes for enum types
#
################################################################################################################

class EnumIO(IOSig):
    """Base class for enum-typed IO ports.

    EnumIO is a single port with enum type semantics, treated as a whole unit.
    It inherits from IOSig like Input/Output.

    Carries an ``EnumType`` for strict type identity checking and supports
    member access via the enum_type property.

    Attributes:
        _enum_name: optional name of the enum type
        _enum_type: EnumType instance (the type kernel)
        _enum_package: optional package name
    """

    def __init__(self, template, enum_name=None, enum_package=None, enum_type=None):
        super().__init__(template)
        self._enum_name = enum_name
        self._enum_package = enum_package
        self._enum_type = enum_type

        if enum_type is not None:
            if enum_name is None and enum_type.name:
                self._enum_name = enum_type.name
            if enum_package is None and enum_type.package:
                self._enum_package = enum_type.package

    @property
    def enum_type(self):
        """Return the EnumType for this port, or None."""
        return self._enum_type

    @property
    def verilog_def(self):
        """Generate port definition using enum type name."""
        if self._enum_name:
            return ['%s %s %s' % (self._iosig_type_prefix, self._enum_name, self.name_before_component)]
        else:
            return super().verilog_def

    @property
    def verilog_def_as_list(self):
        if self._enum_name:
            return [self._iosig_type_prefix, self._enum_name, self.name_before_component]
        else:
            return super().verilog_def_as_list


class InputEnumIO(InputLikeMixin, EnumIO):
    """Input enum port - behaves like Input but for enum types."""

    def reverse(self):
        return OutputEnumIO(self.attribute, enum_name=self._enum_name,
                            enum_package=self._enum_package, enum_type=self._enum_type)

    def template(self):
        return InputEnumIO(self.attribute, enum_name=self._enum_name,
                           enum_package=self._enum_package, enum_type=self._enum_type)

    def _make_outer_def_res(self):
        if self._enum_name:
            normal_res = [self._enum_name, '', self.name_until_component]
            normal_reg_res = [self._enum_name, '', self.name_until_component]
        else:
            normal_res = ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
            normal_reg_res = ["reg", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        return normal_res, normal_reg_res

    def _make_simplified_res(self, other_sig):
        if self._enum_name:
            return [self._enum_name, '', simplified_connection_naming_judgment(other_sig, self)]
        else:
            return ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), simplified_connection_naming_judgment(other_sig, self)]

class OutputEnumIO(OutputLikeMixin, EnumIO):
    """Output enum port - behaves like Output but for enum types."""

    def reverse(self):
        return InputEnumIO(self.attribute, enum_name=self._enum_name,
                           enum_package=self._enum_package, enum_type=self._enum_type)

    def template(self):
        return OutputEnumIO(self.attribute, enum_name=self._enum_name,
                            enum_package=self._enum_package, enum_type=self._enum_type)

    def _make_outer_def_res(self):
        if self._enum_name:
            normal_res = [self._enum_name, '', self.name_until_component]
            normal_reg_res = [self._enum_name, '', self.name_until_component]
        else:
            normal_res = ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
            normal_reg_res = ["reg", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        return normal_res, normal_reg_res

    def _make_simplified_res(self, other_sig):
        if self._enum_name:
            return [self._enum_name, '', simplified_connection_naming_judgment(self, other_sig)]
        else:
            return ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), simplified_connection_naming_judgment(self, other_sig)]

################################################################################################################
#
#   UnionIO – IO port classes for packed union types
#
################################################################################################################

class UnionFieldRef(Value):
    """A reference to one field within a UnionIO port.

    Acts as an rvalue / lvalue that maps to ``port_name.field_name`` in Verilog
    and carries the correct per-field attribute (UInt/SInt of field width).

    Created lazily by ``UnionIO.__getattr__`` when a field name is accessed.
    """

    def __init__(self, parent_union_io, field_name, field_info):
        super().__init__()
        self._parent = parent_union_io
        self._field_name = field_name
        self._field_info = field_info
        w = field_info['width']
        s = field_info.get('signed', False)
        self._attr = SInt(w) if s else UInt(w)

    @property
    def attribute(self):
        return self._attr

    @property
    def lstring(self):
        return "%s.%s" % (self._parent.name_before_component, self._field_name)

    def rstring(self, lvalue):
        return "%s.%s" % (self._parent.rstring(lvalue) if hasattr(self._parent, 'rstring') else self._parent.name_before_component, self._field_name)

    def father_until_component(self):
        return self._parent.father_until_component()

    def father_until(self, T):
        return self._parent.father_until(T)

    @property
    def name(self):
        return "%s_%s" % (self._parent.name if self._parent.name else '', self._field_name)

    @property
    def full_hier(self):
        return "%s.%s" % (self._parent.full_hier if hasattr(self._parent, 'full_hier') else str(self._parent), self._field_name)

    def add_lvalue(self, dontcare):
        pass


class UnionIO(IOSig):
    """Base class for union-typed IO ports.

    UnionIO is a single port with union type semantics, treated as a whole unit.
    It inherits from IOSig like Input/Output.

    Carries a ``UnionType`` for strict type identity checking and supports
    field access via dot notation (``port.field_name`` returns a ``UnionFieldRef``).

    Attributes:
        _field_order: list of field names in declaration order
        _fields: dict mapping field name to IOSig instance
        _union_name: optional name of the union type
        _union_type: UnionType instance (the type kernel)
    """

    def __init__(self, template, fields=None, union_name=None, union_package=None, union_type=None):
        super().__init__(template)
        self._field_order = []
        self._fields = {}
        self._union_name = union_name
        self._union_package = union_package
        self._union_type = union_type

        if union_type is not None:
            if union_name is None and union_type.name:
                self._union_name = union_type.name
            if union_package is None and union_type.package:
                self._union_package = union_type.package

        if fields:
            if isinstance(fields, dict):
                for name, iosig in fields.items():
                    self.add_field(name, iosig)
            elif isinstance(fields, list):
                for name, iosig in fields:
                    self.add_field(name, iosig)

    def add_field(self, name, iosig):
        if not isinstance(iosig, IOSig):
            raise TypeError(f"Field {name} must be an IOSig, got {type(iosig)}")
        self._fields[name] = iosig
        if name not in self._field_order:
            self._field_order.append(name)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        _fields = object.__getattribute__(self, '_fields') if '_fields' in self.__dict__ else {}
        _union_type = object.__getattribute__(self, '_union_type') if '_union_type' in self.__dict__ else None
        if name in _fields:
            if _union_type and name in _union_type.fields:
                finfo = _union_type.fields[name]
            else:
                field_iosig = _fields[name]
                finfo = {'width': field_iosig.attribute.width,
                         'signed': isinstance(field_iosig.attribute, SInt)}
            return UnionFieldRef(self, name, finfo)
        raise AttributeError(f"UnionIO has no field '{name}'. Available: {list(_fields.keys())}")

    @property
    def union_type(self):
        return self._union_type

    @property
    def verilog_def(self):
        if self._union_name:
            return ['%s %s %s' % (self._iosig_type_prefix, self._union_name, self.name_before_component)]
        else:
            return super().verilog_def

    @property
    def verilog_def_as_list(self):
        if self._union_name:
            return [self._iosig_type_prefix, self._union_name, self.name_before_component]
        else:
            return super().verilog_def_as_list


class InputUnionIO(InputLikeMixin, UnionIO):
    """Input union port - behaves like Input but for packed union types."""

    def reverse(self):
        reversed_fields = [(name, self._fields[name].reverse()) for name in self._field_order]
        return OutputUnionIO(self.attribute, fields=reversed_fields, union_name=self._union_name,
                             union_package=self._union_package, union_type=self._union_type)

    def template(self):
        template_fields = [(name, self._fields[name].template()) for name in self._field_order]
        return InputUnionIO(self.attribute, fields=template_fields, union_name=self._union_name,
                            union_package=self._union_package, union_type=self._union_type)

    def _make_outer_def_res(self):
        if self._union_name:
            normal_res = [self._union_name, '', self.name_until_component]
            normal_reg_res = [self._union_name, '', self.name_until_component]
        else:
            normal_res = ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
            normal_reg_res = ["reg", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        return normal_res, normal_reg_res

    def _make_simplified_res(self, other_sig):
        if self._union_name:
            return [self._union_name, '', simplified_connection_naming_judgment(other_sig, self)]
        else:
            return ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), simplified_connection_naming_judgment(other_sig, self)]

class OutputUnionIO(OutputLikeMixin, UnionIO):
    """Output union port - behaves like Output but for packed union types."""

    def reverse(self):
        reversed_fields = [(name, self._fields[name].reverse()) for name in self._field_order]
        return InputUnionIO(self.attribute, fields=reversed_fields, union_name=self._union_name,
                            union_package=self._union_package, union_type=self._union_type)

    def template(self):
        template_fields = [(name, self._fields[name].template()) for name in self._field_order]
        return OutputUnionIO(self.attribute, fields=template_fields, union_name=self._union_name,
                             union_package=self._union_package, union_type=self._union_type)

    def _make_outer_def_res(self):
        if self._union_name:
            normal_res = [self._union_name, '', self.name_until_component]
            normal_reg_res = [self._union_name, '', self.name_until_component]
        else:
            normal_res = ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
            normal_reg_res = ["reg", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), self.name_until_component]
        return normal_res, normal_reg_res

    def _make_simplified_res(self, other_sig):
        if self._union_name:
            return [self._union_name, '', simplified_connection_naming_judgment(self, other_sig)]
        else:
            return ["wire", '' if self.attribute.width == 1 else '[%s:0]' % (self.attribute.width - 1), simplified_connection_naming_judgment(self, other_sig)]

class GroupVar(Variable):

    def exclude(self,*str_list):
        pass

class IOGroup(GroupVar):

    def __init__(self):
        super().__init__()
        #super(IOGroup,self).__init__()
        self._rvalue = None

    @property
    def io_list(self) -> list:
        return sorted([self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],IOSig)])

    # += as circuit assignment
    def __iadd__(self,rvalue):
        if not isinstance(rvalue,IOGroup):
            raise ArithmeticError('A IOGroup expect assigned by a IOGroup.')
        # elif self.attribute != rvalue.attribute:
        #     raise ArithmeticError('Left value attribute/Right value attribute mismatch.')
        else:
            for iol,ior in zip(self.io_list,rvalue.io_list):
                if is_input_port(iol):
                    ior += iol
                else:
                    iol += ior
            object.__setattr__(self,'_rvalue',rvalue)
        return self

    def exclude(self,*args):
        result = copy(self)
        for a in args:
            delattr(result,a)
        return result

    def __getitem__(self,*args):
        result = copy(self)
        for a in args:
            delattr(result,a)
        return result


    @property
    def verilog_assignment(self) -> str:
        return reduce(concat,[x.verilog_assignment for x in self.io_list],[])

    @property
    def verilog_def(self):
        return reduce(concat,[x.verilog_def for x in self.io_list],[])
    
    @property
    def verilog_outer_def(self):
        return reduce(concat,[x.verilog_outer_def for x in self.io_list],[])

    @property
    def verilog_inst(self):
        return reduce(concat,[x.verilog_inst for x in self.io_list],[])

    def reverse(self):
        reverse = IOGroup()
        for i in self.io_list:
            setattr(reverse,i.name,i.reverse())
        return reverse

class StructIOGroup(IOGroup):
    """IOGroup with stable field order and name-based assignment for struct ports.

    - Preserves declaration order for fields
    - Assignment aligns by field name and direction, not by accidental sort
    """

    def __init__(self):
        super().__init__()
        self._field_order = []  # preserve declaration order

    def add_field(self, name, iosig):
        setattr(self, name, iosig)
        self._field_order.append(name)

    @property
    def io_list(self) -> list:
        # Return fields by declaration order, not sorted by name
        return [getattr(self, n) for n in self._field_order if hasattr(self, n)]

    def __iadd__(self, rvalue):
        # Require StructIOGroup on RHS for safe, name-based alignment
        if not isinstance(rvalue, StructIOGroup):
            raise ArithmeticError('A StructIOGroup expects assignment from a StructIOGroup.')
        # Check fields match by name
        rhs_fields = set(rvalue._field_order)
        lhs_fields = set(self._field_order)
        if lhs_fields != rhs_fields:
            missing_lhs = rhs_fields - lhs_fields
            missing_rhs = lhs_fields - rhs_fields
            raise ArithmeticError(f'Struct field mismatch. Missing on LHS: {missing_lhs}, Missing on RHS: {missing_rhs}')
        # Connect by name respecting directions like IOGroup
        for name in self._field_order:
            iol = getattr(self, name)
            ior = getattr(rvalue, name)
            if is_input_port(iol):
                ior += iol
            else:
                iol += ior
        object.__setattr__(self, '_rvalue', rvalue)
        return self

class Expression(Value):

    def __init__(self):
        super().__init__()

    @property
    def op_str(self):
        raise NotImplementedError()

    @property
    def op_name(self):
        raise NotImplementedError

    @property
    def fanin_list(self):
        """
        Get the list of input expressions that this expression depends on.
        Should be implemented by each Expression subclass.
        
        Returns:
            list: List of expressions that are inputs to this expression
        """
        return []  # Default: no fanins

    def get_area(self) -> float:
        """
        Get the normalized area of this expression (combinational logic).
        Uses the unified area calculation system.
        
        Returns:
            float: The normalized area of this expression
        """
        return get_area_for_object(self)


################################################################################################################
#
#   Constant Expression
#
################################################################################################################

class Constant(Expression):
    
    @property
    def fanin_list(self):
        """Constants have no fanins"""
        return []

class AnyConstant(Constant):

    def __init__(self,any_val):
        self._any_val = any_val

    @property
    def attribute(self):
        return self

    @property
    def template(self):
        return self

    def rstring(self, lvalue):
        return self._any_val

    @property
    def lstring(self):
        raise NotImplementedError


    def __str__(self):
        return "AnyConstant %s" % self._any_val

class Bits(Constant):

    def __init__(self,width_or_string,value=0,value_type='bin'):
        super().__init__()
        #super(Bits,self).__init__(self)
        self.type = value_type
        if isinstance(width_or_string,int):
            self.__width = width_or_string
            self.__value = value
            self.__is_string = True
        elif isinstance(width_or_string,str):
            self.__width,self.__value = self._slove_wid_val_from_str(width_or_string)
            self.__is_string = False
        else:
            #raise Exception('Input is not String or Int')
            raise ErrConstInWrong(self,width_or_string)

        if self.__value > (pow(2,self.__width)-1):
            raise ErrBitsValOverflow('The input bit width %s of %s does not match the value %s, and the value is greater than the upper limit.' % (self.__width,GetClsNameFromObj(self),self.__value))

    def _slove_wid_val_from_str(self,string):
        mb = re.match('([0-9]+)(\'[bB])([01_]+)'        ,string)
        md = re.match('([0-9]+)(\'[dD])([0-9_]+)'       ,string)
        mh = re.match('([0-9]+)(\'[hH])([0-9a-fA-F_]+)' ,string)

        if mb:
            width = int(mb.group(1))
            value = int(mb.group(3).replace('_',''),2)
        elif md:
            width = int(md.group(1))
            value = int(md.group(3).replace('_',''),10)
        elif mh:
            width = int(mh.group(1))
            value = int(mh.group(3).replace('_',''),16)
        else:
            raise ErrBitsInvalidStr('"%s" is not a legal string and cannot be decoded as bit width and value' % string)

        return width,value

    @property
    def attribute(self):
        return self

    @property
    def width(self):
        return self.__width

    @property
    def value(self):
        return self.__value

    @property
    def template(self):
        return self

    #@property
    #def string(self):
    #    return '%s\'b%s' % (self.__width,bin(self.__value).replace('0b','') )           #pass

    #@property
    def rstring(self, lvalue):
        if self.type == 'hex':
            return '%s\'h%s' % (self.__width,hex(self.__value).replace('0x','') ) 
        elif self.type == 'oct':
            return '%s\'o%s' % (self.__width,oct(self.__value).replace('0o','') )
        elif self.type == 'dec':
            return '%s\'d%s' % (self.__width,self.__value )
        else:
            return '%s\'b%s' % (self.__width,bin(self.__value).replace('0b','') )           #pass

    @property
    def lstring(self):
        return self.rstring
        raise NotImplementedError
    
    def __eq__(self,other):
        return True if type(self) == type(other) and self.width == other.width else False

    def __hash__(self):
        """Make Bits objects hashable so they can be used as dict keys."""
        return hash((self.__class__.__name__, self.__width, self.__value))

    def __str__(self):
        return "%s(%s,%s)" % (self.__class__.__name__, self.width, self.value)

class UInt(Bits):
    '''
    UInt is a constant type in UHDL.It is an unsigned integer.There are two ways to initialize UInt, the first required parameter is:
    
        int W - 0<W
        int V - 0<=V<(2^W-1)   (default value is 0)
    
    A typical example is

        UInt(4,5)

    It stands for
        
        4'b0101

    The second required parameter is:

        string S - S must be a valid verilog value expression

    A typical example is

        UInt("4'b0101")

    It stands for

        4'b0101

    '''

class SInt(Bits):
    '''
    SInt is a constant type in UHDL.It is a signed integer.There are two ways to initialize SInt, the first required parameter is:
    
        int W - 0<W
        int V - (-2^(W-1))<V<(2^(W-1)-1)   (default value is 0)
    
    A typical example is

        SInt(4,-3)

    It stands for
        
        4'b1101

    The second required parameter is:

        string S - S must be a valid verilog value expression

    A typical example is

        SInt("4'b1101")

    It stands for

        4'b1101

    '''
    #SInt的数值计算需要重新定义一下，Bits的只是对应了UInt

class Parameter(SingleVar):

    #@property
    #def string(self):
    #    return self.name

    #@property
    def rstring(self, lvalue):
        return self.name

    @property
    def lstring(self):
        return self.name

    @property
    def verilog_assignment(self) -> str:
        if not hasattr(self,'_rvalue') or self._rvalue is None:
            return ['.%s(%s)' % (self.lstring,self._template.rstring(self))]
        else:
            return ['.%s(%s)' % (self.lstring,self._rvalue.rstring(self))]

    @property
    def verilog_def(self):
        return ['parameter %s = %s' % (self.lstring,self.attribute.rstring(self))]


    # @property
    # def width(self):
    #     return self.__width

    # @property
    # def string(self):
    #     return self.name_before_component #self.__name
 
    # @property
    # def attribute(self):
    #     return self.__width


    #@attribute.setter
    #def atrribute(self,value):
    #    self.__attribute = value

################################################################################################################
#
#   AlwaysCombExpression
#
################################################################################################################

class AlwaysCombExpression(Expression):
    pass   

class CaseExpression(AlwaysCombExpression):

    def __init__(self,select,case_pair=[],default=None):
        super().__init__()
        self.__select    = select
        self.__default   = default
        self.__attr      = None

        # Convert dict input to list of tuples if needed
        if isinstance(case_pair, dict):
            self.__case_pair = list(case_pair.items())
        else:
            self.__case_pair = case_pair

        self.check_rvalue(select)

        if default is not None:
            self.check_rvalue(default)
            self.__attr = default.attribute

        for k,v in self.__case_pair:
            self.check_rvalue(k)
            self.check_rvalue(v)
            if k.attribute != select.attribute:
                raise ErrAttrMismatch('All key in case_pair must have the same attribute select signal.', self.__select, *self.__case_key)
            if self.__attr is not None and v.attribute != self.__attr:  
                if self.__default is None:
                    raise ErrAttrMismatch('All value in case_pair must have same attribute.', *self.__case_value)
                else:
                    raise ErrAttrMismatch('All value in case_pair must have same attribute.', *self.__case_value, self.__default)
            self.__attr = v.attribute 

    @property
    def __case_key(self):
        return [x[0] for x in self.__case_pair]

    @property
    def __case_value(self):
        # return the value part of each (key, value) pair
        return [x[1] for x in self.__case_pair]

    @property
    def fanin_list(self):
        """Case expressions have select signal, case keys and values as fanins"""
        fanins = [self.__select]
        fanins.extend(self.__case_key)
        fanins.extend(self.__case_value)
        if self.__default is not None:
            fanins.append(self.__default)
        return fanins

    @property
    def attribute(self):
        return self.__attr

    def bstring(self, lvalue, assign_method) -> str:
        str_list = ['case(%s)' % self.__select.rstring(lvalue)]

        for k,v in self.__case_pair:
            logic_block     = v.bstring(lvalue, assign_method)
            logic_block[0]  = '%s : %s' % (k.rstring(lvalue),logic_block[0])
            logic_block[1:] = ['    %s' %x for x in logic_block[1:]]
            str_list += logic_block

        if self.__default != None:
            logic_block     = self.__default.bstring(lvalue, assign_method)
            logic_block[0]  = 'default : %s' % logic_block[0]
            logic_block[1:] = ['    %s' %x for x in logic_block[1:]]
            str_list += logic_block

        str_list.append('endcase')
        return ["begin"] + list(map(lambda x:"    "+x,str_list)) + ["end"]

class WhenExpression(AlwaysCombExpression):
    def __init__(self):
        super().__init__()
        self._condition_list    = []
        self._action_list       = []
        self._otherwise_action  = None

        self._attribute         = None
        self._next_is_when      = True
        self._has_otherwise     = False
    
    def when(self,val: Value):
        '''
        When is used to construct a complex selection circuit, and the input of when is 
            
            rhs I - UInt(1)
            
        The return value of when will only be calculated after the when selection circuit is completed. 
        When the when selection circuit uses multiple "when", "then", "otherwise" completions, 
        the attribute of its return value O will be the same as the input specified by "then" and "otherwise".
        
        A typical example is:

            O += when(A).then(Ares).when(B).then(Bres).otherwise(DFTres)

        The corresponding behavior of this selection circuit example it expresses is 

            if(A)       O = Ares
            else if(B)  O = Bres
            else        O = DFTres
        '''
        # operate struct check
        if self._next_is_when == False : raise ErrWhenExpOperateWrong('A "when" has been added to the when expression.At this time, you can only use "then" complete the "when-then" pairing,but get a "otherwise".')
        
        # input value check
        self.check_rvalue(val)
        if val.attribute != UInt(1)    : raise ErrLogicSigAttrWrong('"when" need a boolean rhs as input.',Value)

        self._next_is_when = False
        self._condition_list.append(val)
        return self

    When = when

    def then(self,val:Value):
        '''
        Then is used to continue filling information into the complex selection circuit constructed by "When" and "EmptyWhen". 
        The input of Then is 
            
            rhs I - UInt/SInt(i)
            
        which represents the output result of the selection circuit when the condition specified by "When" before "Then" is satisfied. 
        
        All output results specified by "Then" and "Otherwise" must have the same attributes.
        '''
        # operate struck check
        if self._next_is_when == True      : raise ErrWhenExpOperateWrong('In when expressions, "then" can only follow "when".')
        # input value check
        self.check_rvalue(val)
        if self._attribute == None         : self._attribute = val.attribute
        if self.attribute != val.attribute : raise ErrAttrMismatch('In a When expression, all variables declared by "then" and "otherwise" must have the same attribute.',*self._action_list,self._otherwise_action)

        self._next_is_when = True
        self._action_list.append(val)
        return self

    Then = then
    
    def otherwise(self,val: Value):
        '''
        Otherwise is used to continue filling information into the complex selection circuit constructed by "When" and "EmptyWhen". 
        The input of Otherwise is 
            
            rhs I - UInt/SInt(i)
            
        which represents the default result selected by the selection circuit when all the conditions specified by "When" are not established.
        
        All output results specified by "Then" and "Otherwise" must have the same attributes.
        '''
        # operate struct check
        if self._has_otherwise == True      : raise ErrWhenExpOperateWrong('A when expression can only have one "otherwise".')
        # input value check
        self.check_rvalue(val)
        if self._attribute == None          : self._attribute = val.attribute
        if self.attribute != val.attribute  : raise ErrAttrMismatch('In a When expression, all variables declared by "then" and "otherwise" must have the same attribute.',*self._action_list,self._otherwise_action)

        self._has_otherwise    = True
        self._otherwise_action = val
        return self

    Ohterwise = otherwise

    @property
    def fanin_list(self):
        """When expressions have conditions and actions as fanins"""
        fanins = []
        fanins.extend(self._condition_list)
        fanins.extend(self._action_list)
        if self._otherwise_action is not None:
            fanins.append(self._otherwise_action)
        return fanins

    @property
    def attribute(self):
        if self._attribute == None: raise Exception('Unprocess Error.expression used before constructed.')
        return self._attribute

    def bstring(self,lvalue,assign_method) -> str:
        str_list = []
        for index,(condition,action) in enumerate(zip(self._condition_list,self._action_list)):
            if_block = action.bstring(lvalue,assign_method)
            if index==0 : if_block[0] = "if(%s) %s"      %(condition.rstring(lvalue),if_block[0])
            else        : if_block[0] = "else if(%s) %s" %(condition.rstring(lvalue),if_block[0])
            str_list += if_block

        if self._has_otherwise:
            if_block = self._otherwise_action.bstring(lvalue,assign_method)
            if_block[0] = "else %s" % if_block[0]
            str_list += if_block

        return ["begin"] + list(map(lambda x:"    "+x,str_list)) + ["end"]

class CutExpression(Expression):

    def __init__(self,op:Value,hbound:int,lbound:int):
        super().__init__()

        self.check_rvalue(op)
        self.op     = op
        self.hbound = hbound
        self.lbound = lbound
        if not isinstance(self.hbound,int):
            raise ErrCutExpSliceInvalid(self,'hbound %s should be int.' % self.hbound)
        if not isinstance(self.lbound,int):
            raise ErrCutExpSliceInvalid(self,'lbound %s should be int.' % self.lbound)
        if self.hbound < 0:
            raise ErrCutExpSliceInvalid(self,'hbound %s must be greater than or equal to 0' % self.hbound)
        if self.lbound < 0:
            raise ErrCutExpSliceInvalid(self,'lbound %s must be greater than or equal to 0' % self.lbound)
        if self.hbound < self.lbound:
            raise ErrCutExpSliceInvalid(self,'hbound %s must be greater than or equal to lbound %s' % (self.hbound,self.lbound))
        if hbound > (op.attribute.width -1):
            raise ErrCutExpSliceInvalid(self,'hbound %s exceeds the variable range of %s[%s:0]' % (self.hbound,self.op.name,op.attribute.width-1))

    @property
    def op_name(self):
        return 'Cut([*:*])'

    @property
    def fanin_list(self):
        """Cut expressions have single fanin"""
        return [self.op]

    @property
    def attribute(self) -> int:
        return type(self.op.attribute)(self.hbound - self.lbound + 1)

    #@property
    #def string(self) -> str:
    #    return self.op.string + '[%s:%s]' % ( self.hbound, self.lbound )
    
    #@property
    def rstring(self, lvalue) -> str:
        # cut single bit, e.g. rstring[3:3] --> rstring[3]
        if self.hbound == self.lbound:
            # rstring is not a vector
            if self.op.attribute.width == 1:    return self.op.rstring(lvalue)
            # rstring is a vector
            else:                               return self.op.rstring(lvalue) + '[%s]' % ( self.lbound )
        # cut multi-bit, e.g. rstring[3:1] --> rstring[3:1]
        else:
            return self.op.rstring(lvalue) + '[%s:%s]' % ( self.hbound, self.lbound )

    def bstring(self, lvalue, assign_method) -> str:
        # For clocked assignments like reg <= expr[h:l], create temp wire approach:
        #   always @(posedge clk) begin
        #       tmp = expr;
        #       reg <= tmp[h:l];
        #   end
        from .Component import Component

        if isinstance(self.op, Expression):
            comp = lvalue.father_until(Component)
            # Build unique temp name
            base_tmp = f"{lvalue.name_before_component}_bcut_tmp"
            tmp_name = base_tmp
            idx = 0
            while hasattr(comp, tmp_name):
                exist = getattr(comp, tmp_name)
                if isinstance(exist, Wire) and getattr(exist, 'attribute', None) == self.op.attribute:
                    tmp_wire = exist
                    break
                idx += 1
                tmp_name = f"{base_tmp}_{idx}"
            else:
                tmp_wire = comp.create(tmp_name, Wire(self.op.attribute))
                # Connect temp wire to the expression
                tmp_wire += self.op

            if self.hbound == self.lbound:
                rhs_str = f"{tmp_wire.name_before_component}[{self.lbound}]"
            else:
                rhs_str = f"{tmp_wire.name_before_component}[{self.hbound}:{self.lbound}]"
            return [" ".join([lvalue.lstring, assign_method, rhs_str]) + ";"]

        # Default path: fall back to direct slicing
        return [" ".join([lvalue.lstring, assign_method, self.rstring(lvalue)]) + ";"]

class FanoutExpression(Expression):

    def __init__(self, op:Value, fanout:int):
        super().__init__()
        self._op = op
        self._fanout = fanout

    @property
    def fanin_list(self):
        """Fanout expressions have single fanin"""
        return [self._op]

    @property
    def attribute(self):
        return type(self._op.attribute)(self._op.attribute.width * self._fanout)

    #@property
    #def string(self) -> str:
    #    return '(%s{%s})' % (self._fanout,self._op.string)

    #@property
    def rstring(self, lvalue) -> str:
        return '({%s{%s}})' % (self._fanout,self._op.rstring(lvalue))

################################################################################################################
#
#   List Op Expression
#
################################################################################################################

class ListExpression(Expression):

    def __init__(self,*op_list):
        super().__init__()
        self.op_list = op_list
        for op in op_list:
            self.check_rvalue(op)

    @property
    def fanin_list(self):
        """List expressions' fanins are all operands in op_list"""
        return list(self.op_list)

    #@property
    #def string(self) -> str:
    #    tmp_op_str = ' %s '%self.op_str
    #    return '(%s)' %  tmp_op_str.join([op.string for op in self.op_list])
    
    #@property
    def rstring(self, lvalue) -> str:
        tmp_op_str = ' %s '%self.op_str
        return '(%s)' %  tmp_op_str.join([op.rstring(lvalue) for op in self.op_list])

class MultiListExpression(ListExpression):

    def __init__(self, *op_list):
        super().__init__(*op_list)
        # 1 param still work.
        #if len(op_list) < 2:    raise ErrListExpNeedMultiOp('',op_list)

    @property
    def attribute(self):
        return UInt(1)

class MultiSameListExpression(MultiListExpression):

    def __init__(self, *op_list):
        super().__init__(*op_list)
        for op in op_list:
            if op_list[0].attribute != op.attribute:raise ErrAttrMismatch('Can not "%s" Values with different attributes.' % self.op_name,*self.op_list)

    @property
    def attribute(self):
        return self.op_list[0].attribute

################################################################################################################
#
#   List Op Expression
#       Same List Expression
################################################################################################################

class AndListExpression(MultiListExpression):

    @property
    def op_name(self):
        return 'AndList(&&)'

    @property
    def op_str(self):
        return '&&'

class OrListExpression(MultiListExpression):

    @property
    def op_name(self):
        return 'OrList(||)'

    @property
    def op_str(self):
        return '||'

class BitAndListExpression(MultiSameListExpression):

    @property
    def op_name(self):
        return 'BitAndList(&)'

    @property
    def op_str(self):
        return '&'

class BitOrListExpression(MultiSameListExpression):

    @property
    def op_name(self):
        return 'BitOrList(|)'

    @property
    def op_str(self):
        return '|'

class BitXorListExpression(MultiSameListExpression):

    @property
    def op_name(self):
        return 'BitXorList(^)'

    @property
    def op_str(self):
        return '^'

class BitXnorListExpression(MultiSameListExpression):

    @property
    def op_name(self):
        return 'BitXnorList(^~)'

    @property
    def op_str(self):
        return '^~'

class CombineExpression(ListExpression):

    @property
    def op_name(self):
        return 'Combine({*,*})'

    @property
    def attribute(self) -> int:
        return type(self.op_list[0].attribute)(sum([op.attribute.width for op in self.op_list]))

    #@property
    #def string(self) -> str:
    #    return '{%s}' % ', '.join([op.string for op in self.op_list])
    
    #@property
    def rstring(self, lvalue) -> str:
        return '{%s}' % ', '.join([op.rstring(lvalue) for op in self.op_list])

################################################################################################################
#
#   One Op Expression
#
################################################################################################################

class OneOpExpression(Expression):

    def __init__(self,op):
        super().__init__()
        self._op = op
        self.check_rvalue(op)

    @property
    def fanin_list(self):
        """One-operand expressions have single fanin"""
        return [self._op]

    #@property
    #def string(self) -> str:
    #    return '(%s%s)' % (self.op_str,self._op.string)

    #@property
    def rstring(self, lvalue) -> str:
        return '(%s%s)' % (self.op_str,self._op.rstring(lvalue))

class OneOpU1Expression(OneOpExpression):

    @property
    def attribute(self) -> int:
        return UInt(1)

class OneOpBitExpressionTest(OneOpExpression):

    @property
    def attribute(self):
        return self._op.attribute

class InverseExpression(OneOpBitExpressionTest):

    @property
    def op_name(self):
        return 'Inverse(~)'

    @property
    def op_str(self):
        return '~'

class NotExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'Not(!)'

    @property
    def op_str(self):
        return '!'

class SelfOrExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'SelfOr(|)'

    @property
    def op_str(self):
        return '|'

class SelfAndExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'SelfAnd(&)'

    @property
    def op_str(self):
        return '&'

class SelfXorExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'SelfXor(^)'

    @property
    def op_str(self):
        return '^'

class SelfXnorExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'SelfXnor(^~)'

    @property
    def op_str(self):
        return '^~'

################################################################################################################
#
#   Two Ops Expression
#
################################################################################################################

class TwoOpExpression(Expression):

    def __init__(self,opL:Value,opR:Value):
        super().__init__()
        self.check_rvalue(opL)
        self.check_rvalue(opR)
        self.opL = opL
        self.opR = opR

    @property
    def fanin_list(self):
        """Two-operand expressions have left and right fanins"""
        return [self.opL, self.opR]

    #@property
    #def string(self) -> str:
    #    return '(%s %s %s)'  % (self.opL.string ,self.op_str,self.opR.string)
    
    #@property
    def rstring(self, lvalue) -> str:
        return '(%s %s %s)'  % (self.opL.rstring(lvalue) ,self.op_str,self.opR.rstring(lvalue))
    
    #def __str__(self):
    #    res = super().__str__()
    #    return str(res + '\n' + str(self.opL) + '\n' + str(self.opR))
 
class TwoSameOpExpression(TwoOpExpression):

    def __init__(self,opL,opR):
        super().__init__(opL,opR)
        if opL.attribute != opR.attribute: raise ErrAttrMismatch('Can not "%s" Values with different attributes.' % self.op_name,opL.attribute,opR.attribute)

class LeftShift(TwoOpExpression):
    
    @property
    def attribute(self):
        return self.opL.attribute

    @property
    def op_name(self):
        return 'LeftShift(<<)'

    @property
    def op_str(self):
        return '<<'

class RightShift(TwoOpExpression):

    @property
    def attribute(self):
        return self.opL.attribute

    @property
    def op_name(self):
        return 'RightShift(>>)'

    @property
    def op_str(self):
        return '>>'

class TwoSameOpU1Expression(TwoSameOpExpression):

    @property
    def attribute(self):
        return UInt(1)

class TwoSameOpBitExpression(TwoSameOpExpression):

    @property
    def attribute(self):
        return self.opL.attribute


################################################################################################################
#
#   Two Ops Expression
#       Arthmatic Expression
################################################################################################################

class AddExpression(TwoSameOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(max(self.opL.attribute.width,self.opR.attribute.width) + 1)

    @property
    def op_name(self):
        return 'Add(+)'

    @property
    def op_str(self):
        return '+'

class SubExpression(TwoSameOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(max(self.opL.attribute.width,self.opR.attribute.width) + 1)

    @property
    def op_name(self):
        return 'Sub(-)'

    @property
    def op_str(self):
        return '-'

class MulExpression(TwoSameOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(self.opL.attribute.width + self.opR.attribute.width)

    @property
    def op_name(self):
        return 'Mul(*)'

    @property
    def op_str(self):
        return '*'

################################################################################################################
#
#   Two Ops Expression
#       Two Ops Bit Expression
################################################################################################################

class BitOrExpression(TwoSameOpBitExpression):

    @property
    def op_name(self):
        return 'BitOr(|)'

    @property
    def op_str(self):
        return '|'

class BitAndExpression(TwoSameOpBitExpression):

    @property
    def op_name(self):
        return 'BitAnd(&)'

    @property
    def op_str(self):
        return '&'

class BitXorExpression(TwoSameOpBitExpression):

    @property
    def op_name(self):
        return 'Xor(^)'

    @property
    def op_str(self):
        return '^'

class BitXnorExpression(TwoSameOpBitExpression):

    @property
    def op_name(self):
        return 'BitXnor(^~)'

    @property
    def op_str(self):
        return '^~'

################################################################################################################
#
#   Two Ops Expression
#       Compare Expression
#
################################################################################################################

class EqualExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'Equal(==)'

    @property
    def op_str(self):
        return '=='

class NotEqualExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'NotEqual(!=)'

    @property
    def op_str(self):
        return '!='

class LessEqualExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'LessEqual(<=)'

    @property
    def op_str(self):
        return '<='

class GreaterEqualExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'GreaterEqual(>=)'

    @property
    def op_str(self):
        return '>='

class LessExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'Less(<)'

    @property
    def op_str(self):
        return '<'

class GreaterExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'Greater(>)'

    @property
    def op_str(self):
        return '>'

class AndExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'And(&&)'

    @property
    def op_str(self):
        return '&&'

class OrExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'Or(||)'

    @property
    def op_str(self):
        return '||'
