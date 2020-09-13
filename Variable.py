import math,re
from enum       import Enum
from functools  import reduce
from operator   import concat
from copy       import copy

from .Root      import Root
import string

from .Exception     import *
from .InternalTool  import *

class Variable(Root):

    def __init__(self):
        super().__init__()

    @property
    def name_until_component(self):
        return self.name_until_not(Variable)

    @property
    def name_before_component(self):
        return self.name_before_not(Variable)
            
    def __gt__(self,other):
        if not isinstance(other,Variable):  raise ErrVarCmpWrong('%s should compare with a Variable,but get a %s.' % (GetClsName(self),GetClsName(other)))
        if self.name == other.name:         raise ErrVarCmpWrong('Two Variable with the same name "%s" cannot be compared.' % (self.name))
        if self.name > other.name:          return True
        else:                               return False

    def __lt__(self,other):
        return not self.__gt__(other)

    @property
    def attribute(self):
        raise NotImplementedError

    @property
    def var_name(self):
        return self.__class__.__name__

    # += as circuit assignment
    def __iadd__(self,rvalue):
        if not isinstance(rvalue,Value):        raise ErrAssignTypeWrong(self,rvalue)
        if self.attribute != rvalue.attribute:  raise ErrAttrMismatch('%s is expected to be connected by a Rvalue with same attribute,but the current attribute does not match.' % self.var_name ,self,rvalue)
        object.__setattr__(self,'_rvalue',rvalue)
        object.__setattr__(rvalue,'_des_lvalue',self)
        return self
    #raise ArithmeticError('Left value attribute/Right value attribute mismatch.')


class ValueRoot():
    pass

class Value(ValueRoot):

    def __init__(self):
        super().__init__()
        self._rvalue     = None
        self._des_lvalue = None


    def check_rvalue(self,op:ValueRoot):
        if not isinstance(op,ValueRoot):    raise ErrExpInTypeWrong('',self,op)

    @property
    def _need_always(self):
        return (self._rvalue and isinstance(self._rvalue,AlwaysCombExpression)) or isinstance(self,Reg)

    def __getitem__(self,s:slice):
        return CutExpression(self,s.start,s.stop)

    def Cut(self,hbound:int,lbound:int):
        return CutExpression(self,hbound,lbound)

    def __add__(self,rhs):
        return AddExpression(self,rhs)

    def __sub__(self,rhs):
        return SubExpression(self,rhs)

    def __mul__(self,rhs):
        return MulExpression(self,rhs)

    @property
    def is_lvalue(self) -> bool:
        return False

    @property
    def string(self):
        raise NotImplementedError

    @property
    def lstring(self):
        raise NotImplementedError

    @property
    def rstring(self):
        raise NotImplementedError

    def bstring(self,lstring,assign_method) -> str:
        return [" ".join([lstring,assign_method,self.rstring]) + ";"]

    @property
    def attribute(self):
        raise NotImplementedError

    @property
    def verilog_assignment(self) -> str:
        if not hasattr(self,'_rvalue') or self._rvalue is None:
            return []
        if self._need_always:
            str_list    = self._rvalue.bstring(self.lstring,"=")
            str_list[0] = "always @(*) %s" % str_list[0]
            return str_list

            #return ['always @(*) begin'] + \
            #         self._rvalue.bstring(self.lstring,"=") + \
            #        ['end']
        else:
            return ['assign ' + str(self.lstring) + ' = ' + str(self._rvalue.rstring) + ';']

    @property
    def des_connect(self):
        return self._des_lvalue

    @property
    def src_connect(self):
        return self._rvalue



class SingleVar(Variable,Value):

    def __init__(self,template):
        super().__init__()
        if not isinstance(template,Constant): raise ErrAttrTypeWrong(self,template)
        self.__template = template

    @property
    def width(self):
        return self.__template.width

    @property
    def string(self):
        return self.name_before_component #self.__name

    @property
    def lstring(self):
        return self.name_before_component #self.__name

    @property
    def rstring(self):
        return self.name_before_component #self.__name

    @property
    def attribute(self):
        return self.__template


class WireSig(SingleVar):
    pass


