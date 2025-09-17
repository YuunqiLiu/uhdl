import os,sys
import unittest

# pylint: disable =unused-wildcard-import
from uhdl import *
# pylint: enable  =unused-wildcard-import

from uhdl.Demo.lwnoc import *


class TestBasic(unittest.TestCase):

    def test_basic_DMst(self):
        mst = DMst(Master())
        mst.generate_verilog()

    def test_basic_DSlv(self):
        slv = DSlv(Slave())
        slv.generate_verilog()

    def test_basic_DArb(self):
        N = Network()

        slv1 = Slave()
        slv2 = Slave()
        arb  = Arbiter(32,32,32,32)

        N.add(slv1)
        N.add(slv2)
        N.add(arb)
        N.link(slv1, arb)
        N.link(slv2, arb)

        darb = arb.create_vinst()
        darb.generate_verilog()

    def test_basic_DDec(self):
        N = Network()

        slv1 = Slave()
        mst1 = Master()
        mst1.global_id_list = [1,2,3]
        mst2 = Master()
        mst2.global_id_list = [4,5,6]
        dec  = Decoder(32,32,32,32)

        N.add(slv1)
        N.add(mst1)
        N.add(mst2)
        N.add(dec)
        N.link(slv1, dec)
        N.link(dec, mst1)
        N.link(dec, mst2)
        N._id_propagation()

        ddec = DDec(dec)
        ddec.generate_verilog()

    def test_basic_DWrap(self):
        slv1 = Slave()
        slv2 = Slave()
        mst1 = Master()
        mst2 = Master()
        arb  = Arbiter(32,32,32,32)
        dec  = Decoder(32,32,32,32)

        N = Network()
        N.add(slv1)
        N.add(slv2)
        N.add(mst1)
        N.add(mst2)
        N.add(arb)
        N.add(dec)
        N._id_propagation()
        
        dwrap = DWrap(N)
        dwrap.generate_verilog()


    @unittest.skip("legacy LwnocArb demo not available in current package")
    def test_LwnocArb(self):
        from uhdl.Demo.lwnoc import LwnocArb
        arb = LwnocArb(4,32)
        arb.generate_verilog()


    @unittest.skip("legacy LwnocDec demo not available in current package")
    def test_LwnocDec(self):
        from uhdl.Demo.lwnoc import LwnocDec
        dec = LwnocDec(4,32,4)
        dec.generate_verilog() 

        #c = Component()
        #port = Port()
        #port.new(clk=Wire(INPUT,1))
        #port.new(rst=Wire(INPUT,1))
        #c.new(cr=port)
        #self.assertIsInstance(c,Component)
    

    @unittest.skip("legacy LwnocXbar demo not available in current package")
    def test_LwnocXbar(self):
        from uhdl.Demo.lwnoc import LwnocXbar
        xbar = LwnocXbar()
        xbar.add_slave(LwnocXbar.Slave([0,1,2,3,4,5,6,7]))
        xbar.add_slave(LwnocXbar.Slave([0,1,2,3,4,5,6,7]))
        xbar.add_master(LwnocXbar.Master([0,1,2,3]))
        xbar.add_master(LwnocXbar.Master([4,5,6,7]))
        xbar.compute_topology()
       # xbar = 

    @unittest.skip("Network visualization test requires GUI; skipping in CI")
    def test_Network(self):
        from uhdl.Demo.lwnoc import Network, Slave, Arbiter, Decoder, Master
        slv1 = Slave()
        slv2 = Slave()
        slv3 = Slave()
        arb1 = Arbiter(32,32,32,32)
        arb2 = Arbiter(32,32,32,32)
        arb3 = Arbiter(32,32,32,32)
        dec1 = Decoder(32,32,32,32)
        dec2 = Decoder(32,32,32,32)
        mst1 = Master()
        mst1.global_id_list = [1,2,3]
        mst2 = Master()
        mst2.global_id_list = [4,5,6]
        mst3 = Master()
        mst3.global_id_list = [7,8,9]
        N = Network()
        N.add(slv1)
        N.add(slv2)
        N.add(slv3)
        N.add(arb1)
        N.add(dec1)
        N.add(dec2)
        N.add(mst1)
        N.add(mst2)
        N.add(arb2)
        N.add(arb3)
        N.link(slv2, arb1)
        N.link(slv3, arb1)
        N.link(arb1, dec1)
        N.link(slv1, dec2)
        N.link(dec1, arb2)
        N.link(dec1, arb3)
        N.link(dec2, arb2)
        N.link(dec2, arb3)
        N.link(arb2, mst1)
        N.link(arb3, mst2)
        N._id_propagation()
        # N._show()


    @unittest.skip("legacy LwnocWrap demo not available in current package")
    def test_LwnocWrap(self):
        from uhdl.Demo.lwnoc import Network, Slave, Arbiter, Decoder, Master, LwnocWrap
        N = Network()
        arb1 = Arbiter(32,32,32,32)
        arb2 = Arbiter(32,32,32,32)
        arb3 = Arbiter(32,32,32,32)
        N.add(arb1)
        N.add(arb2)
        N.add(arb3)
        N._id_propagation()
        wrap = LwnocWrap(N)
        wrap.generate_verilog()