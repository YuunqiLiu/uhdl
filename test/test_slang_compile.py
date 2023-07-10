from uhdl import *



class SlangCompile(Component):

    def __init__(self):
        super().__init__()
        self.din1 = Input(UInt(1))
        self.dout1 = Output(UInt(1))

        #self.dout1 += self.din1

def test_slang_compile():
    d1 = SlangCompile()
    d1.output_dir = 'test_build'
    d1.generate_verilog(iteration=True)
    d1.generate_filelist(abs_path=True)
    d1.run_slang_compile()