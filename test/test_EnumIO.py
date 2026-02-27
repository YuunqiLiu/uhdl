import unittest
from uhdl import *
from uhdl.core.Variable import (EnumType, EnumConstant,
                                 InputEnumIO, OutputEnumIO, SInt, UInt, IOSig)


class TestEnumIO(unittest.TestCase):

    def test_enum_ports_auto(self):
        """Auto mode should create InputEnumIO/OutputEnumIO for typedef enum ports."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        self.assertTrue(hasattr(vc, 'state_in'))
        self.assertTrue(hasattr(vc, 'state_out'))
        self.assertEqual(type(vc.state_in).__name__, 'InputEnumIO')
        self.assertEqual(type(vc.state_out).__name__, 'OutputEnumIO')

    def test_enum_ports_packed_vector(self):
        """Packed mode should return plain vectors (no EnumIO)."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='packed')
        self.assertIsInstance(vc.state_in, Input)
        self.assertIsInstance(vc.state_out, Output)
        self.assertEqual(vc.state_in.attribute.width, 2)
        self.assertEqual(vc.state_out.attribute.width, 2)

    def test_enum_width(self):
        """EnumIO should have correct bit width."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        self.assertEqual(vc.state_in.attribute.width, 2)
        self.assertEqual(vc.state_out.attribute.width, 2)
        self.assertEqual(vc.op_in.attribute.width, 3)
        self.assertEqual(vc.op_out.attribute.width, 3)

    def test_enum_type_name(self):
        """EnumIO should carry the correct enum type name."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        self.assertIn('state_t', vc.state_in._enum_name)
        self.assertIn('state_t', vc.state_out._enum_name)

    def test_enum_type_object(self):
        """EnumIO should carry an EnumType object with members."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        et = vc.state_in.enum_type
        self.assertIsNotNone(et)
        self.assertIsInstance(et, EnumType)
        self.assertEqual(et.width, 2)
        self.assertIn('IDLE', et.members)
        self.assertIn('RUN', et.members)
        self.assertIn('DONE', et.members)
        self.assertIn('ERR', et.members)

    def test_enum_member_values(self):
        """Enum members should have correct integer values."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        et = vc.state_in.enum_type
        self.assertEqual(et.members['IDLE'], 0)
        self.assertEqual(et.members['RUN'], 1)
        self.assertEqual(et.members['DONE'], 2)
        self.assertEqual(et.members['ERR'], 3)

    def test_enum_member_access_via_type(self):
        """EnumType member access via attribute: enum_type.MEMBER."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        et = vc.state_in.enum_type
        self.assertEqual(et.IDLE, 0)
        self.assertEqual(et.RUN, 1)
        self.assertEqual(et.DONE, 2)
        self.assertEqual(et.ERR, 3)

    def test_enum_type_identity(self):
        """Both ports with same typedef should share the same EnumType instance."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        self.assertIs(vc.state_in.enum_type, vc.state_out.enum_type)

    def test_enum_type_different(self):
        """Different enum typedefs should NOT share EnumType."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        self.assertIsNot(vc.state_in.enum_type, vc.op_in.enum_type)

    def test_enum_verilog_def(self):
        """Verilog port definitions should use enum type name."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        vdef = vc.state_in.verilog_def
        self.assertTrue(any('enum_pkg::state_t' in d for d in vdef))

    def test_enum_reverse(self):
        """Reversing an InputEnumIO should give OutputEnumIO and vice versa."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        rev = vc.state_in.reverse()
        self.assertIsInstance(rev, OutputEnumIO)
        self.assertIs(rev.enum_type, vc.state_in.enum_type)

    def test_enum_template(self):
        """Template should create same-type copy."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        tmpl = vc.state_in.template()
        self.assertIsInstance(tmpl, InputEnumIO)
        self.assertIs(tmpl.enum_type, vc.state_in.enum_type)

    def test_enum_in_input_list(self):
        """Enum input ports should appear in component input_list."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        names = [p.name for p in vc.input_list]
        self.assertIn('state_in', names)
        self.assertIn('op_in', names)

    def test_enum_in_output_list(self):
        """Enum output ports should appear in component output_list."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        names = [p.name for p in vc.output_list]
        self.assertIn('state_out', names)
        self.assertIn('op_out', names)

    def test_enum_isinstance_iosig(self):
        """EnumIO should be an IOSig subclass."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        self.assertIsInstance(vc.state_in, IOSig)
        self.assertIsInstance(vc.state_out, IOSig)

    def test_opcode_enum_members(self):
        """Opcode enum should have correct members and values."""
        vc = VComponent(file='test/verilog/enum_ports.v', top='enum_user', struct_mode='auto')
        et = vc.op_in.enum_type
        self.assertEqual(len(et.members), 5)
        self.assertEqual(et.ADD, 0)
        self.assertEqual(et.SUB, 1)
        self.assertEqual(et.MUL, 2)
        self.assertEqual(et.DIV, 3)
        self.assertEqual(et.NOP, 4)


if __name__ == '__main__':
    unittest.main()
