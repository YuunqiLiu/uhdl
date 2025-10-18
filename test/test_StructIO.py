import unittest
from uhdl import *

class TestStructIO(unittest.TestCase):
    def test_struct_ports_group_auto(self):
        # auto mode should create InputStructIO/OutputStructIO if typedef struct is detected
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        # Expect InputStructIO/OutputStructIO ports for s_in and s_out
        self.assertTrue(hasattr(vc, 's_in'))
        self.assertTrue(hasattr(vc, 's_out'))
        # s_in should be InputStructIO, s_out should be OutputStructIO
        self.assertEqual(type(vc.s_in).__name__, 'InputStructIO')
        self.assertEqual(type(vc.s_out).__name__, 'OutputStructIO')
        # Check that StructIO has fields
        self.assertEqual(len(vc.s_in._field_order), 3)
        self.assertEqual(vc.s_in._field_order, ['a','b','c'])
        # Check field widths
        self.assertEqual(vc.s_in._fields['a'].attribute.width, 4)
        self.assertEqual(vc.s_in._fields['b'].attribute.width, 8)
        self.assertEqual(vc.s_in._fields['c'].attribute.width, 1)
        # Signedness for b
        from uhdl.core.Variable import SInt, UInt
        self.assertIsInstance(vc.s_in._fields['b'].attribute, SInt)
        self.assertIsInstance(vc.s_out._fields['b'].attribute, SInt)
        self.assertIsInstance(vc.s_in._fields['a'].attribute, UInt)
        self.assertIsInstance(vc.s_out._fields['a'].attribute, UInt)
        # Check both are IOSig subclasses
        from uhdl.core.Variable import IOSig
        self.assertIsInstance(vc.s_in, IOSig)
        self.assertIsInstance(vc.s_out, IOSig)

    def test_struct_ports_packed_vector(self):
        # packed mode should return vectors (no InputStructIO/OutputStructIO)
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='packed')
        self.assertIsInstance(vc.s_in, Input)
        self.assertIsInstance(vc.s_out, Output)
        self.assertEqual(vc.s_in.attribute.width, 13)  # 4+8+1
        self.assertEqual(vc.s_out.attribute.width, 13)

if __name__ == '__main__':
    unittest.main()
