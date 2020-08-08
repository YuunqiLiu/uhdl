import math,re
from functools  import reduce
from operator   import concat
from copy       import copy

#from Num       import UInt
from uhdl.Root      import Root
#from Value     import Value
import string

class Variable(Root):

    def __init__(self):
        super().__init__()
        #super(Variable,self).__init__()

    @property
    def name_until_component(self):
        return self.name_until_not(Variable)

    @property
    def name_before_component(self):
        return self.name_before_not(Variable)
            
    def __gt__(self,other):
        if not isinstance(other,Variable):
            raise TypeError('%s should compare with a Variable,but get a %s' %(type(self),type(other)))
        elif self.name == other.name:
            raise Exception()
        elif self.name > other.name:
            return True
        else:
            return False

    def __lt__(self,other):
        return not self.__gt__(other)


class Value():

    def __init__(self):
        super().__init__()
        #super(Value,self).__init__()
        #print('init',self)
        self._rvalue     = None
        self._des_lvalue = None

    # += as circuit assignment
    def __iadd__(self,rvalue):
        if not isinstance(rvalue,Value):
            raise ArithmeticError('A left value expect assigned by a right value.')
        elif self.attribute != rvalue.attribute:
            raise ArithmeticError('Left value attribute/Right value attribute mismatch.')
        else:
            #print('%s get rvalue %s'  %(self,rvalue))
            object.__setattr__(self,'_rvalue',rvalue)
            object.__setattr__(rvalue,'_des_lvalue',self)
            #self.__rvalue = rvalue

                
        return self

    @property
    def _need_always(self):
        return (self._rvalue and isinstance(self._rvalue,IfExpression)) or isinstance(self,Reg)

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

    #def __eq__(self,rhs):
    #    return EqualExpression(self,rhs)



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
        return ["    " + " ".join([lstring,assign_method,self.rstring]) + ";"]


    @property
    def attribute(self):
        raise NotImplementedError

    @property
    def verilog_assignment(self) -> str:
        if not hasattr(self,'_rvalue') or self._rvalue is None:
            return []
        if self._need_always:
            #if self._rvalue.string is None:
            #    print(self._rvalue)

            return ['always @(*) begin'] + \
                     self._rvalue.bstring(self.lstring,"=") + \
                    ['end']

        else:

            return ['assign ' + str(self.lstring) + ' = ' + str(self._rvalue.rstring) + ';']

    @property
    def des_connect(self):
        return self._des_lvalue

    @property
    def src_connect(self):
        return self._rvalue









class SingleVar(Variable,Value):

    def __init__(self,template):#=UInt(1,0)):
        super().__init__()
        #super().__init__()
        #print(self.__class__.__mro__)
        #super(SingleVar,self).__init__()
        self.__template = template
        # self.__width = width

    @property
    def width(self):
        return self.__template.width
        # return self.__width

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
        # return self.__width





class WireSig(SingleVar):
    pass


class Reg(SingleVar):

    def __init__(self,template,clk:SingleVar,rst:SingleVar=None,async_rst:bool=True,rst_active_low:bool=True,clk_active_neg:bool=False):
        super().__init__(template=template)
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
            return ['always @(%s) begin' %(" or ".join(sensitivity_list))] + \
                    self._rvalue.bstring(self.lstring,"<=") + \
                    ['end']

            #return ['assign ' + str(self.lstring) + ' = ' + str(self._rvalue.rstring)]

    def __iadd__(self,rvalue):
        if self._rst:
            rst_signal = Not(self._rst) if self._rst_active_low else self._rst
            super().__iadd__(IfExpression(rst_signal).then(Bits(self.width,0)).otherwise(rvalue))
        else:
            super().__iadd__(rvalue)
        return self

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
        return ['wire [%s:0] %s' % ((self.attribute.width-1),self.name_before_component)]
    
    @property
    def verilog_def_as_list(self):
        return ['wire','[%s:0]'%(self.attribute.width-1),self.name_before_component]


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
    def verilog_outer_def_as_list(self):
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
        return 'output'

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
        elif isinstance(width_or_string,str):
            self.__width,self.__value = self._slove_wid_val_from_str(width_or_string)
        else:
            raise Exception('Input is not String or Int')

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
            raise Exception()
        if value > (pow(2,width)-1):
            raise ArithmeticError('Overflow:%s' % string)
        return width,value


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
        #print(self,other)
        #print(self.width,other.width)
        return True if type(self) == type(other) and self.width == other.width else False



