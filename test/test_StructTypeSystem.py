"""Tests for StructType kernel: identity, equality, registry, and StructConstant."""
import unittest
from collections import OrderedDict
from uhdl.core.Variable import StructType, StructConstant, UInt, SInt


class TestStructType(unittest.TestCase):

    def setUp(self):
        StructType.clear_registry()

    def test_basic_creation(self):
        fields = OrderedDict([
            ('a', {'width': 4, 'signed': False}),
            ('b', {'width': 8, 'signed': True}),
        ])
        st = StructType('pkg::my_t', fields, package='pkg')
        self.assertEqual(st.name, 'pkg::my_t')
        self.assertEqual(st.package, 'pkg')
        self.assertEqual(st.width, 12)
        self.assertIn('a', st.fields)
        self.assertIn('b', st.fields)

    def test_width_computation(self):
        fields = OrderedDict([
            ('x', {'width': 1, 'signed': False}),
            ('y', {'width': 16, 'signed': False}),
            ('z', {'width': 3, 'signed': True}),
        ])
        st = StructType('test_t', fields)
        self.assertEqual(st.width, 20)

    def test_registry_singleton(self):
        """get_or_create returns the same object for same name."""
        f1 = OrderedDict([('a', {'width': 4, 'signed': False})])
        st1 = StructType.get_or_create('pkg::t1', f1, package='pkg')
        f2 = OrderedDict([('a', {'width': 8, 'signed': False})])  # different fields
        st2 = StructType.get_or_create('pkg::t1', f2, package='pkg')
        self.assertIs(st1, st2)  # same name -> same instance

    def test_equality_named(self):
        """Two StructTypes with the same canonical name are equal."""
        f = OrderedDict([('a', {'width': 4, 'signed': False})])
        st1 = StructType('pkg::t', f)
        st2 = StructType('pkg::t', f)
        self.assertEqual(st1, st2)

    def test_inequality_different_names(self):
        """Different typedef names -> not equal even with same schema."""
        f = OrderedDict([('a', {'width': 4, 'signed': False})])
        st1 = StructType('pkg::t1', f)
        st2 = StructType('pkg::t2', OrderedDict(f))
        self.assertNotEqual(st1, st2)

    def test_anonymous_schema_equal(self):
        """Anonymous structs with same schema are equal."""
        f1 = OrderedDict([('a', {'width': 4, 'signed': False}), ('b', {'width': 8, 'signed': True})])
        f2 = OrderedDict([('a', {'width': 4, 'signed': False}), ('b', {'width': 8, 'signed': True})])
        st1 = StructType(None, f1)
        st2 = StructType(None, f2)
        self.assertEqual(st1, st2)

    def test_anonymous_schema_not_equal(self):
        """Anonymous structs with different schemas are not equal."""
        f1 = OrderedDict([('a', {'width': 4, 'signed': False})])
        f2 = OrderedDict([('a', {'width': 8, 'signed': False})])
        st1 = StructType(None, f1)
        st2 = StructType(None, f2)
        self.assertNotEqual(st1, st2)

    def test_named_vs_anonymous_not_equal(self):
        """Named struct != anonymous struct even with same schema."""
        f = OrderedDict([('a', {'width': 4, 'signed': False})])
        st1 = StructType('pkg::t', f)
        st2 = StructType(None, OrderedDict(f))
        self.assertNotEqual(st1, st2)

    def test_package_auto_detection(self):
        """Package is auto-detected from name if not given explicitly."""
        f = OrderedDict([('a', {'width': 1, 'signed': False})])
        st = StructType('mypkg::my_struct_t', f)
        self.assertEqual(st.package, 'mypkg')

    def test_clear_registry(self):
        f = OrderedDict([('a', {'width': 1, 'signed': False})])
        StructType.get_or_create('test_clear', f)
        self.assertIn('test_clear', StructType._registry)
        StructType.clear_registry()
        self.assertNotIn('test_clear', StructType._registry)

    def test_field_offsets(self):
        """Fields should have correct bit-offsets (packed, MSB-first)."""
        fields = OrderedDict([
            ('a', {'width': 4, 'signed': False}),
            ('b', {'width': 8, 'signed': True}),
            ('c', {'width': 1, 'signed': False}),
        ])
        st = StructType('test_off', fields)
        # Packed MSB-first: c at offset 0, b at offset 1, a at offset 9
        self.assertEqual(st.fields['c']['offset'], 0)
        self.assertEqual(st.fields['b']['offset'], 1)
        self.assertEqual(st.fields['a']['offset'], 9)


class TestStructConstant(unittest.TestCase):

    def setUp(self):
        StructType.clear_registry()

    def test_basic(self):
        f = OrderedDict([('a', {'width': 4, 'signed': False})])
        st = StructType('pkg::t', f)
        sc = StructConstant(st)
        self.assertEqual(sc.width, 4)
        self.assertIs(sc.struct_type, st)

    def test_equality_same_type(self):
        f = OrderedDict([('a', {'width': 4, 'signed': False})])
        st = StructType('pkg::t', f)
        sc1 = StructConstant(st)
        sc2 = StructConstant(st)
        self.assertEqual(sc1, sc2)

    def test_inequality_different_struct_type(self):
        f = OrderedDict([('a', {'width': 4, 'signed': False})])
        st1 = StructType('pkg::t1', f)
        st2 = StructType('pkg::t2', OrderedDict(f))
        sc1 = StructConstant(st1)
        sc2 = StructConstant(st2)
        self.assertNotEqual(sc1, sc2)

    def test_inequality_vs_plain_bits(self):
        """StructConstant != UInt/SInt even if same width (strict type safety)."""
        f = OrderedDict([('a', {'width': 8, 'signed': False})])
        st = StructType('pkg::t', f)
        sc = StructConstant(st)
        plain = UInt(8)
        self.assertNotEqual(sc, plain)


if __name__ == '__main__':
    unittest.main()
