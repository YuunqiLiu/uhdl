import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from uhdl import *


class Test(Component):

    def __init__(self):
        super().__init__()
        self.clk    = Input(UInt(1))
        self.rst_n  = Input(UInt(1))
        self.comp   = VComponent('test.v', top='test_v')
        self.comp.clk += self.clk
        self.comp.rst_n += self.rst_n


        # self.data_in = Input(UInt(32))
        # self.data_out = Output(UInt(32))
        # data pipeline registers with clk and reset
        # self.data_reg = Reg(UInt(32), clk=self.clk, rst=self.rst_n)






a = Test()
a.generate_verilog()
a.generate_filelist(prefix="qwer")