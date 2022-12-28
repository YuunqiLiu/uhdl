from uhdl import *


# Define a new component named "EmptyModule".
class EmptyModule(Component):

    def __init__(self):
        # It is very important to pass super(). __init__() 
        # to call the initialization process in the parent class "Component".
        super().__init__()



# build a instance
inst = EmptyModule()

# generate verilog
inst.output_dir = 'docs/generated_verilog'
inst.generate_verilog()