class UInt(Bits):
    pass

class SInt(Bits):
    pass
  








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
        #print(self.name,self.io_list)
        #print(self.io_list[0].name,self.io_list[1].io_list)
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

    #@property
    #def is_lvalue(self):
    #    return False

    def __init__(self):
        super().__init__()
        #super(Expression,self).__init__()

    # def check_lvalue(self,op:Value):
    #     if not op.is_lvalue:
    #         raise ArithmeticError('Input %s can not be a Left Value.' % type(op))

    def check_rvalue(self,op:Value):
        if not isinstance(op,Value):
            raise ArithmeticError('Input %s can not be a Right Value.' % type(op))



class IfExpression(Expression):
    def __init__(self,val: Value):
        super().__init__()
        self._condition_list = []
        self._action_list = []
        self._closed = False

        self.__push_condition(val)
        
    
    def __push_condition(self,val: Value):
        if val.attribute != UInt(1):
            raise ArithmeticError('condition expression must be instance of UInt(1).')
        elif len(self._condition_list) != len(self._action_list):
            raise Exception('When and then method must be used in pairs.')
        self._condition_list.append(val)
    
    def __push_action(self,val: Value,tail=False):
        if self._action_list != []:
            if self.attribute != val.attribute:
                raise ArithmeticError('width mismatch between different paths.')
        elif not tail:
            if len(self._condition_list) != len(self._action_list)+1:
                raise Exception('When and then method don\'t be used in pairs.')
        self._action_list.append(val)
    
    def when(self,val: Value):
        self.__push_condition(val)
        return self

    def then(self,val:Value):
        self.__push_action(val)
        return self
    
    def otherwise(self,val: Value):
        if self._closed:
            raise Exception('When expression has already been close.')
        self.__push_action(val,tail=True)
        self._closed = True
        return self

    @property
    def attribute(self) -> int:
        return UInt(self._action_list[0].attribute.width)

    def bstring(self,lstring,assign_method) -> str:
        def get_string(if_pair):
            str_list = []
            str_list.append("if(%s)"%(if_pair[0].rstring))
            if isinstance(if_pair[1],IfExpression):
                str_list[0] += " begin"
                str_list += if_pair[1].bstring(lstring,assign_method)
                str_list += ["end"]
            else:
                str_list[0] += " %s %s %s;"%(lstring,assign_method,if_pair[1].rstring)
            return  str_list
        str_list = []
        for index,if_pair in enumerate(zip(self._condition_list,self._action_list[0:len(self._condition_list)])):
            if_block = get_string(if_pair)
            if_block[0] = "else "+if_block[0] if index!=0 else if_block[0]
            str_list += if_block
        if self._closed:
            str_list.append("else %s %s %s;"%(lstring,assign_method,self._action_list[-1].rstring))
        return list(map(lambda x:"    "+x,str_list))


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


class CombineExpression(Expression):

    def __init__(self,*op_list):
        super().__init__()
        #super(CombineExpression,self).__init__()
        self.op_list = op_list

    @property
    def attribute(self) -> int:
        return type(self.op_list[0].attribute)(sum([op.attribute.width for op in self.op_list]))

    @property
    def string(self) -> str:
        #', '.join([op.string for op in self.op_list])
        return '{%s}' % ', '.join([op.string for op in self.op_list])
    
    @property
    def rstring(self) -> str:
        #', '.join([op.string for op in self.op_list])
        return '{%s}' % ', '.join([op.rstring for op in self.op_list])




def Combine(*op_list):
    return CombineExpression(*op_list)



class CutExpression(Expression):

    def __init__(self,op:Value,hbound:int,lbound:int):
        super().__init__()
        #super(CutExpression,self).__init__()
        if hbound > op.attribute.width or lbound <0:
            raise ArithmeticError('index out of range.')
        self.check_rvalue(op)
        self.op     = op
        self.hbound = hbound
        self.lbound = lbound

    @property
    def attribute(self) -> int:
        return type(self.op.attribute)(self.hbound - self.lbound + 1)

    @property
    def string(self) -> str:
        return self.op.string + '[%s:%s]' % ( self.hbound, self.lbound )
    
    @property
    def rstring(self) -> str:
        return self.op.rstring + '[%s:%s]' % ( self.hbound, self.lbound )


