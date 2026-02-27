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
        name = getattr(self.bits, 'var_name', self.bits.__class__.__name__)
        return '%s is expected a "int" or "string" to declare width (and value),but get "%s"' % (name, self.int_or_string.__class__.__name__)


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


# ── Struct-specific exceptions ──────────────────────────────────────
class ErrTypeMismatch(ErrUHDL):
    """Raised when two typed signals with different typedef identity are connected."""

    def __init__(self, lvalue, rvalue, ltype=None, rtype=None, type_kind="Type"):
        self.lvalue = lvalue
        self.rvalue = rvalue
        self.ltype = ltype
        self.rtype = rtype
        self.type_kind = type_kind

    def __str__(self):
        lname = getattr(self.lvalue, 'full_hier', str(self.lvalue))
        rname = getattr(self.rvalue, 'full_hier', str(self.rvalue))
        lt = self.ltype or 'unknown'
        rt = self.rtype or 'unknown'
        return (f"{self.type_kind} type mismatch: lhs {lname} (type {lt}) "
                f"cannot be connected to rhs {rname} (type {rt}). "
                f"{self.type_kind} connections require identical typedef identity.")

class ErrStructTypeMismatch(ErrTypeMismatch):
    def __init__(self, lvalue, rvalue, ltype=None, rtype=None):
        super().__init__(lvalue, rvalue, ltype, rtype, type_kind="Struct")

class ErrFieldNotFound(ErrUHDL):
    """Raised when accessing a nonexistent field on a port."""

    def __init__(self, port, field_name, available_fields=None, type_kind="Field"):
        self.port = port
        self.field_name = field_name
        self.available_fields = available_fields or []
        self.type_kind = type_kind

    def __str__(self):
        port_name = getattr(self.port, 'full_hier', str(self.port))
        avail = ', '.join(self.available_fields) if self.available_fields else 'none'
        return (f"{self.type_kind} field '{self.field_name}' not found on {port_name}. "
                f"Available fields: [{avail}]")

class ErrStructFieldNotFound(ErrFieldNotFound):
    def __init__(self, struct_port, field_name, available_fields=None):
        super().__init__(struct_port, field_name, available_fields, type_kind="Struct")

class ErrStructIllegalDecompose(ErrUHDL):
    """Raised when an illegal decomposition is attempted on a struct signal."""

    def __init__(self, str_in):
        self.str = str_in

    def __str__(self):
        return f"Illegal struct decomposition: {self.str}"


class ErrStructIncompatibleExpression(ErrUHDL):
    """Raised when a struct signal is used in an incompatible expression context."""

    def __init__(self, str_in):
        self.str = str_in

    def __str__(self):
        return f"Incompatible expression on struct type: {self.str}"


# ── Enum-specific exceptions ────────────────────────────────────────────────────────────
class ErrEnumTypeMismatch(ErrTypeMismatch):
    def __init__(self, lvalue, rvalue, ltype=None, rtype=None):
        super().__init__(lvalue, rvalue, ltype, rtype, type_kind="Enum")

# ── Union-specific exceptions ───────────────────────────────────────────────────────────
class ErrUnionTypeMismatch(ErrTypeMismatch):
    def __init__(self, lvalue, rvalue, ltype=None, rtype=None):
        super().__init__(lvalue, rvalue, ltype, rtype, type_kind="Union")

class ErrUnionFieldNotFound(ErrFieldNotFound):
    def __init__(self, union_port, field_name, available_fields=None):
        super().__init__(union_port, field_name, available_fields, type_kind="Union")
