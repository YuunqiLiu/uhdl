import unittest
from uhdl import *
from uhdl.core.Variable import (UnionType, UnionConstant, UnionFieldRef,
                                 InputUnionIO, OutputUnionIO, SInt, UInt, IOSig)


class TestUnionIO(unittest.TestCase):

    def test_union_ports_auto(self):
        """Auto mode should create InputUnionIO/OutputUnionIO for typedef union ports."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        self.assertTrue(hasattr(vc, 'u_in'))
        self.assertTrue(hasattr(vc, 'u_out'))
        self.assertEqual(type(vc.u_in).__name__, 'InputUnionIO')
        self.assertEqual(type(vc.u_out).__name__, 'OutputUnionIO')

    def test_union_ports_packed_vector(self):
        """Packed mode should return plain vectors (no UnionIO)."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='packed')
        self.assertIsInstance(vc.u_in, Input)
        self.assertIsInstance(vc.u_out, Output)
        self.assertEqual(vc.u_in.attribute.width, 8)
        self.assertEqual(vc.u_out.attribute.width, 8)

    def test_union_width(self):
        """UnionIO should have correct bit width (max of all fields)."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        self.assertEqual(vc.u_in.attribute.width, 8)
        self.assertEqual(vc.u_out.attribute.width, 8)

    def test_union_type_name(self):
        """UnionIO should carry the correct union type name."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        self.assertIn('my_union_t', vc.u_in._union_name)
        self.assertIn('my_union_t', vc.u_out._union_name)

    def test_union_type_object(self):
        """UnionIO should carry a UnionType object with fields."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        ut = vc.u_in.union_type
        self.assertIsNotNone(ut)
        self.assertIsInstance(ut, UnionType)
        self.assertEqual(ut.width, 8)
        self.assertIn('byte_val', ut.fields)
        self.assertIn('as_point', ut.fields)

    def test_union_field_dot_access(self):
        """Dot access on union IO should return UnionFieldRef."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        ref_byte = vc.u_in.byte_val
        self.assertIsInstance(ref_byte, UnionFieldRef)
        self.assertEqual(ref_byte.attribute.width, 8)
        ref_point = vc.u_in.as_point
        self.assertIsInstance(ref_point, UnionFieldRef)
        self.assertEqual(ref_point.attribute.width, 8)

    def test_union_field_nonexistent_raises(self):
        """Accessing nonexistent field should raise error."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        with self.assertRaises(AttributeError):
            _ = vc.u_in.nonexistent_field

    def test_union_type_identity(self):
        """Both ports with same typedef should share the same UnionType instance."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        self.assertIs(vc.u_in.union_type, vc.u_out.union_type)

    def test_union_verilog_def(self):
        """Verilog port definitions should use union type name."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        vdef = vc.u_in.verilog_def
        self.assertTrue(any('union_pkg::my_union_t' in d for d in vdef))

    def test_union_reverse(self):
        """Reversing an InputUnionIO should give OutputUnionIO and vice versa."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        rev = vc.u_in.reverse()
        self.assertIsInstance(rev, OutputUnionIO)
        self.assertIs(rev.union_type, vc.u_in.union_type)

    def test_union_template(self):
        """Template should create same-type copy with fields."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        tmpl = vc.u_in.template()
        self.assertIsInstance(tmpl, InputUnionIO)
        self.assertIs(tmpl.union_type, vc.u_in.union_type)

    def test_union_in_input_list(self):
        """Union input ports should appear in component input_list."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        names = [p.name for p in vc.input_list]
        self.assertIn('u_in', names)

    def test_union_in_output_list(self):
        """Union output ports should appear in component output_list."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        names = [p.name for p in vc.output_list]
        self.assertIn('u_out', names)

    def test_union_isinstance_iosig(self):
        """UnionIO should be an IOSig subclass."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        self.assertIsInstance(vc.u_in, IOSig)
        self.assertIsInstance(vc.u_out, IOSig)

    def test_union_nested_struct_field(self):
        """Union field that is a struct should have struct_type info."""
        vc = VComponent(file='test/verilog/union_ports.v', top='union_user', struct_mode='auto')
        ut = vc.u_in.union_type
        as_point_info = ut.fields['as_point']
        self.assertIn('struct_type', as_point_info)
        self.assertIsNotNone(as_point_info['struct_type'])


if __name__ == '__main__':
    unittest.main()
