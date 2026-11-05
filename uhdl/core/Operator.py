from .Variable import *
from .Variable import _coerce_pair, _lit, _known_attr


def _is_uint_const(v):
    return isinstance(v, UInt)


def _fold_compare(opL, opR, kind):
    '''Return UInt(1, x) when a comparison against a constant is always true/false
    for the variable's width (e.g. 3'b111 >= ptr). Emitting such compares makes
    Verilator report CMPCONST/UNSIGNED, so they are folded here.'''
    if not hasattr(opL, 'attribute') or not hasattr(opR, 'attribute') or opL.attribute != opR.attribute:
        return None     # let the expression raise its usual type/width error
    if _is_uint_const(opL) and _is_uint_const(opR):
        a, b = opL.value, opR.value
        res = {'ge': a >= b, 'le': a <= b, 'gt': a > b, 'lt': a < b}[kind]
        return UInt(1, int(res))
    if _is_uint_const(opR) and not _is_uint_const(opL) and isinstance(opL.attribute, UInt):
        top, c = (1 << opL.attribute.width) - 1, opR.value
        if kind == 'ge' and c == 0:   return UInt(1, 1)
        if kind == 'lt' and c == 0:   return UInt(1, 0)
        if kind == 'le' and c == top: return UInt(1, 1)
        if kind == 'gt' and c == top: return UInt(1, 0)
    if _is_uint_const(opL) and not _is_uint_const(opR) and isinstance(opR.attribute, UInt):
        top, c = (1 << opR.attribute.width) - 1, opL.value
        if kind == 'le' and c == 0:   return UInt(1, 1)
        if kind == 'gt' and c == 0:   return UInt(1, 0)
        if kind == 'ge' and c == top: return UInt(1, 1)
        if kind == 'lt' and c == top: return UInt(1, 0)
    return None


def Cat(*items):
    '''Concatenate LSB first: Cat(a, b, c) == Combine(c, b, a), so item i of a
    per-index list lands at bits [i*w +: w]. Also takes one list: Cat(lst).'''
    if len(items) == 1 and isinstance(items[0], (list, tuple)):
        items = items[0]
    if len(items) == 0:
        raise ErrUHDLStr('Cat() needs at least one value.')
    return Combine(*reversed(list(items)))


def If(cond, a, b):
    '''Two-way mux: a when cond is 1, else b. Same as when(cond).then(a).otherwise(b).'''
    return WhenExpression().when(cond).then(a).otherwise(b)


def Mux(sel, values):
    '''Index a list with a signal: values[sel]. Values may be signals or ints.
    If the list does not cover every select value, out-of-range selects give 0.'''
    values = list(values)
    w = sel.attribute.width
    if not values:
        raise ErrUHDLStr('Mux() needs at least one value.')
    if len(values) > (1 << w):
        raise ErrUHDLStr('Mux: %d values, but a %d-bit select reaches only %d of them.' % (len(values), w, 1 << w))
    pairs = [(UInt(w, i), v) for i, v in enumerate(values)]
    return CaseExpression(sel, pairs, None if len(values) == (1 << w) else 0)


def Priority(pairs, default):
    '''Priority mux from a list of (condition, value): the first true condition wins,
    otherwise default. Same as an EmptyWhen() chain built in a loop.'''
    pairs = list(pairs)
    if not pairs:
        return default
    ch = WhenExpression()
    for c, v in pairs:
        ch.when(c).then(v)
    return ch.otherwise(default)


def WrapAdd(A, B):
    '''A + B with the result truncated to the operand width (modulo 2**width).
    Use this for counters and pointers instead of Cut(A + B, w-1, 0).'''
    return WrapAddExpression(A, B)


def WrapSub(A, B):
    '''A - B with the result truncated to the operand width (modulo 2**width).'''
    return WrapSubExpression(A, B)


