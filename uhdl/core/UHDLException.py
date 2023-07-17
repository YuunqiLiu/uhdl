from . import Config
from .Terminal import Terminal

class ErrUHDL(ArithmeticError):
    pass

class ErrUHDLStr(ErrUHDL):

    def __init__(self,str_in):
        self.str = str_in

    def __str__(self):
        return self.str

class ErrBitsValOverflow(ErrUHDLStr):
    pass

class ErrBitsInvalidStr(ErrUHDLStr):
    pass

class ErrVarCmpWrong(ErrUHDLStr):
    pass
    #def __init__(self,str_in):
    #    self.str = str_in

    #def __str__(self):
    #    return self.str


class ErrNeedBool(ErrUHDLStr):
    pass
    #def __init__(self,str_in):
    #    self.str = str_in

    #def __str__(self):
    #    return self.str

class ErrAssignTypeWrong(ErrUHDL):

    def __init__(self,variable,right_value):
        self.variable    = variable
        self.right_value = right_value

    def __str__(self):
        return '%s is expected to be connected by "Rvalue(rhs)",but is currently connected by %s.' % (self.variable.var_name,self.right_value.__class__.__name__)

def raise_ErrAssignTypeWrong(self,rvalue):
    raise ErrAssignTypeWrong(self,rvalue)


class ErrConstInWrong(ErrUHDL):

    def __init__(self,bits,int_or_string):
        self.bits           = bits
        self.int_or_string  = int_or_string

    def __str__(self):
        return '%s is expected a "int" or "string" to declare width (and value),but get "%s"' % (self.bits.var_name,self.int_or_string.__class__.__name__)


class ErrAttrTypeWrong(ErrUHDL):

    def __init__(self,variable,attribute):
        self.variable  = variable
        self.attribute = attribute

    def __str__(self):
        return '%s expect a "Constant(Bits,UInt,SInt or ...)" as attribute,but get "%s"' % (self.variable.var_name,self.attribute.__class__.__name__)


class ErrListExpNeedMultiOp(ErrUHDL):

    def __init__(self,str_in,*var_list):
        self.str        = str_in
        self.var_list   = var_list

    def __str__(self):
        return "MutiListExpression need more than one \"Right Value(rhs)\",but only get %s:\n" % len(self.var_list) + '\n'.join(['\t%s' %x for x in self.var_list]) 


class ErrLogicSigAttrWrong(ErrUHDL):

    def __init__(self,str_in,op):
        self.str = str_in
        self.op = op

    def __str__(self):
        return "%s\n\t%s must have the same attribute as UInt(1) as a boolean rhs,but it's attribute is %s" %(self.str,self.op,self.op.attribute)


class ErrExpInTypeWrong(ErrUHDL):

    def __init__(self,str_in,op,var):
        self.op        = op
        self.str       = str_in
        self.var       = var

    def __str__(self):
        return "%s\n\"%s\" Expression expect a \"Right Value(rhs)\" input but get a \"%s\" with value %s" %(self.str,self.op.op_name,self.var.__class__.__name__,self.var)


class ErrAttrMismatch(ErrUHDL):

    def __init__(self,str_in,*var_list):
        self.str        = str_in
        self.var_list   = var_list

    def __str__(self):
        string = "".join(["\n\t%s" % x for x in self.var_list])
        return "%s\nAttribute Mismatch:%s" % (self.str,string)

def raise_ErrAttrMismatch(str_in,*var_list):
    #print('asfasdfaf')
    #print(Config.IGNORE_ERROR)
    err = ErrAttrMismatch(str_in,*var_list)
    if Config.IGNORE_ERROR:
        #pass
        Terminal.error(err)
    else:
        raise ErrAttrMismatch(str_in,*var_list)



class ErrCutExpSliceInvalid(ErrUHDL):

    def __init__(self,exp,str_in):
        self.exp = exp
        self.str = str_in

    def __str__(self):
        return '%s has invalid slice [%s:%s]:\n\t%s' % (self.exp.op.name,self.exp.hbound,self.exp.lbound,self.str)


class ErrWhenExpOperateWrong(ErrUHDL):

    def __init__(self,str_in):
        self.str = str_in

    def __str__(self):
        return 'The When expression is incorrectly constructed,and the order of using the construction method is incorrect:\t\n%s' % self.str
    

class ErrVarNotBelongComponent(ErrUHDL):

    def __init__(self,variable):
        self.__var = variable
    
    def __str__(self):
        return 'Variable used to assign should belong to a Component.'

def raise_ErrVarNotBelongComponent(variable):
    raise ErrVarNotBelongComponent(variable)
