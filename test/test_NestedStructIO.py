import unittest
from uhdl import *
from uhdl.core.Variable import (StructType, StructConstant, StructFieldRef,
                                 InputStructIO, OutputStructIO, SInt, UInt, IOSig)


class TestNestedStructIO(unittest.TestCase):

    def test_nested_struct_ports_auto(self):
        """Auto mode should create InputStructIO/OutputStructIO for nested struct ports."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        self.assertTrue(hasattr(vc, 'line_in'))
        self.assertTrue(hasattr(vc, 'line_out'))
        self.assertEqual(type(vc.line_in).__name__, 'InputStructIO')
        self.assertEqual(type(vc.line_out).__name__, 'OutputStructIO')

    def test_nested_struct_width(self):
        """Nested struct should have correct total width."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        # point_t = 4+4 = 8, line_t = 8+8+8 = 24
        self.assertEqual(vc.line_in.attribute.width, 24)
        self.assertEqual(vc.line_out.attribute.width, 24)

    def test_nested_struct_top_level_fields(self):
        """Nested struct should have correct top-level fields."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        self.assertEqual(vc.line_in._field_order, ['start_pt', 'end_pt', 'color'])

    def test_nested_struct_field_access(self):
        """Dot access on nested struct fields should work."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        ref_start = vc.line_in.start_pt
        self.assertIsInstance(ref_start, StructFieldRef)
        self.assertEqual(ref_start.attribute.width, 8)  # point_t is 8 bits

    def test_nested_struct_subfield_access(self):
        """Dot access on sub-fields of nested struct should work: line_in.start_pt.x."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        ref_x = vc.line_in.start_pt.x
        self.assertIsInstance(ref_x, StructFieldRef)
        self.assertEqual(ref_x.attribute.width, 4)

    def test_nested_struct_subfield_y(self):
        """Access sub-field y: line_in.start_pt.y."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        ref_y = vc.line_in.start_pt.y
        self.assertIsInstance(ref_y, StructFieldRef)
        self.assertEqual(ref_y.attribute.width, 4)

    def test_nested_struct_end_pt_subfields(self):
        """Access sub-fields on end_pt: line_in.end_pt.x/y."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        ref_ex = vc.line_in.end_pt.x
        self.assertEqual(ref_ex.attribute.width, 4)
        ref_ey = vc.line_in.end_pt.y
        self.assertEqual(ref_ey.attribute.width, 4)

    def test_nested_struct_nonexistent_subfield(self):
        """Accessing nonexistent sub-field should raise error."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        with self.assertRaises(AttributeError):
            _ = vc.line_in.start_pt.z

    def test_nested_struct_plain_field(self):
        """Non-nested field should work normally."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        ref_color = vc.line_in.color
        self.assertIsInstance(ref_color, StructFieldRef)
        self.assertEqual(ref_color.attribute.width, 8)

    def test_nested_struct_type_has_struct_type_info(self):
        """StructType fields for nested structs should have struct_type populated."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        st = vc.line_in.struct_type
        self.assertIsNotNone(st)
        start_info = st.fields['start_pt']
        self.assertIn('struct_type', start_info)
        self.assertIsNotNone(start_info['struct_type'])
        # The nested struct_type should have x and y fields
        nested_st = start_info['struct_type']
        self.assertIn('x', nested_st.fields)
        self.assertIn('y', nested_st.fields)

    def test_nested_struct_type_identity(self):
        """Both ports with same typedef should share the same StructType instance."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        self.assertIs(vc.line_in.struct_type, vc.line_out.struct_type)

    def test_nested_struct_nested_type_identity(self):
        """Nested struct types (point_t) should share identity between start_pt and end_pt."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        st = vc.line_in.struct_type
        start_nested = st.fields['start_pt']['struct_type']
        end_nested = st.fields['end_pt']['struct_type']
        self.assertIs(start_nested, end_nested)

    def test_nested_struct_verilog_def(self):
        """Verilog port definitions should use struct type name."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        vdef = vc.line_in.verilog_def
        self.assertTrue(any('nested_pkg::line_t' in d for d in vdef))

    def test_nested_struct_lstring(self):
        """Nested field refs should have correct lstring for verilog generation."""
        vc = VComponent(file='test/verilog/nested_struct_ports.v', top='nested_struct_user', struct_mode='auto')
        ref_x = vc.line_in.start_pt.x
        # lstring should be something like "line_in.start_pt.x"
        self.assertIn('start_pt', ref_x.lstring)
        self.assertIn('x', ref_x.lstring)


if __name__ == '__main__':
    unittest.main()