def Case(select, casepair, default):
    """
    Case is used to construct a parallel selection circuit,and the input of this function is

        rhs select    - UInt/SInt(k)
        rhs casepair  - list[(UInt/SInt(k),UInt/SInt(v)),...,(UInt/SInt(k),UInt/SInt(v))] 
                        OR dict{UInt/SInt(k): UInt/SInt(v), ...}
        rhs default   - UInt/SInt(v)

    select is the selection signal.

    casepair can be either:
    1. A lookup table organized as a list of tuples. Each tuple expresses a mapping relationship.
       When sel equals the first value in the tuple, the output is the second value of the tuple.
    2. A dictionary where keys are selection values and values are corresponding outputs.
       When sel equals a key, the output is the corresponding value.

    default is the default output value of the circuit. 
    When sel does not match any item in the lookup table, the circuit will output this value.
    
    The return value of this function is 
    
        rhs O - UInt/SInt(v)

    Typical examples:

    Using list of tuples:
        O += Case(sel,[(UInt(2,0),Ares),(UInt(2,1),Bres)],DFTres)

    Using dictionary:
        O += Case(sel,{UInt(2,0):Ares, UInt(2,1):Bres}, DFTres)

    Both examples correspond to the same behavior: 

        case(sel)
        2'b0:       O = Ares
        2'b1:       O = Bres
        default:    O = DFTres
        endcase

    select and the first value of tuple in casepair list must have the same attributes, that is, all UInt(k) or SInt(k).

    default and the second value of tuple in casepair list mus have the sam attributss, that is, all UInt(v) or SInt(v).
    
    """
    if default is None:
        n_keys = len(casepair)
        if n_keys < (1 << select.attribute.width):
            from .Terminal import Terminal
            Terminal.warning('Case on %d-bit select covers %d of %d values and has no default: '
                             'combinational use will infer a latch. Pass a default.' %
                             (select.attribute.width, n_keys, 1 << select.attribute.width))
    return CaseExpression(select, casepair, default)


def EmptyWhen():
    '''
    EmptyWhen is used to construct a complex selection circuit, it has no input.

    EmptyWhen is only used to construct a temporarily empty selection circuit, 
    which is used to allow users to use "when", "then", "otherwise" methods to complete the selection circuit
    
    A typical example is:

        ew = EmptyWhen()
        for cond,dat in CondDatPair:
            ew = ew.when(cond).then(dat)
        ew.otherwise(UInt(32,0))
        O += ew

    The behavior model corresponding to this typical example is:

        if(cond0)       O = dat0
        else if(cond1)  O = dat1
        else if(cond2)  O = dat2
        ..
        else if（condN) O = datN
        else            O = 32'b0

        
    '''
    return WhenExpression()

def When(val):
    '''
    When is used to construct a complex selection circuit, and the input of when is 
        
        rhs I - UInt(1)
        
    The return value of when will only be calculated after the when selection circuit is completed. 
    When the when selection circuit uses multiple "when", "then", "otherwise" completions, 
    the attribute of its return value O will be the same as the input specified by "then" and "otherwise".
    
    A typical example is:

        when(A).then(Ares).when(B).then(Bres).otherwise(DFTres)

    The corresponding behavior of this selection circuit example it expresses is 

        if(A)       O = Ares
        else if(B)  O = Bres
        else        O = DFTres
    '''
    when = WhenExpression()
    return when.when(val)


def Cut(I, H, L):
    '''
    The circuit expressed by this function takes 
        
        rhs I - UInt/SInt(a)
        int H - 0 <= H < I.width
        int L - 0 <= L <= H
    
    as input to realize a circuit that intercepts the [H:L] bits of A.

    The return value of this function is 
    
        rhs O - UInt/SInt(H-L+1)

    The corresponding behavior model it expresses is 
    
        O = I[H:L]

    The attribute type of the return value is the same as the input I.
    '''
    return CutExpression(I, H, L)


def Fanout(A,F):
    return FanoutExpression(A, F)



