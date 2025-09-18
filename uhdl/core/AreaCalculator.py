"""
UHDL Area Calculator

This module provides unified area calculation functions for Expression and Reg components in UHDL.
The area calculations for these specific component types are centralized here to maintain 
consistency and allow easy modification of area models.

Area values are normalized relative values, not absolute physical areas.
They represent relative resource usage for comparison purposes.
"""

# Area calculation function registry for Expression and Reg types only
# Maps class names to their corresponding calculation functions
# Each type uses direct lambda functions for area calculation
AREA_CALCULATORS = {
    # Register types - Reg objects always have attribute.width
    'Reg': lambda reg: reg.attribute.width * 0.1,
    
    # Arithmetic Expression types
    'AddExpression'     : lambda expr: expr.attribute.width * 4.0,  # Carry lookahead adder: ~4 gates per bit (including group-level carry logic)
    'SubExpression'     : lambda expr: expr.attribute.width * 4.0,  # Subtractor: CLA + inverter + carry logic (~4.5 gates per bit)
    'MulExpression'     : lambda expr: expr.attribute.width ** 2 * 0.8,  # Booth multiplier: ~0.8 gates per bit² (partial product reduction + booth encoding)
    
    # Logical Expression types - operate on entire vectors and produce 1-bit result
    'AndExpression'     : lambda expr: expr.opL.attribute.width + expr.opR.attribute.width - 1,  # Logic AND: reduction OR for each input + 1 AND gate
    'OrExpression'      : lambda expr: expr.opL.attribute.width + expr.opR.attribute.width - 1,  # Logic OR: reduction AND for each input + 1 OR gate
    
    # Bitwise Expression types - each bit requires one logic gate
    'BitAndExpression'  : lambda expr: expr.attribute.width * 1.0,  # 1 AND gate per bit
    'BitOrExpression'   : lambda expr: expr.attribute.width * 1.0,  # 1 OR gate per bit  
    'BitXorExpression'  : lambda expr: expr.attribute.width * 1.0,  # 1 XOR gate per bit
    'BitXnorExpression' : lambda expr: expr.attribute.width * 1.0,  # 1 XNOR gate per bit
    'InverseExpression' : lambda expr: expr.attribute.width * 1.0,  # 1 NOT gate per bit
    
    # Single operand logic expressions - reduction operations
    'NotExpression'     : lambda expr: expr.op.attribute.width,  # Logic NOT: reduction OR (n-1) + NOT gate (1) = n gates
    'SelfOrExpression'  : lambda expr: expr.op.attribute.width,  # Reduction OR: n-1 OR gates
    'SelfAndExpression' : lambda expr: expr.op.attribute.width,  # Reduction AND: n-1 AND gates  
    'SelfXorExpression' : lambda expr: expr.op.attribute.width,  # Reduction XOR: n-1 XOR gates
    'SelfXnorExpression': lambda expr: expr.op.attribute.width,  # Reduction XNOR: n-1 XNOR gates
    
    # List-based logical expressions (multi-input operations)
    'AndListExpression'    : lambda expr: sum(op.attribute.width for op in expr.op_list) - len(expr.op_list) + 1,  # Multi-input logic AND
    'OrListExpression'     : lambda expr: sum(op.attribute.width for op in expr.op_list) - len(expr.op_list) + 1,  # Multi-input logic OR
    'BitAndListExpression' : lambda expr: expr.attribute.width * (len(expr.op_list) - 1),  # Multi-input bitwise AND
    'BitOrListExpression'  : lambda expr: expr.attribute.width * (len(expr.op_list) - 1),  # Multi-input bitwise OR
    'BitXorListExpression' : lambda expr: expr.attribute.width * (len(expr.op_list) - 1),  # Multi-input bitwise XOR
    'BitXnorListExpression': lambda expr: expr.attribute.width * (len(expr.op_list) - 1),  # Multi-input bitwise XNOR
    
    # Shift Expression types - Barrel shifter with m levels of 2:1 MUX per bit
    'LeftShift'         : lambda expr: expr.attribute.width * expr.opR.attribute.width,  # n-bit data × m-bit shift amount × 1 gate per MUX level
    'RightShift'        : lambda expr: expr.attribute.width * expr.opR.attribute.width,  # n-bit data × m-bit shift amount × 1 gate per MUX level
    
    # Wire/routing Expression types
    'CutExpression'     : lambda expr: 0.0,  # Cut expressions are just wire routing, no area cost
    'CombineExpression' : lambda expr: 0.0,  # Wire routing, minimal cost
    'FanoutExpression'  : lambda expr: 0.0,  # Fanout is just wire branching, no area cost
    
    # Comparison Expression types - all operate on same-width inputs and produce 1-bit result
    'EqualExpression'      : lambda expr: 2 * expr.opL.attribute.width,  # n XNOR gates + (n-1) AND gates
    'NotEqualExpression'   : lambda expr: 2 * expr.opL.attribute.width,      # Equal + 1 NOT gate
    'GreaterExpression'    : lambda expr: expr.opL.attribute.width * 2.5,    # Complex magnitude comparator
    'GreaterEqualExpression': lambda expr: expr.opL.attribute.width * 2.5,   # Complex magnitude comparator
    'LessExpression'       : lambda expr: expr.opL.attribute.width * 2.5,    # Complex magnitude comparator  
    'LessEqualExpression'  : lambda expr: expr.opL.attribute.width * 2.5,    # Complex magnitude comparator
    
    # Control/Mux Expression types
    'WhenExpression'    : lambda expr: len(expr._condition_list) * expr.attribute.width,  # k conditions × n bits, each 1-bit MUX area = 1
    'CaseExpression'    : lambda expr: len(expr._CaseExpression__case_pair) * expr.attribute.width,  # k cases × n bits, each 1-bit MUX area = 1
    
    # Constant expressions (have no area cost)
    'Constant'          : lambda obj: 0.0,
    'Bits'              : lambda obj: 0.0,
    'UInt'              : lambda obj: 0.0,
    'SInt'              : lambda obj: 0.0,
    'AnyConstant'       : lambda obj: 0.0,
}


def get_area_for_object(obj):
    """
    Get the normalized area for Expression and Reg objects only.
    
    This function looks up the appropriate area calculation function
    based on the object's class name and applies it. Only works for
    Expression and Reg types that are registered in AREA_CALCULATORS.
    
    Args:
        obj: Expression or Reg object
        
    Returns:
        float: The normalized area of the object
        
    Raises:
        ValueError: If the object type is not supported by this calculator
    """
    class_name = type(obj).__name__
    
    # Try to find exact class name match first
    if class_name in AREA_CALCULATORS:
        calculator_func = AREA_CALCULATORS[class_name]
        return calculator_func(obj)
    
    # If no exact match, try to find a parent class match
    for cls in type(obj).__mro__:  # Method Resolution Order
        parent_class_name = cls.__name__
        if parent_class_name in AREA_CALCULATORS:
            calculator_func = AREA_CALCULATORS[parent_class_name]
            return calculator_func(obj)
    
    # If no calculator found for Expression/Reg types, raise error
    raise ValueError(f"No area calculator found for object type: {class_name}")