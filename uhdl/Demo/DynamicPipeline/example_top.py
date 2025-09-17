# Minimal example for DynamicPipeline (not executed)
from uhdl import *
from uhdl.Demo.DynamicPipeline import DynamicPipeline

stages = [
    {'w': 16, 'op': 'add', 'const': 1, 'reg': True},
    {'w': 24, 'op': 'mul', 'const': 3, 'reg': False},
    {'w': 24, 'op': 'id',  'reg': True},
]

class PipelineTop(Component):
    def __init__(self):
        super().__init__()
        self.clk   = Input(UInt(1))
        self.rst_n = Input(UInt(1))
        self.din   = Input(UInt(16))
        self.dout  = Output(UInt(24))

        self.pipe = DynamicPipeline(stages)
        self.pipe.clk   += self.clk
        self.pipe.rst_n += self.rst_n
        self.pipe.din   += self.din
        self.dout       += self.pipe.dout

# Usage:
# t = PipelineTop(); t.output_dir='build'; t.generate_verilog(iteration=True)
