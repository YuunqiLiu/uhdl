import os,sys
import unittest

# # pylint: disable =unused-wildcard-import
# from ..core import *
# # pylint: enable  =unused-wildcard-import

# class TestWire(unittest.TestCase):

#     def test_define(self):
#         p = Port()
#         p.new(clk=Wire(INPUT,1))
#         p.new(rst=Wire(INPUT,1))
#         self.assertIsInstance(p.clk,Wire)
#         self.assertIsInstance(p.rst,Wire)
#         for item in p.sub_port():
#             self.assertIsInstance(item,Wire)

#     def test_equal(self):
#         p1 = Port()
#         p2 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p2.new(clk=Wire(INPUT,1))
#         self.assertEqual(p1.clk,p2.clk)

#     def test_not_equal_by_name(self):
#         p1 = Port()
#         p2 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p2.new(rst=Wire(INPUT,1))
#         self.assertNotEqual(p1.clk,p2.rst)
    
#     def test_not_equal_by_direction(self):
#         p1 = Port()
#         p2 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p2.new(clk=Wire(OUTPUT,1))
#         self.assertNotEqual(p1.clk,p2.clk)

#     def test_not_equal_by_width(self):
#         p1 = Port()
#         p2 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p2.new(clk=Wire(INPUT,2))
#         self.assertNotEquals(p1.clk,p2.clk)

#     def test_reverse(self):
#         p1 = Port()
#         p2 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p2.new(clk=Wire(OUTPUT,1))
#         self.assertEqual(p1.clk.reverse(),p2.clk)
#         self.assertEqual(p2.clk.reverse(),p1.clk)

#     def test_match(self):
#         p1 = Port()
#         p2 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p2.new(clk=Wire(OUTPUT,1))
#         self.assertTrue(p1.clk.is_match(p2.clk))

#     def test_one_direction(self):
#         pass

    
#     def test_expand(self):
#         p1 = Port()
#         p2 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p2.new(clk=Wire(OUTPUT,1))
#         exp = p1.clk.expand()
#         self.assertIsInstance(exp,list)
#         self.assertEqual(len(exp),1)
#         self.assertIsInstance(exp[0],Wire)

# #if __name__ == '__main__':
# #    unittest.main()