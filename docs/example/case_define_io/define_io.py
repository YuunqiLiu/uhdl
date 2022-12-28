from uhdl import *


# Define a new component named "DefineIO".
class DefineIO(Component):

    def __init__(self):
        # It is very important to pass super(). __init__() 
        # to call the initialization process in the parent class "Component".
        super().__init__()

        self.din = Input(UInt(32))
        self.dout = Output(UInt(32))


# build a instance
inst = DefineIO()

# generate verilog
inst.output_dir = 'docs/generated_verilog'
inst.generate_verilog()
