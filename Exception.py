

class ErrListExpNeedMultiOp(ArithmeticError):

    def __init__(self,str_in,*var_list):
        self.str        = str_in
        self.var_list   = var_list

    def __str__(self):
        return "MutiListExpression need more than one \"Right Value(rhs)\",but only get %s:\n" % len(self.var_list) + '\n'.join(['\t%s' %x for x in self.var_list]) 

class ErrLogicSigAttrWrong(ArithmeticError):

    def __init__(self,str_in,op):
        self.str = str_in
        self.op = op

    def __str__(self):
        return "%s\n\t%s must have the same attribute as UInt(1) as a boolean rhs,but it's attribute is %s" %(self.str,self.op,self.op.attribute)


class ErrExpInTypeWrong(ArithmeticError):

    def __init__(self,str_in,op,var):
        self.op        = op
        self.str       = str_in
        self.var       = var

    def __str__(self):
        return "%s\n\"%s\" Expression expect a \"Right Value(rhs)\" input but get a \"%s\" with value %s" %(self.str,self.op.op_name,self.var.__class__.__name__,self.var)


class ErrAttrMismatch(ArithmeticError):

    def __init__(self,str_in,*var_list):
        self.str        = str_in
        self.var_list   = var_list

    def __str__(self):
        string = "".join(["\n\t%s" % x for x in self.var_list])
        return "%s\nAttribute Mismatch:%s" % (self.str,string)


class ErrCutExpSliceInvalid(ArithmeticError):

    def __init__(self,exp,str_in):
        self.exp = exp
        self.str = str_in

    def __str__(self):
        return '%s has invalid slice [%s:%s]:\n\t%s' % (self.exp.op.name,self.exp.hbound,self.exp.lbound,self.str)

class ErrWhenExpOperateWrong(ArithmeticError):

    def __init__(self,str_in):
        self.str = str_in

    def __str__(self):
        return 'The When expression is incorrectly constructed,and the order of using the construction method is incorrect:\t\n%s' % self.str