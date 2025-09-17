# Minimal example for RomFromFile (not executed)
from uhdl import *
from uhdl.Demo.RomFromFile import RomFromFile

data = {0: 5, 1: 7, 4: 9}

class RomTop(Component):
    def __init__(self):
        super().__init__()
        self.key = Input(UInt(4))
        self.val = Output(UInt(8))
        self.rom = RomFromFile(data, key_w=4, val_w=8, default=0)
        self.rom.key += self.key
        self.val     += self.rom.val

# Usage:
# t = RomTop(); t.output_dir='build'; t.generate_verilog(iteration=True)
