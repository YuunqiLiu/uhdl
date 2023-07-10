import math, re, string

from enum       import Enum
from functools  import reduce
from operator   import concat
from copy       import copy

from numpy import isin

from .Root      import Root
from .          import Component

from .Exception     import *
from .InternalTool  import *



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
        return self._lvalue_list[0]

    def add_lvalue(self,lvalue):
        self._lvalue_list.append(lvalue)

    @property
    def single_connection(self):
        return True if len(self._lvalue_list) <= 1 else False



    @property
    def name_until_component(self):
        return self.name_until(Component.Component)

    @property
    def name_before_component(self):
        return self.name_before(Component.Component)
    
    def __str__(self):
        return "%s - %s" % (self.name_before(None), self.attribute)
        return "%s %s" % (super().__str__(),self.attribute)

    @property
    def attribute(self):
        raise NotImplementedError

    @property
    def var_name(self):
        return self.__class__.__name__

    # += as circuit assignment
    def __iadd__(self,rvalue):
        # check whether variable used in Assign belongs to component.
        # rvalue may be expression, so it's no need to check them.
        if not isinstance(self.father, Component.Component):    
            raise_ErrVarNotBelongComponent(self)
        if not isinstance(rvalue,Value):                        
            raise_ErrAssignTypeWrong(self,rvalue)
        if self.attribute != rvalue.attribute:  
            raise_ErrAttrMismatch('%s is expected to be connected by a Rvalue with same attribute,but the current attribute does not match.' % self.var_name ,self,rvalue)
        object.__setattr__(self, '_rvalue', rvalue)
        #object.__setattr__(rvalue, '_des_lvalue', self)
        rvalue.add_lvalue(self)

        self_module = self.father_until(Component.Component)
        if isinstance(rvalue, CutExpression):
            rvalue_module = rvalue.op.father_until(Component.Component)
        elif isinstance(rvalue, Expression):
            rvalue_module = None
        else:
            rvalue_module = rvalue.father_until(Component.Component)

        if isinstance(self, Inout) and isinstance(rvalue, Inout):
            # inout connection, give up all check.
            pass
        elif (isinstance(self, Inout) and not isinstance(rvalue, Inout)) or\
           (not isinstance(self, Inout) and isinstance(rvalue, Inout)):
            # inout connect to other type, error.
            raise Exception('error.')

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
                    raise ErrUHDLStr("lhs %s and rhs %s have same father Component %s, bus lhs is Input, it\'s illegal." % (self, rvalue, self_module))
            elif self_module.father is rvalue_module.father:
                # same level connection.
                #    ------------------   ------------------
                #    |                |   |                |
                #    |          (lhs)<-   <-(rhs)          |
                #    |                |   |                |
                #    ------------------   ------------------
                if not isinstance(self, Input):
                    raise ErrUHDLStr("lhs %s's father Component and rhs %s's father Component are in same Component, so lhs should be Input." % (self, rvalue))
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
                if not isinstance(self, Input):
                    raise ErrUHDLStr("lhs %s's father Component is in rhs %s's father Component, so lhs should be Input." % (self, rvalue))
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
                if not isinstance(rvalue, Output):
                    raise ErrUHDLStr("rhs %s's father Component is in lhs %s's father Component, so rhs should be Output." % (self, rvalue))
                if isinstance(self, Input):
                    raise ErrUHDLStr("rhs %s's father Component is in lhs %s's father Component, so lhs should not be Input." % (self, rvalue))
            else:
                # illegal hier.
                raise ErrUHDLStr("The hier where lhs %s and rhs %s are located cannot be legally connected." % (self, rvalue))
        else:
            # rvalue is a unregsitered signal.
            raise ErrUHDLStr("rhs %s does not have a legal component father, it may not be registered into a component." % rvalue)
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
                pass
            elif isinstance(self, Output) and isinstance(self._rvalue, Input) and\
            self.father_until_component() == self._rvalue.father_until_component():
                pass
            else:
                return []
        if self._need_always:
            str_list    = self._rvalue.bstring(self,"=")
            str_list[0] = "always @(*) %s" % str_list[0]
            return str_list
        else:
            return ['assign ' + str(self.lstring) + ' = ' + str(self._rvalue.rstring(self)) + ';']





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
        component_father = self.father_until(Component.Component)
        #print(self)
        #print(self.father)
        #print(component_father)
        for value in self._var_list:
            setattr(component_father, value.name_before(Component.Component), value)

    @property
    def io_list(self) -> list:
        return [self.__dict__[k] for k in self.__dict__ if isinstance(self.__dict__[k],IOSig)]



    def reverse(self):
        reverse = Bundle()
        for i in self.io_list:
            setattr(reverse, i.name.lstrip('%s_'%self.name), i.reverse())
        return reverse



    # def exclude(self,*exclude_list):


    #     res_list = []
    #     exclude_list = ['%s_%s' % (self.name, item) for item in exclude_list]
    #     for var in self._var_list:
    #         if var.name not in exclude_list:
    #             res_list.append(var)
    #     return res_list




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


    #@property
    #def name(self) -> str:
    #    from .Component import Component
    #    return self.name_until_not(Component)

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
        return "%s - %s" % (super().__str__(),self.attribute)


    def check_rvalue(self, op: ValueRoot):
        op.add_lvalue(self)
        '''This function is used to check the validity of rvalue, rvalue must be of type ValueRoot or its subclass.'''
        if not isinstance(op, ValueRoot):
            raise ErrExpInTypeWrong('', self, op)


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
        if not isinstance(template, Constant): raise ErrAttrTypeWrong(self, template)
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
                str_list = self._rvalue.bstring(self,'<=')
                str_list[0] = '    %s' % str_list[0]
                tmp_str_list[1:] = ['    %s' % x for x in tmp_str_list[1:0]]
            str_list += ['end']
            return str_list

    @property
    def verilog_def(self):
        '''生成端口定义的RTL'''
        return ['reg [%s:0] %s' % ((self.attribute.width-1),self.name_before_component)]
    
    @property
    def verilog_def_as_list(self):
        return ['reg','[%s:0]'%((self.attribute.width-1)),self.name_before_component]






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
        # check whether a io need outer def.

        if isinstance(self, Inout):
            if isinstance(self._rvalue, Inout) and same_level_connection(self,self._rvalue):
                return ["wire",
                '' if self.attribute.width==1 else '[%s:0]' % (self.attribute.width-1),
                simplified_connection_naming_judgment(self,self._rvalue)]

            else:
                return None

        if not self.single_connection:
            return ["wire",
                '' if self.attribute.width==1 else '[%s:0]' % (self.attribute.width-1),
                self.name_until_component]

        elif isinstance(self._rvalue, Variable) and isinstance(self, Variable) :

            if (self.father_until_component().father == self._rvalue.father_until_component()) or\
               (self._rvalue.father_until_component().father == self.father_until_component()) or\
               (self.father_until_component().father == self._des_lvalue.father_until_component()) or\
               (self._des_lvalue.father_until_component().father == self.father_until_component()):
               return None

            elif self.father_until_component().father == self._des_lvalue.father_until_component().father and isinstance(self, Output):
                rvalue_sig_name = simplified_connection_naming_judgment(self,self._des_lvalue)

                return ["wire",
                '' if self.attribute.width==1 else '[%s:0]' % (self.attribute.width-1),
                rvalue_sig_name]
            else:
                return None
        else:

            return ["wire",
                '' if self.attribute.width==1 else '[%s:0]' % (self.attribute.width-1),
                self.name_until_component]

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