class TwoOpExpression(Expression):

    def __init__(self,opL:Value,opR:Value):
        super().__init__()
        #super(TwoOpExpression,self).__init__()
        self.check_rvalue(opL)
        self.check_rvalue(opR)
        self.opL = opL
        self.opR = opR

    @property
    def attribute(self) -> int:
        raise NotImplementedError

    @property
    def string(self) -> str:
        raise NotImplementedError



class AddExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(max(self.opL.attribute.width,self.opR.attribute.width) + 1)

    @property
    def string(self) -> str:
        return '(%s + %s)'  % (self.opL.string ,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s + %s)'  % (self.opL.rstring ,self.opR.rstring)



class SubExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(max(self.opL.attribute.width,self.opR.attribute.width) + 1)

    @property
    def string(self) -> str:
        return '(%s - %s)'  % (self.opL.string ,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s - %s)'  % (self.opL.rstring ,self.opR.rstring)


class MulExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return type(self.opL.attribute)(self.opL.attribute.width + self.opR.attribute.width)

    @property
    def string(self) -> str:
        return '(%s * %s)'  % (self.opL.string ,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s * %s)'  % (self.opL.rstring ,self.opR.rstring)


class EqualExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return UInt(1)
        #type(self.opL.attribute)(self.opL.attribute.width + self.opR.attribute.width)

    @property
    def string(self) -> str:
        return '(%s == %s)'  % (self.opL.string ,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s == %s)'  % (self.opL.rstring ,self.opR.rstring)

def Equal(lhs,rhs):
    return EqualExpression(lhs,rhs)


class LessEqualExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return UInt(1)

    @property
    def string(self) -> str:
        return '(%s <= %s)'  % (self.opL.string ,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s <= %s)'  % (self.opL.rstring ,self.opR.rstring)

def LessEqual(lhs,rhs):
    return LessEqualExpression(lhs,rhs)

class GreaterEqualExpression(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return UInt(1)

    @property
    def string(self) -> str:
        return '(%s >= %s)'  % (self.opL.string ,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s >= %s)'  % (self.opL.rstring ,self.opR.rstring)

def GreaterEqual(lhs,rhs):
    return GreaterEqualExpression(lhs,rhs)

class Not(Expression):

    def __init__(self,op:Value):
        super().__init__()
        #super(TwoOpExpression,self).__init__()
        self.check_rvalue(op)
        self.op = op

    @property
    def attribute(self) -> int:
        return UInt(1)
        #type(self.opL.attribute)(self.opL.attribute.width + self.opR.attribute.width)

    @property
    def string(self) -> str:
        return '(!%s)'  % (self.op.string)
    
    @property
    def rstring(self) -> str:
        return '(!%s)'  % (self.op.rstring)

class And(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return UInt(1)
        #type(self.opL.attribute)(self.opL.attribute.width + self.opR.attribute.width)

    @property
    def string(self) -> str:
        return '(%s && %s)'  % (self.opL.string ,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s && %s)'  % (self.opL.rstring ,self.opR.rstring)


class Or(TwoOpExpression):

    @property
    def attribute(self) -> int:
        return UInt(1)
        #type(self.opL.attribute)(self.opL.attribute.width + self.opR.attribute.width)

    @property
    def string(self) -> str:
        return '(%s || %s)'  % (self.opL.string ,self.opR.string)
    
    @property
    def rstring(self) -> str:
        return '(%s || %s)'  % (self.opL.rstring ,self.opR.rstring)

    # @property
    # def gen_rtl_io(self):
    #     '''生成信号声明的RTL'''
    #     return ["wire %s %s;" %('' if self.data_width==1 else '[%s:0]' % (self.data_width-1),self.name_until(Component))]

#from Entity    import Entity
#from Virtual import Virtual
#from Component import Component
        #self.__name = None
        #if self.__name is None:
        #self.__get_name()

    #@property
    #def name(self):
    #    return self.__name

    #def __get_name(self):
    #    x = inspect.currentframe()
    #    while 1:
    #        for line in inspect.getframeinfo(x)[3]:
    #            m = re.search(r'([a-zA-Z0-9][a-zA-Z0-9_]*)\s*=\s*([a-zA-Z0-9][a-zA-Z0-9_]*)',line)
    #            if m:
    #                self.__name = m.group(1)
    #                return 
    #        x = x.f_back