class Reg(SingleVar):

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
            sensitivity_list = [("negedge" if self._clk_active_neg else "posedge") + " " + self._aclk.rstring]
            if self._rst and self._async_rst:
                sensitivity_list += [("negedge" if self._rst_active_low else "posedge") + " " + self._rst.rstring]

            str_list = ['always @(%s) begin' %(" or ".join(sensitivity_list))]

            if self._rst:
                str_list += ['    if(%s%s) %s <= %s;' % ('~' if self._rst_active_low else '',self._rst.rstring,self.lstring,self.attribute.rstring)] 
                tmp_str_list = self._rvalue.bstring(self.lstring,'<=')
                tmp_str_list[0] = '    else %s' % tmp_str_list[0]
                tmp_str_list[1:] = ['    %s' % x for x in tmp_str_list[1:]]
                str_list += tmp_str_list
            else:
                str_list = self._rvalue.bstring(self.lstring,'<=')
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
        return [".%s(%s)" %(self.name_before_component,self.name_until_component)]

    @property
    def verilog_outer_def(self):
        '''生成信号声明的RTL'''
        return ["wire %s %s" %('' if self.attribute.width==1 else '[%s:0]' % (self.attribute.width-1),self.name_until_component)]
    
    @property
    def verilog_outer_def_as_list_io(self):
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

    @property
    def is_lvalue(self):
        pass

    @property
    def lstring(self):
        return self.name_until_component #self.__name

    @property
    def rstring(self):
        return self.name_before_component #self.__name

    @property
    def _iosig_type_prefix(self):
        return 'input'

    def reverse(self):
        return Output(self.attribute)


class Output(IOSig):

    @property
    def is_lvalue(self):
        pass

    @property
    def lstring(self):
        return self.name_before_component #self.__name

    @property
    def rstring(self):
        return self.name_until_component #self.__name

    @property
    def _iosig_type_prefix(self):
        return 'output reg' if self._need_always else 'output'

    def reverse(self):
        return Input(self.attribute)


class Inout(IOSig):

    @property
    def _iosig_type_prefix(self):
        return 'inout'

    def reverse(self):
        return Inout(self.attribute)


class Constant(WireSig):
    
    # def __init__(self,template=UInt(1,0)):
    #     self.__width = math.ceil(math.log(num,2))
    #     self.__value = num

    pass


class Bits(Constant):

    def __init__(self,width_or_string,value=0):
        super().__init__(self)
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

    @property
    def string(self):
        return '%s\'b%s' % (self.__width,bin(self.__value).replace('0b','') )           #pass

    @property
    def rstring(self):
        return '%s\'b%s' % (self.__width,bin(self.__value).replace('0b','') )           #pass

    @property
    def lstring(self):
        raise NotImplementedError

    def __eq__(self,other):
        return True if type(self) == type(other) and self.width == other.width else False

    def __str__(self):
        return "Bits(%s,%s) with py ID %s" % (self.width,self.value,id(self))


class UInt(Bits):

    def __str__(self):
        return "UInt(%s,%s) with py ID %s" % (self.width,self.value,id(self))

class SInt(Bits):

    def __str__(self):
        return "SInt(%s,%s) with py ID %s" % (self.width,self.value,id(self))








class Parameter(SingleVar):

    @property
    def string(self):
        return self.name

    @property
    def rstring(self):
        return self.name

    @property
    def lstring(self):
        return self.name

    @property
    def verilog_assignment(self) -> str:
        if not hasattr(self,'_rvalue') or self._rvalue is None:
            return []
        else:
            return ['.%s(%s)' % (self.lstring,self._rvalue.rstring)]

    @property
    def verilog_def(self):
        return ['parameter %s = %s' % (self.lstring,self.attribute.rstring)]


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
                #print(iol,ior)
                #print(iol,ior)
                #print(iol.width,ior.width)
                if isinstance(iol,Input):
                    ior += iol
                else:
                    iol += ior
            #print('%s get rvalue %s'  %(self,rvalue))
            object.__setattr__(self,'_rvalue',rvalue)
            #self.__rvalue = rvalue
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

    def bstring(self,lstring,assign_method) -> str:
        str_list = ['case(%s)' % self.__select.rstring]

        for k,v in self.__case_pair:
            logic_block     = v.bstring(lstring,assign_method)
            logic_block[0]  = '%s : %s' % (k.rstring,logic_block[0])
            logic_block[1:] = ['    %s' %x for x in logic_block[1:]]
            str_list += logic_block

        if self.__default != None:
            logic_block     = self.__default.bstring(lstring,assign_method)
            logic_block[0]  = 'default : %s' % logic_block[0]
            logic_block[1:] = ['    %s' %x for x in logic_block[1:]]
            str_list += logic_block

        str_list.append('endcase')
        return ["begin"] + list(map(lambda x:"    "+x,str_list)) + ["end"]

