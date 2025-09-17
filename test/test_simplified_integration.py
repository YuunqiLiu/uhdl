

from uhdl import *

class sub_mod(Component):

    def __init__(self):
        super().__init__()

        self.din0 = Input(UInt(1))
        self.din1 = Input(UInt(1))
        self.dout1 = Output(UInt(1))
        self.din2 = Input(UInt(1))
        self.dout2 = Output(UInt(1))

        self.dout1 += self.din1
        self.dout2 += self.din2

class top(Component):

    def __init__(self):
        super().__init__()
        self.din1 = Input(UInt(1))
        self.dout1 = Output(UInt(1))
        self.din2 = Input(UInt(1))
        self.dout2 = Output(UInt(1))

        self.sub1 = sub_mod()
        self.sub2 = sub_mod()
        
        self.sub1.din0 += UInt(1,0)
        self.sub2.din0 += And(self.sub1.dout1, self.sub1.dout2)

        # red line
        self.dout1      += self.sub2.dout1
        self.sub1.din1  += self.din1
        
        # blue line
        self.sub2.din1  += self.sub1.dout1

        # green line
        #self.sub2.din2  += self.sub1.dout2
        #self.sub1.din2  += self.sub1.dout2

        self.sub2.din2  += self.sub1.dout2
        self.sub1.din2  += self.sub2.dout2

            
def test_simplified_integration():

    t = top()
    t.output_dir = 'test_build/test_simplified_integration'
    t.generate_verilog(iteration=True)
    t.generate_filelist(abs_path=True)

if __name__ == "__main__":
    test_simplified_integration()