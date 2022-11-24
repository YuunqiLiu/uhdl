from uhdl import *

class FirstComp(Component):

    def __init__(self):
        super().__init__()
     
        # IO define
        self.clk    = Input(UInt(1))
        self.rst_n  = Input(UInt(1))
        self.din1   = Input(UInt(1))
        self.din2   = Input(UInt(1))
        self.dout   = Output(UInt(2))

        # Reg define
        self.dout_reg = Reg(UInt(2,0),self.clk,self.rst_n)

        # connect (din1 + din2) to dout_reg
        self.dout_reg += self.din1 + self.din2

        # connect dout_reg to dout
        self.dout += self.dout_reg

# build a instance
inst = FirstComp()

# generate verilog
inst.output_dir = 'docs/generated_verilog'
inst.generate_verilog()