def Case(select,case_pair,default):
    return CaseExpression(select,case_pair,default)


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
        # operate struct check
        if self._next_is_when == False : raise ErrWhenExpOperateWrong('A "when" has been added to the when expression.At this time, you can only use "then" complete the "when-then" pairing,but get a "otherwise".')
        
        # input value check
        self.check_rvalue(val)
        if val.attribute != UInt(1)    : raise ErrLogicSigAttrWrong('"when" need a boolean rhs as input.',Value)

        self._next_is_when = False
        self._condition_list.append(val)
        return self

    def then(self,val:Value):
        # operate struck check
        if self._next_is_when == True      : raise ErrWhenExpOperateWrong('In when expressions, "then" can only follow "when".')
        # input value check
        self.check_rvalue(val)
        if self._attribute == None         : self._attribute = val.attribute
        if self.attribute != val.attribute : raise ErrAttrMismatch('In a When expression, all variables declared by "then" and "otherwise" must have the same attribute.',*self._action_list,self._otherwise_action)

        self._next_is_when = True
        self._action_list.append(val)
        return self
    
    def otherwise(self,val: Value):
        # operate struct check
        if self._has_otherwise == True      : raise ErrWhenExpOperateWrong('A when expression can only have one "otherwise".')
        # input value check
        self.check_rvalue(val)
        if self._attribute == None          : self._attribute = val.attribute
        if self.attribute != val.attribute  : raise ErrAttrMismatch('In a When expression, all variables declared by "then" and "otherwise" must have the same attribute.',*self._action_list,self._otherwise_action)

        self._has_otherwise    = True
        self._otherwise_action = val
        return self

    @property
    def attribute(self):
        if self._attribute == None: raise Exception('Unprocess Error.expression used before constructed.')
        return self._attribute

    def bstring(self,lstring,assign_method) -> str:
        str_list = []
        for index,(condition,action) in enumerate(zip(self._condition_list,self._action_list)):
            if_block = action.bstring(lstring,assign_method)
            if index==0 : if_block[0] = "if(%s) %s"      %(condition.rstring,if_block[0])
            else        : if_block[0] = "else if(%s) %s" %(condition.rstring,if_block[0])
            str_list += if_block

        if self._has_otherwise:
            if_block = self._otherwise_action.bstring(lstring,assign_method)
            if_block[0] = "else %s" % if_block[0]
            str_list += if_block

        return ["begin"] + list(map(lambda x:"    "+x,str_list)) + ["end"]

def EmptyWhen():
    return WhenExpression()

def When(val):
    when = WhenExpression()
    return when.when(val)


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

    @property
    def string(self) -> str:
        return self.op.string + '[%s:%s]' % ( self.hbound, self.lbound )
    
    @property
    def rstring(self) -> str:
        return self.op.rstring + '[%s:%s]' % ( self.hbound, self.lbound )


def Cut(op,hbound,lbound):
    CutExpression(op,hbound,lbound)


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
    def string(self) -> str:
        tmp_op_str = ' %s '%self.op_str
        return '(%s)' %  tmp_op_str.join([self.string for op in self.op_list])
    
    @property
    def rstring(self) -> str:
        tmp_op_str = ' %s '%self.op_str
        return '(%s)' %  tmp_op_str.join([self.string for op in self.op_list])


class MultiListExpression(ListExpression):

    def __init__(self, *op_list):
        super().__init__(*op_list)
        if len(op_list) < 2:    raise ErrListExpNeedMultiOp('',op_list)

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

def AndList(*opList):
    return AndListExpression(*opList)


class OrListExpression(MultiListExpression):

    @property
    def op_name(self):
        return 'OrList(||)'

    @property
    def op_str(self):
        return '||'

def OrList(*opList):
    return OrListExpression(*opList)



class BitAndListExpression(MultiSameListExpression):

    @property
    def op_name(self):
        return 'BitAndList(&)'

    @property
    def op_str(self):
        return '&'

def BitAndList(*opList):
    return BitAndListExpression(*opList)


class BitOrListExpression(MultiSameListExpression):

    @property
    def op_name(self):
        return 'BitOrList(|)'

    @property
    def op_str(self):
        return '|'

