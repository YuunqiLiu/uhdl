import unittest

# pylint: disable =unused-wildcard-import
from uhdl import *
# pylint: enable  =unused-wildcard-import




class TestAssign(unittest.TestCase):


    
    def test_Assign_Right(self):
        class design(Component):
            def __init__(self):
                super().__init__()
                self.in0  = Input(UInt(1))
                self.out0 = Output(UInt(1))
                Assign(self.out0,self.in0)

        dut = design()

    def test_Assign_Wrong(self):
        class design(Component):
            def __init__(self):
                super().__init__()
                self.in0  = Input(UInt(1))
                self.in1 = Output(UInt(1))
                #self.in0 += self.out0
                Assign(self.in0,self.in1)
        dut = design()
