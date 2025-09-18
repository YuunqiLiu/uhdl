#!/usr/bin/env python3

import unittest
import sys
import os

# Add the parent directory to the path to import uhdl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from uhdl import *


class SimpleComponent(Component):
    """Simple test component with basic registers and expressions."""
    
    def __init__(self):
        super().__init__()
        self.a = Input(UInt(8))
        self.b = Input(UInt(8))
        self.out = Output(UInt(8))
        self.clk = Input(UInt(1))
        self.rst = Input(UInt(1))
        
        # Internal wire and registers
        self.temp_wire = Wire(UInt(9))  # Need 9 bits for addition result
        self.temp_reg = Reg(UInt(8), self.clk, self.rst)
        self.counter = Reg(UInt(4), self.clk, self.rst)
        
        # Simple logic
        self.temp_wire += self.a + self.b
        self.temp_reg += self.temp_wire[7:0]  # Take lower 8 bits
        self.counter += (self.counter + UInt(4, 1))[3:0]  # Keep only 4 bits
        self.out += self.temp_reg


class ComplexComponent(Component):
    """Complex test component with sub-components and complex expressions."""
    
    def __init__(self):
        super().__init__()
        self.in1 = Input(UInt(16))
        self.in2 = Input(UInt(16))
        self.out1 = Output(UInt(16))
        self.out2 = Output(UInt(16))
        
        # Sub-components
        self.sub1 = SimpleComponent()
        self.sub2 = SimpleComponent()
        
        # Internal signals and more complex logic
        self.internal_wire = Wire(UInt(16))
        self.result_reg = Reg(UInt(16), self.sub1.clk, self.sub1.rst)
        self.expanded_out = Wire(UInt(16))
        
        # More complex expressions
        self.internal_wire += (self.in1 * self.in2)[15:0]  # Take lower 16 bits
        self.result_reg += (self.internal_wire & UInt(16, 0xFFFF)) | (self.in1 << UInt(4, 2))[15:0]
        self.out1 += self.result_reg
        # Connect with proper width expansion
        self.expanded_out += Combine(self.sub1.out, UInt(8, 0))  # Expand 8-bit to 16-bit
        self.out2 += self.expanded_out


class SharedExpressionComponent(Component):
    """Test component for shared expression analysis."""
    
    def __init__(self):
        super().__init__()
        
        self.a = Input(UInt(8))
        self.b = Input(UInt(8))
        
        self.out1 = Output(UInt(9))
        self.out2 = Output(UInt(9))
        self.out3 = Output(UInt(9))
        
        # Case 1: 共享同一个表达式对象
        shared_expr = self.a + self.b
        self.out1 += shared_expr
        self.out2 += shared_expr
        
        # Case 2: 创建相同但不同的表达式对象
        self.out3 += self.a + self.b  # 这是一个新的表达式对象