def BitOrList(*opList):
    return BitOrListExpression(*opList)


class BitXorListExpression(MultiSameListExpression):

    @property
    def op_name(self):
        return 'BitXorList(^)'

    @property
    def op_str(self):
        return '^'

def BitXorList(*opList):
    return BitXorListExpression(*opList)


class BitXnorListExpression(MultiSameListExpression):

    @property
    def op_name(self):
        return 'BitXnorList(^~)'

    @property
    def op_str(self):
        return '^~'

def BitXnorList(*opList):
    return BitXnorListExpression(*opList)


class CombineExpression(ListExpression):

    @property
    def op_name(self):
        return 'Combine({*,*})'

    @property
    def attribute(self) -> int:
        return type(self.op_list[0].attribute)(sum([op.attribute.width for op in self.op_list]))

    @property
    def string(self) -> str:
        return '{%s}' % ', '.join([op.string for op in self.op_list])
    
    @property
    def rstring(self) -> str:
        return '{%s}' % ', '.join([op.rstring for op in self.op_list])

def Combine(*op_list):
    return CombineExpression(*op_list)


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
    def string(self) -> str:
        return '(%s%s)' % (self.op_str,self._op.string)

    @property
    def rstring(self) -> str:
        return '(%s%s)' % (self.op_str,self._op.string)

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

def Inverse(op):
    return InverseExpression(op)


class NotExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'Not(!)'

    @property
    def op_str(self):
        return '!'

def Not(op):
    return NotExpression(op)


class SelfOrExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'SelfOr(|)'

    @property
    def op_str(self):
        return '|'

def SelfOr(op):
    return SelfOrExpression(op)


class SelfAndExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'SelfAnd(&)'

    @property
    def op_str(self):
        return '&'

def SelfAnd(op):
    return SelfAndExpression(op)


class SelfXorExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'SelfXor(^)'

    @property
    def op_str(self):
        return '^'

def SelfXor(op):
    return SelfXorExpression(op)


class SelfXnorExpression(OneOpU1Expression):

    @property
    def op_name(self):
        return 'SelfXnor(^~)'

    @property
    def op_str(self):
        return '^~'

def SelfXnor(op):
    return SelfXnorExpression(op)

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
    def string(self) -> str:
        return '(%s %s %s)'  % (self.opL.string ,self.op_str,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s %s %s)'  % (self.opL.rstring ,self.op_str,self.opR.rstring)

class TwoSameOpExpression(TwoOpExpression):

    def __init__(self,opL,opR):
        super().__init__(opL,opR)
        if opL.attribute != opR.attribute: raise ErrAttrMismatch('Can not "%s" Values with different attributes.' % self.op_name,opL.attribute,opR.attribute)


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

class AddExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(max(self.opL.attribute.width,self.opR.attribute.width) + 1)

    @property
    def op_name(self):
        return 'Add(+)'

    @property
    def op_str(self):
        return '+'

def Add(opL,opR):
    return AddExpression(opL,opR)


class SubExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(max(self.opL.attribute.width,self.opR.attribute.width) + 1)

    @property
    def op_name(self):
        return 'Sub(-)'

    @property
    def op_str(self):
        return '-'

def Sub(opL,opR):
    return SubExpression(opL,opR)


class MulExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(self.opL.attribute.width + self.opR.attribute.width)

    @property
    def op_name(self):
        return 'Mul(*)'

    @property
    def op_str(self):
        return '*'

def Mul(opL,opR):
    return MulExpression(opL,opR)


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

def BitOr(lhs,rhs):
    return BitOrExpression(lhs,rhs)


class BitAndExpression(TwoSameOpBitExpression):

    @property
    def op_name(self):
        return 'BitAnd(&)'

    @property
    def op_str(self):
        return '&'

def BitAnd(lhs,rhs):
    return BitAndExpression(lhs,rhs)


class BitXorExpression(TwoSameOpBitExpression):

    @property
    def op_name(self):
        return 'Xor(^)'

    @property
    def op_str(self):
        return '^'

def BitXor(lhs,rhs):
    return BitXorExpression(lhs,rhs)


class BitXnorExpression(TwoSameOpBitExpression):

    @property
    def op_name(self):
        return 'BitXnor(^~)'

    @property
    def op_str(self):
        return '^~'

def BitXnor(lhs,rhs):
    return BitXnorExpression(lhs,rhs)

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

