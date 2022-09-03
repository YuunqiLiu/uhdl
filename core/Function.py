
#from .Value import Value
from .Variable import *
from functools import reduce
from .Root      import Root



def Assign(opl:Value,opr:Value):
    tmp = opl
    tmp += opr

def SmartAssign(op1:Value,op2:Value,outer=False):
    if isinstance(op1,Input):
        if hasattr(op2,'father') and op1.father is op2.father and outer: Assign(op1,op2)
        else:                                                            Assign(op2,op1)
    elif isinstance(op2,Input):
        if hasattr(op1,'father') and op1.father is op2.father and outer: Assign(op2,op1)
        else:                                                            Assign(op1,op2)
    else:
        raise Exception()

def LCA(*node_list):
    tree_list = [x.ancestors() for x in node_list]
    common_path = list(reduce(lambda x,y:set(x)&set(y),tree_list))
    return None if not common_path else common_path[0]

def Linkable(op1,op2):
    if isinstance(op1,Input) and not isinstance(op2,Input):
        return True
    elif isinstance(op2,Input) and not isinstance(op1,Input):
        return True
    else:
        return False




def Unpack(rhs,*lhs_list):
    lhs_width_sum = sum([x.attribute.width for x in lhs_list])
    rhs_width = rhs.attribute.width

    if rhs_width != lhs_width_sum:
        print('RHS:%s' % rhs)
        print('LHS list with width sum:%s' % lhs_width_sum)
        for lhs in lhs_list:
            print('    %s' % lhs)
        raise Exception('lhs list width sum not equal rhs.')

    ptr = 0
    for lhs in reversed(lhs_list):
        width = lhs.attribute.width
        lhs += rhs[ptr+width-1:ptr]
        ptr = ptr+width
        print(lhs.attribute.width)


def BitMask(vector, mask):
    return BitAnd(vector, Fanout(mask, vector.attribute.width))