from uhdl import *

class AdderTop(Component):

    def __init__(self):
        super().__init__()
     
        # IO define
        self.din1   = Input(UInt(32))
        self.din2   = Input(UInt(32))
        self.dout   = Output(UInt(33))

        # Import adder.v and instantiate it as a component in UHDL.
        self.u_adder = VComponent('docs/example/case_import_v/adder.v','adder')


        self.dout += self.u_adder.dout
        self.u_adder.din1 += self.din1
        self.u_adder.din2 += self.din2


# build a instance
u_adder_top = AdderTop()

# generate verilog
u_adder_top.output_dir = 'docs/generated_verilog'
u_adder_top.generate_verilog()