def Equal(lhs,rhs):
    return EqualExpression(lhs,rhs)


class NotEqualExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'NotEqual(!=)'

    @property
    def op_str(self):
        return '!='

def NotEqual(lhs,rhs):
    return NotEqualExpression(lhs,rhs)


class LessEqualExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'LessEqual(<=)'

    @property
    def op_str(self):
        return '<='

def LessEqual(lhs,rhs):
    return LessEqualExpression(lhs,rhs)


class GreaterEqualExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'GreaterEqual(>=)'

    @property
    def op_str(self):
        return '>='

def GreaterEqual(lhs,rhs):
    return GreaterEqualExpression(lhs,rhs)


class LessExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'Less(<)'

    @property
    def op_str(self):
        return '<'

def Less(opL,opR):
    return LessExpression(opL,opR)


class GreaterExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'Greater(>)'

    @property
    def op_str(self):
        return '>'

def Greater(opL,opR):
    return GreaterExpression(opL,opR)


class AndExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'And(&&)'

    @property
    def op_str(self):
        return '&&'


def And(opL,opR):
    return AndExpression(opL,opR)


class OrExpression(TwoSameOpU1Expression):

    @property
    def op_name(self):
        return 'Or(||)'

    @property
    def op_str(self):
        return '||'

def Or(opL,opR):
    return OrExpression(opL,opR)




#==============================================================================================================================================
        #str_list = ["if(%s)" % condition.rstring ]
        #str_list.append("if(%s)"%(if_pair[0].rstring))
           # str_list[0] += " begin"
           # str_list += action.bstring(lstring,assign_method)
           # str_list += ["end"]
            #str_list[0] += " %s %s %s;"%(lstring,assign_method,action.rstring)
        #if isinstance(action,AlwaysCombExpression):
        #    str_list =  ["if(%s) begin" % condition.rstring]  +\
        #                action.bstring(lstring,assign_method) +\
        #                ["end"]
        #else:
            #str_list = ["if(%s) %s %s %s;" % (condition.rstring,lstring,assign_method,action.rstring)]
            #str_list = ["if(%s) %s;" %(condition.rstring,action.bstring(lstring,assign_method))]

            #if_block[0] = "else "+if_block[0] if index!=0 else if_block[0]
            #if_block = self.get_string(lstring,assign_method,condition,action)

    # def get_string(self,lstring,assign_method,condition,action):
    #     str_list = action.bstring(lstring,assign_method)
    #     str_list[0] = "if(%s) %s" % (condition.rstring,str_list[0])
    #     return  str_list
            # if isinstance(self._otherwise_action,AlwaysCombExpression):
            #     str_list += ["else begin"]
            #     str_list += self._otherwise_action.bstring(lstring,assign_method)
            #     str_list += ["end"]
            # else:
            #     str_list.append("else %s %s %s;"%(lstring,assign_method,self._otherwise_action.rstring))
        #print(str_list)


# class ConstExpression(Expression):
# 
#     def __init__(self,const,width):
#         super(ConstExpression,self).__init__()
#         self.const = const
#         self.width = width
# 
#     @property
#     def attribute(self) -> int:
#         return self.width
# 
#     @property
#     def string(self) -> str:
#         return str(self.const)
# 
# def Const(const,width):
#     return ConstExpression(const,width)