class Input(IOSig):
    '''
    Input is used to declare an input port for Component in UHDL.

    Input needs a UHDL constant as a template to declare its type. 
    Its type will be consistent with the constants they use as templates.

    A typical example is

            Input(UInt(32))

    The type of Input in this example will be consistent with UInt(32), 
    that is, it is a 32-bit unsigned integer.
    '''
    #@property
    #def is_lvalue(self):
    #    pass

    @property
    def lstring(self):
        return self.name_until_component #self.__name

    #@property
    def rstring(self, lvalue):
        return self.name_before_component #self.__name

    @property
    def _iosig_type_prefix(self):
        return 'input'

    def reverse(self):
        return Output(self.attribute)

    def template(self):
        return Input(self.attribute)


    @property
    def verilog_inst(self):
        if isinstance(self._rvalue, Variable):
            if not self._rvalue.single_connection:
                rvalue_sig_name = self.name_until_component
            elif self.father_until_component().father == self._rvalue.father_until_component():
                rvalue_sig_name = self._rvalue.name_before_component
            elif self.father_until_component().father == self._rvalue.father_until_component().father:
                rvalue_sig_name = simplified_connection_naming_judgment(self._rvalue, self)
        else:
            rvalue_sig_name = self.name_until_component
        return [".%s(%s)" %(self.name_before_component, rvalue_sig_name)]