def Combine(*rhs_list):
    '''
    The circuit expressed by this function takes 
        
        rhs A - UInt/SInt(a)
        rhs B - UInt/SInt(b)
        ..
        rhs N - UInt/SInt(n)
    
    as input to realize a circuit that splices all input signals together.

    The return value of this function is 
    
        rhs O - UInt/SInt(a+b+..+n)

    The corresponding behavior model it expresses is 
    
        O = {A,B,...,N}

    The attribute type of the return value is the same as the input.
    
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    if len(rhs_list) == 1:
        return rhs_list[0]
    return CombineExpression(*rhs_list)

def Inverse(I):
    '''
    The circuit expressed by this function takes 
        
        rhs I - UInt/SInt(x)
    
    as input to realize an inverter used to inverse each bit of I.

    The return value of this function is 
    
        rhs O - UInt/SInt(x)

    The corresponding behavior model it expresses is 
    
        O = ~ I

    The attribute type of the return value is the same as the input.
    '''
    return InverseExpression(I)


def Not(I):
    '''
    The circuit expressed by this function takes 
        
        rhs I - UInt/SInt(x)
    
    as input to realize a comparator used to confirm whether I is not equal to 0.

    The return value of this function is 
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if (I==0) O = 1'b1
        else      O = 1'b0
    '''
    return NotExpression(I)


def SelfOr(I):
    '''
    The circuit expressed by this function takes 
        
        rhs I - UInt/SInt(x)
    
    as input to realize a circuit that or all bits of the input signal.

    The return value of this function is 
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        O = | I
    '''
    return SelfOrExpression(I)

def SelfAnd(I):
    '''
    The circuit expressed by this function takes 
        
        rhs I - UInt/SInt(x)
    
    as input to realize a circuit that and all bits of the input signal.

    The return value of this function is 
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        O = & I
    '''
    return SelfAndExpression(I)


def SelfXor(op):
    '''
    The circuit expressed by this function takes 
        
        rhs I - UInt/SInt(x)
    
    as input to realize a circuit that xor all bits of the input signal.

    The return value of this function is 
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        O = ^ I
    '''
    return SelfXorExpression(op)


def SelfXnor(I):
    '''
    The circuit expressed by this function takes 
        
        rhs I - UInt/SInt(x)
    
    as input to realize a circuit that xnor all bits of the input signal.

    The return value of this function is 
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        O = ^~ I
    '''
    return SelfXnorExpression(I)


def Add(A,B):
    '''
    The circuit expressed by this function takes 
        
        rhs A - UInt/SInt(a)
        rhs B - UInt/SInt(b)
    
    as input to realize an adder that adds A and B. 

    The return value of this function is 
    
        rhs O - UInt/SInt(max(a,b)+1)

    The corresponding behavior model it expresses is 
    
        O = A + B

    The attribute type of the return value is the same as the input.
    
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return AddExpression(A,B)


def Sub(A,B):
    '''
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(a)
        rhs B - UInt/SInt(b)

    as input to realize a subtractor that subtracts A and B. 

    The return value of this function is
    
        rhs O - UInt/SInt(max(a,b)+1)
    
    The corresponding behavior model it expresses is 
    
        O = A - B

    The attribute type of the return value is the same as the input.

    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return SubExpression(A,B)

def Mul(A,B):
    '''
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(a)
        rhs B - UInt/SInt(b)

    as input to realize a multiplier that multiplies A and B. 
    
    The return value of this function is
    
        rhs O - UInt/SInt(a+b)

    The corresponding behavior model it expresses is
    
        O = A * B
        
    The attribute type of the return value is the same as the input.

    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return MulExpression(A,B)






def BitOr(*opList):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)
        ....
        rhs N - UInt/SInt(x)

    as input to realize a circuit that "or" A and B and ... and N bit by bit.

    The return value of this function is
    
        rhs O - UInt/SInt(x)

    The corresponding behavior model it expresses is 
    
        O = A | B | ... | N

    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return BitOrListExpression(*opList)

BitOrList = BitOr

#def BitOrList(*opList):
#    return BitOrListExpression(*opList)


def BitAnd(*opList):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)
        ...
        rhs N - UInt/SInt(x)

    as input to realize a circuit that "and" A and B and ... and N bit by bit.

    The return value of this function is
    
        rhs O - UInt/SInt(x)

    The corresponding behavior model it expresses is 
    
        O = A & B & ... & N

    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return BitAndListExpression(*opList)

BitAndList = BitAnd

#def BitAndList(*opList):
#    return BitAndListExpression(*opList)







