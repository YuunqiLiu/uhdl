import os,sys
import unittest

# pylint: disable =unused-wildcard-import
from uhdl.Demo import *
from uhdl import *
# pylint: enable  =unused-wildcard-import


class Caculator(Component):
    def __init__(self,mode):
        super().__init__()
        self.din0 = Input(UInt(1))
        self.din1 = Input(UInt(1))
        self.dout = Output(UInt(2))

        if mode == 'add':
            self.dout += self.din0 + self.din1
        else:
            self.dout += self.din0 - self.din1

class UniqueNameTestWrapper(Component):
    def __init__(self):
        super().__init__()
        self.din0 = Input(UInt(1))
        self.din1 = Input(UInt(1))
        self.dout0 = Output(UInt(2))
        self.dout1 = Output(UInt(2))

        self.cal0 = Caculator('add')
        self.cal1 = Caculator('sub')

        self.cal0.din0 += self.din0
        self.cal1.din0 += self.din0
        self.cal0.din1 += self.din1
        self.cal1.din1 += self.din1
        
        self.dout0 += self.cal0.dout
        self.dout1 += self.cal1.dout



class TestNameSys(unittest.TestCase):
    
    def test_unique_name(self):
        res = UniqueNameTestWrapper()
        res.output_path = './Vout/Test/unique_name'
        res.generate_verilog(iteration=True)