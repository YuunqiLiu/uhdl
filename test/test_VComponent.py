from uhdl import *


class VCompBasic(Component):

    def __init__(self):
        super().__init__()

        self.din = Input(UInt(32))
        self.din2 = Input(UInt(64))

        self.inst1 = VComponent(file='test/verilog/module1.v',top='module1',DATA_WIDTH=32)
        self.inst2 = VComponent(file='test/verilog/module1.v',top='module1',DATA_WIDTH=64)

        self.inst1.din += self.din
        self.inst2.din += self.din2

def test_VComp_Basic():

    inst = VCompBasic()
    inst.output_dir = 'test_build'
    inst.generate_verilog()