def BitXor(*opList):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)
        ...
        rhs N - UInt/SInt(x)

    as input to realize a circuit that "xor" A and B and ... and N bit by bit.

    The return value of this function is
    
        rhs O - UInt/SInt(x)

    The corresponding behavior model it expresses is 
    
        O = A ^ B ^ ... ^ N

    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''

    return BitXorListExpression(*opList)

BitXorList = BitXor

#def BitXorList(*opList):
#    return BitXorListExpression(*opList)


def BitXnor(*opList):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)
        ...
        rhs N - UInt/SInt(x)

    as input to realize a circuit that "xnor" A and B and ... and N bit by bit.

    The return value of this function is
    
        rhs O - UInt/SInt(x)

    The corresponding behavior model it expresses is 
    
        O = A ^~ B ^~ ... ^~ N

    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return BitXnorListExpression(*opList)


BitXnorList = BitXnor
#def BitXnorList(*opList):
#    return BitXnorListExpression(*opList)



def Equal(A,B):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)

    as input to realize a comparator to compare whether A and B are equal.

    The return value of this function is
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if(A==B) O = 1'b1
        else     O = 1'b0
 
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return EqualExpression(A,B)



def NotEqual(A,B):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)

    as input to realize a comparator to compare whether A and B are not equal.

    The return value of this function is
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if(A!=B) O = 1'b1
        else     O = 1'b0
 
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return NotEqualExpression(A,B)


def LessEqual(A,B):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)

    as input to realize a comparator to compare whether A is less equal than B.

    The return value of this function is
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if(A<=B) O = 1'b1
        else     O = 1'b0
 
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    A, B = _coerce_pair(A, B, 'LessEqual')
    folded = _fold_compare(A, B, 'le')
    if folded is not None:
        return folded
    return LessEqualExpression(A,B)


def GreaterEqual(lhs,rhs):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)

    as input to realize a comparator to compare whether A is greater equal than B.

    The return value of this function is
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if(A>=B) O = 1'b1
        else     O = 1'b0
 
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    lhs, rhs = _coerce_pair(lhs, rhs, 'GreaterEqual')
    folded = _fold_compare(lhs, rhs, 'ge')
    if folded is not None:
        return folded
    return GreaterEqualExpression(lhs,rhs)


def Less(opL,opR):
    '''
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)

    as input to realize a comparator to compare whether A is less than B.

    The return value of this function is
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if(A<B) O = 1'b1
        else    O = 1'b0
 
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    opL, opR = _coerce_pair(opL, opR, 'Less')
    folded = _fold_compare(opL, opR, 'lt')
    if folded is not None:
        return folded
    return LessExpression(opL,opR)


def Greater(opL,opR):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)

    as input to realize a comparator to compare whether A is greater than B.

    The return value of this function is
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if(A>B) O = 1'b1
        else    O = 1'b0
 
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    opL, opR = _coerce_pair(opL, opR, 'Greater')
    folded = _fold_compare(opL, opR, 'gt')
    if folded is not None:
        return folded
    return GreaterExpression(opL,opR)








def And(*opList):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)
        ...
        rhs N - UInt/SInt(x)

    as input to realize a comparator to compare whether both A and B and ... and N not equal to 0.

    The return value of this function is
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if((A!=0) && (B!=0) && (...!=0) && (N!=0))  O = 1'b1
        else                                        O = 1'b0
 
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return AndListExpression(*opList)

AndList = And

#def AndList(*opList):
#    return AndListExpression(*opList)


def Or(*opList):
    ''' 
    The circuit expressed by this function takes 
    
        rhs A - UInt/SInt(x)
        rhs B - UInt/SInt(x)
        ...
        rhs N - UInt/SInt(x)


    as input to realize a comparator to compare whether A or B or ... or N not equal to 0.

    The return value of this function is
    
        rhs O - UInt(1)

    The corresponding behavior model it expresses is 
    
        if((A!=0) || (B!=0) || (...!=0) || (N!=0))  O = 1'b1
        else                                        O = 1'b0
 
    This function requires its input to have the same type of attributes, that is, all UInt or SInt.
    '''
    return OrListExpression(*opList)

OrList = Or

#def OrList(*opList):
#    return OrListExpression(*opList)