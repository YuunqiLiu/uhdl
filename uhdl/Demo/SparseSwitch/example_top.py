# Minimal example for SparseSwitchFabric (not executed)
from uhdl import *
from uhdl.Demo.SparseSwitch import SparseSwitchFabric

spec = {
    'out0': ['in0', 'in2'],
    'out1': ['in1'],
}

class SparseSwitchTop(Component):
    def __init__(self):
        super().__init__()
        self.in0 = Input(UInt(16))
        self.in1 = Input(UInt(16))
        self.in2 = Input(UInt(16))
        self.sel_out0 = Input(UInt(1))
        self.sel_out1 = Input(UInt(1))
        self.out0 = Output(UInt(16))
        self.out1 = Output(UInt(16))

        self.sw = SparseSwitchFabric(spec, DW=16)
        self.sw.in0 += self.in0
        self.sw.in1 += self.in1
        self.sw.in2 += self.in2
        self.sw.sel_out0 += self.sel_out0
        self.sw.sel_out1 += self.sel_out1
        self.out0 += self.sw.out0
        self.out1 += self.sw.out1

# Usage:
# t = SparseSwitchTop(); t.output_dir='build'; t.generate_verilog(iteration=True)