class Output(IOSig):
    '''
    Output is used to declare an output port for Component in UHDL.

    Output needs a UHDL constant as a template to declare its type. 
    Its type will be consistent with the constants they use as templates.

    A typical example is

            Output(UInt(32))

    The type of Output in this example will be consistent with UInt(32), 
    that is, it is a 32-bit unsigned integer.
    '''
    #@property
    #def is_lvalue(self):
    #    pass

    @property
    def lstring(self):
        return self.name_before_component #self.__name

    #@property
    def rstring(self, lvalue):

        if lvalue.father_until_component() is self.father_until_component():
            return self.name_before_component
        else:
            return self.name_until_component #self.__name

    @property
    def _iosig_type_prefix(self):
        return 'output reg' if self._need_always else 'output'

    def reverse(self):
        return Input(self.attribute)

    def template(self):
        return Output(self.attribute)


    @property
    def verilog_inst(self):
        if not self.single_connection:
            rvalue_sig_name = self.name_until_component
        elif self.father_until_component().father == self._des_lvalue.father_until_component():
            rvalue_sig_name = self._des_lvalue.name_before_component
        elif self.father_until_component().father == self._des_lvalue.father_until_component().father:
            rvalue_sig_name = simplified_connection_naming_judgment(self, self._des_lvalue)
        else:
            rvalue_sig_name = self.name_until_component
        return [".%s(%s)" %(self.name_before_component, rvalue_sig_name)]



class Inout(IOSig):

    @property
    def _iosig_type_prefix(self):
        return 'inout'

    def reverse(self):
        return Inout(self.attribute)

    def template(self):
        return Inout(self.attribute)



    @property
    def verilog_inst(self):
        #if not self.single_connection:
        #    rvalue_sig_name = self.name_until_component
        #rvalue_sig_name = self.name_until_component
        #return [".%s(%s)" %(self.name_before_component, rvalue_sig_name)]
    
        if isinstance(self._rvalue, Inout):
            if same_module_connection(self, self._rvalue):
                num = 0
                rvalue_sig_name = simplified_connection_naming_judgment(self, self._rvalue)
            elif same_level_connection(self, self._rvalue):
                num = 1
                rvalue_sig_name = simplified_connection_naming_judgment(self, self._rvalue)
            elif low_to_high_connection(self, self._rvalue) or low_to_high_connection(self._rvalue, self):
                num = 2
                rvalue_sig_name = self._rvalue.name_before_component
            else:
                raise Exception()

        elif isinstance(self._des_lvalue, Inout):
           # print(self, self._des_lvalue)
           

            if same_module_connection(self, self._des_lvalue):
                num = 3
                rvalue_sig_name = simplified_connection_naming_judgment(self._des_lvalue, self)
            elif same_level_connection(self, self._des_lvalue):
                num = 4
                rvalue_sig_name = simplified_connection_naming_judgment(self._des_lvalue, self)
            elif low_to_high_connection(self, self._des_lvalue) or low_to_high_connection(self._des_lvalue, self):
                num = 5
                rvalue_sig_name = self.name_before_component
            else:
                raise Exception()

        return [".%s(%s)" %(self.name_before_component, rvalue_sig_name)]
        return [".%s(%s) %s %s %s " %(self.name_before_component, rvalue_sig_name,self, self._rvalue, num)]



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
                if isinstance(iol,Input):
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






class Expression(Value):

    def __init__(self):
        super().__init__()

    @property
    def op_str(self):
        raise NotImplementedError()

    @property
    def op_name(self):
        raise NotImplementedError


################################################################################################################
#
#   Constant Expression
#
################################################################################################################

class Constant(Expression):
    pass


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

    def __init__(self,width_or_string,value=0):
        super().__init__()
        #super(Bits,self).__init__(self)
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
        return '%s\'b%s' % (self.__width,bin(self.__value).replace('0b','') )           #pass

    @property
    def lstring(self):
        raise NotImplementedError

    def __eq__(self,other):
        return True if type(self) == type(other) and self.width == other.width else False

    def __str__(self):
        return "Bits(%s,%s) with py ID %s" % (self.width,self.value,id(self))






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
    def __str__(self):
        return "UInt(%s,%s) with py ID %s" % (self.width,self.value,id(self))



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
    def __str__(self):
        return "SInt(%s,%s) with py ID %s" % (self.width,self.value,id(self))

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
# 
    # @property
    # def string(self):
    #     return self.name_before_component #self.__name
# 
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
        self.__case_pair = case_pair
        self.__default   = default
        self.__attr      = None

        self.check_rvalue(select)

        if default is not None:
            self.check_rvalue(default)
            self.__attr = default.attribute

        for k,v in case_pair:
            self.check_rvalue(k)
            self.check_rvalue(v)
            if k.attribute != select.attribute:                         ErrAttrMismatch('All key in case_pair must have the same attribute select signal.',self.__select,*self.__case_key)
            if self.__attr is not None and v.attribute != self.__attr:  
                if self.__default is None: ErrAttrMismatch('All value in case_pair must have same attribute.',*self.__case_value)
                else                     : ErrAttrMismatch('All value in case_pair must have same attribute.',*self.__case_value,self.__default)
            self.__attr = v.attribute 

    @property
    def __case_key(self):
        return [x[0] for x in self.__case_pair]

    @property
    def __case_value(self):
        return [x[0] for x in self.__case_value]

    @property
    def attribute(self):
        return self.__attr

    def bstring(self, lvalue, assign_method) -> str:
        str_list = ['case(%s)' % self.__select.rstring(lvalue)]

        for k,v in self.__case_pair:
            logic_block     = v.bstring(lstring,assign_method)
            logic_block[0]  = '%s : %s' % (k.rstring(lvalue),logic_block[0])
            logic_block[1:] = ['    %s' %x for x in logic_block[1:]]
            str_list += logic_block

        if self.__default != None:
            logic_block     = self.__default.bstring(lstring,assign_method)
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
    def attribute(self) -> int:
        return type(self.op.attribute)(self.hbound - self.lbound + 1)

    #@property
    #def string(self) -> str:
    #    return self.op.string + '[%s:%s]' % ( self.hbound, self.lbound )
    
    #@property
    def rstring(self, lvalue) -> str:
        return self.op.rstring(lvalue) + '[%s:%s]' % ( self.hbound, self.lbound )






