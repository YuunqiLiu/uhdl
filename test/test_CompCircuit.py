from uhdl import *

class Test(Component):
    def circuit(self):
        self.din = Input(UInt(1))
        self.dout = Output(UInt(1))

        Assign(self.dout, self.din)





def test_CompCircuit():
    t = Test()
    t.output_dir = 'test_build/test_CompCircuit'
    t.compile()
