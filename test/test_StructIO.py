import unittest
from uhdl import *
from uhdl.core.Variable import (StructType, StructConstant, StructFieldRef,
                                 InputStructIO, OutputStructIO, SInt, UInt, IOSig)

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
        self.assertIsInstance(vc.s_in._fields['b'].attribute, SInt)
        self.assertIsInstance(vc.s_out._fields['b'].attribute, SInt)
        self.assertIsInstance(vc.s_in._fields['a'].attribute, UInt)
        self.assertIsInstance(vc.s_out._fields['a'].attribute, UInt)
        # Check both are IOSig subclasses
        self.assertIsInstance(vc.s_in, IOSig)
        self.assertIsInstance(vc.s_out, IOSig)

    def test_struct_ports_packed_vector(self):
        # packed mode should return vectors (no InputStructIO/OutputStructIO)
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='packed')
        self.assertIsInstance(vc.s_in, Input)
        self.assertIsInstance(vc.s_out, Output)
        self.assertEqual(vc.s_in.attribute.width, 13)  # 4+8+1
        self.assertEqual(vc.s_out.attribute.width, 13)

    def test_struct_field_dot_access(self):
        """Dot access on struct IO should return StructFieldRef."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        ref_a = vc.s_in.a
        self.assertIsInstance(ref_a, StructFieldRef)
        self.assertEqual(ref_a.attribute.width, 4)
        self.assertIsInstance(ref_a.attribute, UInt)
        ref_b = vc.s_in.b
        self.assertEqual(ref_b.attribute.width, 8)
        self.assertIsInstance(ref_b.attribute, SInt)

    def test_struct_field_nonexistent_raises(self):
        """Accessing nonexistent field should raise error."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        with self.assertRaises(Exception):
            _ = vc.s_in.nonexistent_field

    def test_struct_type_name(self):
        """StructIO should carry the correct struct type name."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        self.assertIn('my_struct_t', vc.s_in._struct_name)
        self.assertIn('my_struct_t', vc.s_out._struct_name)

    def test_struct_type_object(self):
        """StructIO should carry a StructType object."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        st = vc.s_in.struct_type
        self.assertIsNotNone(st)
        self.assertIsInstance(st, StructType)
        self.assertEqual(st.width, 13)
        self.assertIn('a', st.fields)
        self.assertIn('b', st.fields)
        self.assertIn('c', st.fields)

    def test_struct_type_identity(self):
        """Both ports with same typedef should share the same StructType instance."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        self.assertIs(vc.s_in.struct_type, vc.s_out.struct_type)

    def test_struct_verilog_def(self):
        """Verilog port definitions should use struct type name."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        vdef = vc.s_in.verilog_def
        self.assertTrue(any('mypkg::my_struct_t' in d for d in vdef))

    def test_struct_reverse(self):
        """Reversing an InputStructIO should give OutputStructIO and vice versa."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        rev = vc.s_in.reverse()
        self.assertIsInstance(rev, OutputStructIO)
        self.assertEqual(rev._field_order, ['a', 'b', 'c'])
        self.assertIs(rev.struct_type, vc.s_in.struct_type)

    def test_struct_template(self):
        """Template should create same-type copy with fields."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        tmpl = vc.s_in.template()
        self.assertIsInstance(tmpl, InputStructIO)
        self.assertEqual(tmpl._field_order, ['a', 'b', 'c'])
        self.assertIs(tmpl.struct_type, vc.s_in.struct_type)

    def test_struct_in_input_list(self):
        """Struct input ports should appear in component input_list."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        names = [p.name for p in vc.input_list]
        self.assertIn('s_in', names)

    def test_struct_in_output_list(self):
        """Struct output ports should appear in component output_list."""
        vc = VComponent(file='test/verilog/struct_ports.v', top='struct_user', struct_mode='auto')
        names = [p.name for p in vc.output_list]
        self.assertIn('s_out', names)


if __name__ == '__main__':
    unittest.main()