class FanoutExpression(Expression):

    def __init__(self, op:Value, fanout:int):
        super().__init__()
        self._op = op
        self._fanout = fanout

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

    #@property
    #def string(self) -> str:
    #    return '(%s %s %s)'  % (self.opL.string ,self.op_str,self.opR.string)
    
    #@property
    def rstring(self, lvalue) -> str:
        return '(%s %s %s)'  % (self.opL.rstring(lvalue) ,self.op_str,self.opR.rstring(lvalue))
 


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





    #     if op1_component.father is op2_component or op2_component.father is op1_component: 
    #         # input  <= input  or
    #         # output <= output



    #         if op1.father_until(Component).father is op2.father:
    #             son_op = op1
    #             father_op = op2
    #         else:
    #             son_op = op2
    #             father_op = op1

    #         if isinstance(son_op, Input) and isinstance(father_op, Input):
    #             son_op += father_op
    #         elif isinstance(son_op, Output) and isinstance(father_op, Output):
    #             father_op += son_op
    #         else:
    #             raise Exception()

    #     elif op1.father_until(Component).father is op2.father_unril(Component).father or (outer and op1.father_until(Component) is op2.father_unril(Component)): 
    #         # input <= output
    #         if isinstance(op1, Input) and isinstance(op2, Output):
    #             op1 += op2
    #         elif isinstance(op1, Output) and isinstance(op2, Input):
    #             op2 += op1
    #         else:
    #             raise Exception()


    #     elif (not outer) and op1.father_until(Component) is op2.father_unril(Component):  
    #         # output <= input
    #         if isinstance(op1, Input) and isinstance(op2, Output):
    #             op2 += op1
    #         elif isinstance(op1, Output) and isinstance(op2, Input):
    #             op1 += op2
    #         else:
    #             raise Exception()

    #     else:
    #         raise Exception('op1 %s and op2 %s can not connect.' % (op1, op2))







        #internal
        #same_lvl
        #high_lvl
        #constant
        #self_module = self.father_until(Component.Component)
        #ravlue_module = rvalue.father_until(Component.Component)
        # self_module = self.father_until(Component.Component)
        # if isinstance(rvalue,CutExpression):
        #     rvalue_module = rvalue.op.father_until(Component.Component)
        # elif isinstance(rvalue,Expression):
        #     rvalue_module = self_module
        # else:
        #     rvalue_module = rvalue.father_until(Component.Component)
        # # visible and direction check
        # if self_module is rvalue_module:
        #     if not isinstance(self,(Reg,Wire,Output,Inout)):
        #         raise ErrUHDLStr("rvalue(%s) is not a instance of Reg or Wire or Output."%(rvalue))
        #     pass
        # elif self_module.father is rvalue_module:
        #     if not isinstance(self,(Input,Inout)):
        #         raise ErrUHDLStr("lvalue(%s) is not an output port of submodule.."%(self))
        # elif self_module is rvalue_module.father:
        #     if not isinstance(self,(Reg,Wire,Output,Inout)):
        #         raise ErrUHDLStr("lvalue(%s) is not a instance of Reg or Wire or Output."%(self))
        #     if not isinstance(rvalue,Output):
        #         raise ErrUHDLStr("rvalue(%s) is not an output port of submodule."%(rvalue))
        # elif self_module.father is rvalue_module.father:
        #     if not isinstance(self,Input):
        #         raise ErrUHDLStr("lvalue(%s) is not a instance of Input."%(self))
        #     if not isinstance(rvalue,Output):
        #         raise ErrUHDLStr("rvalue(%s) is not an a instance of Output."%(rvalue))
        # return self



        #else:
        #    raise ErrUHDL("can't connect two signal cross multi layers")
    #raise ArithmeticError('Left value attribute/Right value attribute mismatch.')

    #@property
    #def name(self) -> str:
    #    from .Component import Component
    #    return self.name_until_not(Component)