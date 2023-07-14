from uhdl import *



class LintSub(Component):

    def __init__(self):
        super().__init__()
        self.din1 = Input(UInt(1))
        self.dout1 = Output(UInt(1))

        self.dout1 += self.din1

class LintTop(Component):

    def __init__(self):
        super().__init__()
        self.din1 = Input(UInt(1))
        self.dout1 = Output(UInt(1))

        self.inst = LintSub()
        self.inst.din1 += self.din1
        self.dout1 += self.inst.dout1

def test_slang_compile():
    d1 = LintTop()
    d1.output_dir = 'test_build'
    d1.generate_verilog(iteration=True)
    d1.generate_filelist(abs_path=True)
    d1.run_lint()
    d1.run_slang_compile()