class TestAreaCalculation(unittest.TestCase):
    """Test cases for area calculation functionality."""
    
    def setUp(self):
        """Set up test components."""
        self.simple_comp = SimpleComponent()
        self.complex_comp = ComplexComponent()
        self.shared_expr_comp = SharedExpressionComponent()
        
        # Update instance trees
        self.simple_comp.update_instance_tree()
        self.complex_comp.update_instance_tree()
        self.shared_expr_comp.update_instance_tree()
    
    def test_simple_component_area(self):
        """Test area calculation for simple component."""
        area = self.simple_comp.get_area()
        self.assertGreater(area, 0, "Simple component should have non-zero area")
        
        # Verify that area calculation includes all instances
        self.assertGreater(len(self.simple_comp._sub_instance_list), 0, 
                          "Simple component should have sub-instances")
    
    def test_complex_component_area(self):
        """Test area calculation for complex component with sub-components."""
        area = self.complex_comp.get_area()
        simple_area = self.simple_comp.get_area()
        
        self.assertGreater(area, simple_area, 
                          "Complex component should have larger area than simple component")
        
        # Verify that complex component includes sub-component areas
        self.assertGreater(len(self.complex_comp._sub_instance_list), 
                          len(self.simple_comp._sub_instance_list),
                          "Complex component should have more instances")
    
    def test_area_report_format(self):
        """Test area report string formatting."""
        report = self.simple_comp.report_area()
        
        self.assertIsInstance(report, str, "report_area should return a string")
        self.assertIn("Instance Name", report, "Report should contain header")
        self.assertIn("Module Name", report, "Report should contain module name column")
        self.assertIn("Area", report, "Report should contain area column")
        self.assertIn("|", report, "Report should be table formatted")
    
    def test_complex_area_report(self):
        """Test area report for complex component."""
        report = self.complex_comp.report_area()
        
        self.assertIsInstance(report, str, "Complex report should return a string")
        self.assertGreater(len(report.split('\n')), 5, 
                          "Complex report should have multiple lines")
    
    def test_shared_expression_area(self):
        """Test area calculation with shared expressions."""
        area = self.shared_expr_comp.get_area()
        self.assertGreater(area, 0, "Shared expression component should have non-zero area")
        
        # Check that expressions exist in instance list
        expr_count = sum(1 for instance in self.shared_expr_comp._sub_instance_list 
                        if 'Expression' in type(instance).__name__)
        self.assertGreater(expr_count, 0, "Should have expression instances")
    
    def test_expression_types_area(self):
        """Test that different expression types have appropriate areas."""
        # Create test expressions with known widths
        from uhdl.core.AreaCalculator import get_area_for_object
        
        # Create mock expressions for testing
        class MockAddExpression:
            def __init__(self, width):
                self.attribute = type('', (), {'width': width})()
        
        class MockMulExpression:
            def __init__(self, width):
                self.attribute = type('', (), {'width': width})()
        
        MockAddExpression.__name__ = 'AddExpression'
        MockMulExpression.__name__ = 'MulExpression'
        
        add_expr = MockAddExpression(8)
        mul_expr = MockMulExpression(8)
        
        add_area = get_area_for_object(add_expr)
        mul_area = get_area_for_object(mul_expr)
        
        # Multipliers should be more expensive than adders
        self.assertGreater(mul_area, add_area, 
                          "Multiplier should have larger area than adder")
        
        # Check expected values
        self.assertEqual(add_area, 8 * 0.05, "AddExpression area should be width * 0.05")
        self.assertEqual(mul_area, 8 * 0.2, "MulExpression area should be width * 0.2")
    
    def test_reg_area_calculation(self):
        """Test that register area calculation is correct."""
        from uhdl.core.AreaCalculator import get_area_for_object
        
        # Create a mock Reg for testing
        class MockReg:
            def __init__(self, width):
                self.attribute = type('', (), {'width': width})()
        
        MockReg.__name__ = 'Reg'
        
        reg8 = MockReg(8)
        reg32 = MockReg(32)
        
        area8 = get_area_for_object(reg8)
        area32 = get_area_for_object(reg32)
        
        # Area should be proportional to width
        self.assertEqual(area8, 8 * 0.1, "8-bit reg area should be 0.8")
        self.assertEqual(area32, 32 * 0.1, "32-bit reg area should be 3.2")
        self.assertEqual(area32 / area8, 4, "32-bit reg should be 4x larger than 8-bit")


class TestAreaReportOutput(unittest.TestCase):
    """Test cases specifically for area report output functionality."""
    
    def setUp(self):
        """Set up test components."""
        self.simple_comp = SimpleComponent()
        self.simple_comp.update_instance_tree()
    
    def test_report_returns_string(self):
        """Test that report_area returns a properly formatted string."""
        report = self.simple_comp.report_area()
        
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)
    
    def test_report_contains_table_structure(self):
        """Test that the report has proper table structure."""
        report = self.simple_comp.report_area()
        lines = report.split('\n')
        
        # Should have at least header, separator, and data rows
        self.assertGreater(len(lines), 2)
        
        # First line should be header
        self.assertIn('Instance Name', lines[0])
        self.assertIn('Module Name', lines[0])
        self.assertIn('Area', lines[0])
        
        # Second line should be separator (dashes)
        self.assertTrue(all(c in '- |' for c in lines[1]))
    
    def test_empty_component_report(self):
        """Test area report for component with no instances."""
        empty_comp = Component()
        empty_comp.update_instance_tree()
        
        report = empty_comp.report_area()
        # Empty component should still generate a table with the component itself
        self.assertIn("Component", report)
        self.assertIn("0.000", report)  # Should show zero area


if __name__ == '__main__':
    # Create a test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestAreaCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestAreaReportOutput))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)