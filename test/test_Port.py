# import os,sys
# import unittest

# # pylint: disable =unused-wildcard-import
# from ..core import *
# # pylint: enable  =unused-wildcard-import

# class TestPort(unittest.TestCase):

#     def setup_port_contain_any(self):
#         p = Port()
#         w  = Wire(OUTPUT,32)
#         p1 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p1.new(rst=Wire(INPUT,1))
#         p2 = Port()
#         p2.new(do=Wire(OUTPUT,32))
#         p2.new(di=Wire(INPUT,32)) 
#         p.new(w=w)
#         p.new(p1=p1)
#         p.new(p2=p2)
#         return p

#     def test_define(self):
#         port = Port()
#         port.new(clk=Wire(INPUT,1))
#         port.new(rst=Wire(INPUT,1))
#         self.assertIsInstance(port,Port)

#     def test_equal_contain_wire(self):
#         p1 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p1.new(rst=Wire(INPUT,1))
#         p2 = Port()
#         p2.new(clk=Wire(INPUT,1))
#         p2.new(rst=Wire(INPUT,1))
#         self.assertEqual(p1,p2)

#     def test_not_equal_contain_wire(self):
#         p1 = Port()
#         p1.new(clk=Wire(INPUT,1))
#         p1.new(rst=Wire(INPUT,1))
#         p2 = Port()
#         p2.new(clk=Wire(OUTPUT,1))
#         p2.new(rst=Wire(INPUT,1))
#         self.assertNotEqual(p1,p2)        

#     def test_equal_contain_any(self):
#         p1 = self.setup_port_contain_any()
#         p2 = self.setup_port_contain_any()
#         self.assertEqual(p1,p2)

#     def test_not_equal_contain_any(self):
#         p1 = self.setup_port_contain_any()
#         p2 = self.setup_port_contain_any()
#         p3 = self.setup_port_contain_any()
#         p4 = self.setup_port_contain_any()
#         p1.new(w2=Wire(INPUT,3))
#         p2.new(w3=Wire(INPUT,3))
#         p3.new(w2=Wire(OUTPUT,3))
#         p4.new(w2=Wire(INPUT,2))
#         self.assertNotEqual(p1,p2)
#         self.assertNotEqual(p1,p3)
#         self.assertNotEqual(p1,p4)



#     def test_reverse_contain_wire(self):
#         p1 = Port()
#         p1.new(clk=Wire(OUTPUT,1))
#         p1.new(rst=Wire(OUTPUT,1))
#         p2 = Port()
#         p2.new(clk=Wire(INPUT,1))
#         p2.new(rst=Wire(INPUT,1))
#         self.assertEqual(p1.reverse(),p2)
#         self.assertEqual(p2.reverse(),p1)

#     def test_reverse_contain_any(self):
#         p1 = Port()
#         p1.new(clk=Wire(OUTPUT,1))
#         p1.new(rst=Wire(OUTPUT,1))
#         p2 = Port()
#         p2.new(clk=Wire(INPUT,1))
#         p2.new(rst=Wire(INPUT,1))
#         
#         pr = Port()
#         p  = Port()
#         pr.new(p=p1)
#         pr.new(w=Wire(INPUT,2))
#         p.new(p=p2)
#         p.new(w=Wire(OUTPUT,2))
#         self.assertEqual(p.reverse(),pr)
#         self.assertEqual(pr.reverse(),p)

#     def test_expand(self):
#         p = self.setup_port_contain_any()
#         exp = p.expand()
#         self.assertIsInstance(exp,list)
#         for w in exp:
#             self.assertIsInstance(w,Wire)
