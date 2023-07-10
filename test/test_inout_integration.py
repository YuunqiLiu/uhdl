


from uhdl import *


class InoutIntegSub(Component):

    def __init__(self):
        super().__init__()
        self.d1 = Inout(UInt(1))
        self.d2 = Inout(UInt(1))

        #self.d2 += self.d1

class InoutIntegTop(Component):

    def __init__(self):
        super().__init__()
        self.d1 = Inout(UInt(1))
        self.d2 = Inout(UInt(1))

        self.sub1 = InoutIntegSub()
        self.sub2 = InoutIntegSub()

        self.sub1.d1 += self.d1
        
        self.sub2.d1 += self.sub1.d2

        self.d2 += self.sub2.d2

def test_inout_integration():

    s = InoutIntegTop()
    s.output_dir = 'test_build'
    s.generate_verilog(iteration=True)
    s.generate_filelist()


if __name__ == "__main__":
    pass