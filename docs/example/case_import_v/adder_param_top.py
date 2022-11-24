from uhdl import *

class AdderParamTop(Component):

    def __init__(self, WIDTH = 64):
        super().__init__()
     
        # IO define
        self.din1   = Input(UInt(WIDTH))
        self.din2   = Input(UInt(WIDTH))
        self.dout   = Output(UInt(WIDTH+1))

        # Import adder.v and instantiate it as a component in UHDL.
        self.u_adder = VComponent('docs/example/case_import_v/adder_param.v','adder_param', WIDTH=WIDTH)

        self.dout += self.u_adder.dout
        self.u_adder.din1 += self.din1
        self.u_adder.din2 += self.din2


# build a instance
u_adder_param_top = AdderParamTop()

# generate verilog
u_adder_param_top.output_dir = 'docs/generated_verilog'
u_adder_param_top.generate_verilog()
