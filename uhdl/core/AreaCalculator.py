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
    'AddExpression'     : lambda expr: expr.attribute.width * 0.05,  # Adders
    'SubExpression'     : lambda expr: expr.attribute.width * 0.05,  # Subtractors
    'MulExpression'     : lambda expr: expr.attribute.width * 0.2,   # Multipliers are expensive
    
    # Bitwise Expression types
    'BitAndExpression'  : lambda expr: expr.attribute.width * 0.02,
    'BitOrExpression'   : lambda expr: expr.attribute.width * 0.02,
    'BitXorExpression'  : lambda expr: expr.attribute.width * 0.02,
    'InverseExpression' : lambda expr: expr.attribute.width * 0.01,
    
    # Shift Expression types
    'LeftShift'         : lambda expr: expr.attribute.width * 0.02,
    'RightShift'        : lambda expr: expr.attribute.width * 0.02,
    
    # Wire/routing Expression types
    'CutExpression'     : lambda expr: 0.0,  # Cut expressions are just wire routing, no area cost
    'CombineExpression' : lambda expr: expr.attribute.width * 0.01,  # Wire routing, minimal cost
    
    # Comparison Expression types
    'EqualExpression'   : lambda expr: expr.attribute.width * 0.03,    # Comparators
    'GreaterExpression' : lambda expr: expr.attribute.width * 0.03,  # Comparators
    'LessExpression'    : lambda expr: expr.attribute.width * 0.03,     # Comparators
    
    # Control/Mux Expression types
    'WhenExpression'    : lambda expr: expr.attribute.width * 0.04,  # Multiplexers
    'CaseExpression'    : lambda expr: expr.attribute.width * 0.04,  # Multiplexers
    
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