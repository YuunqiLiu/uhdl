
#from .Value import Value
from .Variable import *
from .Operator import *
from functools import reduce
from .Root      import Root
from .Component import *




def _smart_assign_core(op1, op2, outer=False):
    op1_component = op1.father_until(Component)
    op2_component = op2.father_until(Component)

    # Import Enum/Union IO types along with StructIO
    from .Variable import InputStructIO, OutputStructIO, InputEnumIO, OutputEnumIO, InputUnionIO, OutputUnionIO
    
    # Define type groups for direction checks
    _input_types = (Input, InputStructIO, InputEnumIO, InputUnionIO)
    _output_types = (Output, OutputStructIO, OutputEnumIO, OutputUnionIO)
    
    # Check if either operand is a valid IO type (including Struct/Enum/Union IO)
    valid_io_types = (Input, Output, Inout, InputStructIO, OutputStructIO, InputEnumIO, OutputEnumIO, InputUnionIO, OutputUnionIO)
    
    if (not isinstance(op1, valid_io_types)) or (not isinstance(op2, valid_io_types)):
        raise ErrUHDLStr("smart assign only used for IO connection, at least one of op1 %s and op2 %s should be Input, Output, Inout, or a Struct/Enum/Union IO variant." % (op1, op2))
    
    
    
    if isinstance(op1, (Input, Output, InputStructIO, OutputStructIO, InputEnumIO, OutputEnumIO, InputUnionIO, OutputUnionIO)) and isinstance(op2, (Input, Output, InputStructIO, OutputStructIO, InputEnumIO, OutputEnumIO, InputUnionIO, OutputUnionIO)):
        if op1_component.father is op2_component:
            # op1 in low level
            #    ----------------------
            #    |                    |
            #    |    ---------       |
            #    |    |       |       |
            #    |    |  (op1)-  (op2)|
            #    |    |       |       |
            #    |    ---------       |
            #    |                    |
            #    ----------------------
            #
            #   case1:
            #       op1 is Input/InputStructIO/InputEnumIO/InputUnionIO, op1 should be lhs.
            #   case2:
            #       op1 is Output/OutputStructIO/OutputEnumIO/OutputUnionIO, op1 should be rhs.
            #
            if isinstance(op1, _input_types):
                op1 += op2
            elif isinstance(op1, _output_types):
                op2 += op1
            else:
                raise ErrUHDLStr("op1 %s's father Component is in op2 %s's father Component, so op1 should be an input-like or output-like IO." % (op1, op2))

        elif op2_component.father is op1_component:
            # op2 in low level
            #    ----------------------
            #    |                    |
            #    |    ---------       |
            #    |    |       |       |
            #    |    |  (op2)-  (op1)|
            #    |    |       |       |
            #    |    ---------       |
            #    |                    |
            #    ----------------------
            #
            #   case1:
            #       op2 is Input/InputStructIO/InputEnumIO/InputUnionIO, op2 should be lhs.
            #   case2:
            #       op2 is Output/OutputStructIO/OutputEnumIO/OutputUnionIO, op2 should be rhs.
            #
            if isinstance(op2, _input_types):
                op2 += op1
            elif isinstance(op2, _output_types):
                op1 += op2
            else:
                raise ErrUHDLStr("op2 %s's father Component is in op1 %s's father Component, so op2 should be an input-like or output-like IO." % (op2, op1))

        elif op1_component is op2_component:
            if outer:
                # outer connection.
                #    -------------------
                #    |                 |
                #  ---(op1)-------(op2)---
                #  | |                 | |
                #  | ------------------- |
                #  |                     |
                #  -----------------------
                if isinstance(op1, _input_types) and isinstance(op2, _output_types):
                    op1 += op2
                elif isinstance(op2, _input_types) and isinstance(op1, _output_types):
                    op2 += op1
                else:
                    raise ErrUHDLStr("op1 %s and op2 %s have same father Component, so op1 and op2 should have different direction." % (op1, op2))

            else:
                # inter connection.
                #    -------------------
                #    |                 |
                #    -(op1)-------(op2)-
                #    |                 |
                #    -------------------
                if isinstance(op1, _input_types) and isinstance(op2, _output_types):
                    op2 += op1
                elif isinstance(op2, _input_types) and isinstance(op1, _output_types):
                    op1 += op2
                else:
                    raise ErrUHDLStr("op1 %s and op2 %s have same father Component, so op1 and op2 should have different direction." % (op1, op2))

        elif op1_component.father is op2_component.father:
            # same level connection.
            #    ------------------   ------------------
            #    |                |   |                |
            #    |           (op1)-   -(op2)           |
            #    |                |   |                |
            #    ------------------   ------------------
            if isinstance(op1, _input_types) and isinstance(op2, _output_types):
                op1 += op2
            elif isinstance(op2, _input_types) and isinstance(op1, _output_types):
                op2 += op1
            else:
                raise ErrUHDLStr("op1 %s's father Component and op2 %s's father Component are in same Component, so op1 and op2 should have different direction." % (op1, op2))

        else:
            # illegal hier.
            raise ErrUHDLStr("The hier where op1 %s and op2 %s are located cannot be legally connected." % (op1, op2))
    elif isinstance(op1, Inout) and isinstance(op2, Inout):
        print("inout")
        op1 += op2 
    elif isinstance(op1, Inout):
        raise ErrUHDLStr("op1 %s is Inout, but op2 %s is not." % (op1, op2))
    elif isinstance(op1, Inout):
        raise ErrUHDLStr("op2 %s is Inout, but op1 %s is not." % (op2, op1))
    else:
        raise ErrUHDLStr("smart assign illegal case.")




def Assign(opl:Value, opr:Value):
    tmp = opl
    tmp += opr

def SmartAssign(op1, op2, outer=False):

    if isinstance(op1, Bundle) and isinstance(op2, Bundle):
        op1_list = op1.as_list()
        op2_list = op2.as_list()

        for opl, opr in zip(op1_list, op2_list):
            SmartAssign(opl, opr, outer)

    elif isinstance(op1, list) and isinstance(op2, list):

        for opl, opr in zip(op1, op2):
            SmartAssign(opl, opr, outer)

    elif isinstance(op1, Variable) and isinstance(op2, Variable):
        _smart_assign_core(op1, op2, outer)




    # if not hasattr(op1, 'father'): # father until ?
    #     raise Exception('%s doesn\'t in a module.')


    # if isinstance(op1,Input):
    #     if hasattr(op2,'father') and op1.father is op2.father and outer: Assign(op1,op2)
    #     else:                                                            Assign(op2,op1)
    # elif isinstance(op2,Input):
    #     if hasattr(op1,'father') and op1.father is op2.father and outer: Assign(op2,op1)
    #     else:                                                            Assign(op1,op2)
    # else:
    #     raise Exception()

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
        #print(lhs.attribute.width)


def BitMask(vector, mask):
    return BitAnd(vector, Fanout(mask, vector.attribute.width))


def Exclude(io_list, exclude_list):
    pattern = '|'.join(exclude_list)
    io_list_new=[]
    for io in io_list:
        if not re.search(pattern, io.name):
            io_list_new.append(io)
    return io_list_new