# class WhenOperate(Enum):
#     when                = 1
#     then                = 2
#     otherwise           = 3
# 
# class WhenState(Enum):
#     # when_only           = 1
#     then_only           = 1
#     when_or_otherwise   = 2
#     close               = 3
# 
# 
#     self.__push_condition(val)
# 
#     self._state = WhenState.then_only
# 
#     def state_change(self,operate):
#         if not isinstance(self._state,WhenState)  : raise Exception('Internal error')
#         if not isinstance(operate,WhenOperate)      : raise Exception('Internal error.')
# 
#         # def when_only_state_change(operate):
#         #     #when状态机的第一次跳转在构建函数中完成，任何错误都是内部错误
#         #     if operate == WhenOperate.when      : return WhenState.then_only
#         #     if operate == WhenOperate.then      : raise  Exception('Internal error.')
#         #     if operate == WhenOperate.otherwise : raise  Exception('Internal error.')
# 
#         def then_only_state_change(operate):
#             if operate == WhenOperate.when      : 
#                 raise  ErrWhenExpOperateWrong('A "when" has been added to the when expression.At this time, you can only use "then" complete the "when-then" pairing,but get a "when".')
#             if operate == WhenOperate.then      : return WhenState.when_or_otherwise
#             if operate == WhenOperate.otherwise : 
#                 raise  ErrWhenExpOperateWrong('A "when" has been added to the when expression.At this time, you can only use "then" complete the "when-then" pairing,but get a "otherwise".')
# 
#         def when_or_otherwise_state_change(operate):
#             if operate == WhenOperate.when      : return WhenState.then_only
#             if operate == WhenOperate.then      : raise ErrWhenExpOperateWrong('In when expressions, "then" can only follow "when".')
#             if operate == WhenOperate.otherwise : return WhenState.close
# 
#         def close_state_change(operate):
#             raise ErrWhenExpOperateWrong('This when expression has "otherwise" and closed,no longer accepts new "when-then" pairing.')
# 
#         state_change_lut = {
#             #WhenState.when_only         :when_only_state_change         ,
#             WhenState.then_only         :then_only_state_change         ,
#             WhenState.when_or_otherwise :when_or_otherwise_state_change ,
#             WhenState.close             :close_state_change             }
#         self._state = state_change_lut[self._state](operate)

#    def __push_condition(self,val: Value):
#        pass
#    
#    def __push_action(self,val: Value,tail=False):
#        pass

            #str_list.append('%s : %s %s %s;' % (k.rstring,lstring,assign_method,v.rstring))
            #str_list.append('default: %s %s %s;' % (lstring,assign_method,self.__default.rstring))
        # def get_string(if_pair):
        #     str_list = []
        #     str_list.append("if(%s)"%(if_pair[0].rstring))
        #     if isinstance(if_pair[1],IfExpression):
        #         str_list[0] += " begin"
        #         str_list += if_pair[1].bstring(lstring,assign_method)
        #     else:
        #         str_list[0] += " %s %s %s;"%(lstring,assign_method,if_pair[1].rstring)
        #     return  str_list
        # str_list = []
        # for index,if_pair in enumerate(zip(self._condition_list,self._action_list[0:len(self._condition_list)])):
        #     if_block = get_string(if_pair)
        #     if_block[0] = "else "+if_block[0] if index!=0 else if_block[0]
        #     str_list += if_block
        # if self._closed:
        #     str_list.append("else %s %s %s;"%(lstring,assign_method,self._action_list[-1].rstring))
        # return list(map(lambda x:"    "+x,str_list))
            #str_list.append('%s : %s %s %s;' % (k.rstring,lstring,assign_method,v.rstring))
            #str_list.append('default: %s %s %s;' % (lstring,assign_method,self.__default.rstring))
        # def get_string(if_pair):
        #     str_list = []
        #     str_list.append("if(%s)"%(if_pair[0].rstring))
        #     if isinstance(if_pair[1],IfExpression):
        #         str_list[0] += " begin"
        #         str_list += if_pair[1].bstring(lstring,assign_method)
        #     else:
        #         str_list[0] += " %s %s %s;"%(lstring,assign_method,if_pair[1].rstring)
        #     return  str_list
        # str_list = []
        # for index,if_pair in enumerate(zip(self._condition_list,self._action_list[0:len(self._condition_list)])):
        #     if_block = get_string(if_pair)
        #     if_block[0] = "else "+if_block[0] if index!=0 else if_block[0]
        #     str_list += if_block
        # if self._closed:
        #     str_list.append("else %s %s %s;"%(lstring,assign_method,self._action_list[-1].rstring))
        # return list(map(lambda x:"    "+x,str_list))
            #return ['always @(%s) begin' %(" or ".join(sensitivity_list))] + \
            #        self._rvalue.bstring(self.lstring,"<=") + \
            #        ['end']

            #sensitivity_list = ["%s %s" % ("negedge" if self._clk_active_neg else "posedge",self._aclk.rstring)]
            #return ['assign ' + str(self.lstring) + ' = ' + str(self._rvalue.rstring)]

    #def __iadd__(self,rvalue):
    #    super().__iadd__(rvalue)
        #if self._rst:
        #    rst_signal = Not(self._rst) if self._rst_active_low else self._rst
        #    super().__iadd__(When(rst_signal).then(Bits(self.width,0)).otherwise(rvalue))
        #else:
    #    return self

    