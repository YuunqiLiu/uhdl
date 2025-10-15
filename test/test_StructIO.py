import unittest
from uhdl import *

class TestStructIO(unittest.TestCase):
    def test_struct_ports_group_auto(self):
        # auto mode should create StructIOGroup if typedef struct is detected
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        # Expect grouped ports for s_in and s_out
        self.assertTrue(hasattr(vc, 's_in'))
        self.assertTrue(hasattr(vc, 's_out'))
        # s_in and s_out should be StructIOGroup
        self.assertEqual(type(vc.s_in).__name__, 'StructIOGroup')
        self.assertEqual(type(vc.s_out).__name__, 'StructIOGroup')
        # Field order and widths
        names = [x.name for x in vc.s_in.io_list]
        widths = [x.attribute.width for x in vc.s_in.io_list]
        self.assertEqual(names, ['a','b','c'])
        self.assertEqual(widths, [4,8,1])
        # Signedness for b
        from uhdl.core.Variable import SInt, UInt
        self.assertIsInstance(vc.s_in.b.attribute, SInt)
        self.assertIsInstance(vc.s_out.b.attribute, SInt)
        self.assertIsInstance(vc.s_in.a.attribute, UInt)
        self.assertIsInstance(vc.s_out.a.attribute, UInt)

    def test_struct_ports_packed_vector(self):
        # packed mode should return vectors (no StructIOGroup)
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='packed')
        self.assertIsInstance(vc.s_in, Input)
        self.assertIsInstance(vc.s_out, Output)
        self.assertEqual(vc.s_in.attribute.width, 13)  # 4+8+1
        self.assertEqual(vc.s_out.attribute.width, 13)

if __name__ == '__main__':
    unittest.main()
