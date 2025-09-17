# Minimal example for BitfieldPack/Unpack (not executed)
from uhdl import *
from uhdl.Demo.Bitfield import BitfieldPack, BitfieldUnpack

# 8 + 10 + 1 = 19 bits
spec = [('op', 8), ('id', {'width': 10}), ('flag', 1)]

class BitfieldTop(Component):
    def __init__(self):
        super().__init__()
        self.op   = Input(UInt(8))
        self.id   = Input(UInt(10))
        self.flag = Input(UInt(1))
        self.out_bus = Output(UInt(19))

        self.pack = BitfieldPack(spec)
        self.pack.op   += self.op
        self.pack.id   += self.id
        self.pack.flag += self.flag
        self.out_bus   += self.pack.out

        self.unpack = BitfieldUnpack(spec)
        self.unpack.in_bus += self.out_bus

# Usage:
# t = BitfieldTop(); t.output_dir='build'; t.generate_verilog(iteration=True)
