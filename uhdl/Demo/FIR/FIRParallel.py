from uhdl import *
from uhdl.core.Variable import Constant
from uhdl.core.Operator import Combine

class FIRParallel(Component):
    def __init__(self, tap_num=4, data_width=16, coef_width=16):
        self.tap_num = tap_num
        self.data_width = data_width
        self.coef_width = coef_width
        # 输入信号
        self.data_in = Input(UInt(data_width))
        # 系数输入（每个抽头一个系数）
        for i in range(tap_num):
            setattr(self, f'coef_{i}', Input(UInt(coef_width)))
        self.coef = [getattr(self, f'coef_{i}') for i in range(tap_num)]
        # 输出信号
        max_mul_width = data_width + coef_width
        max_acc_width = max_mul_width + int(tap_num).bit_length()
        self.data_out = Output(UInt(max_acc_width))
        # 时钟和复位
        self.clk = Input(UInt(1))
        self.rst = Input(UInt(1))
        # 内部寄存器阵列，保存历史输入
        for i in range(tap_num):
            setattr(self, f'shift_reg_{i}', Reg(UInt(data_width), self.clk, self.rst))
        self.shift_reg = [getattr(self, f'shift_reg_{i}') for i in range(tap_num)]
        super().__init__()

    def circuit(self):
        # 输入移位
        self.shift_reg[0] += self.data_in
        for i in range(1, self.tap_num):
            self.shift_reg[i] += self.shift_reg[i-1]
        # 并行乘法和累加
        mul_results = [self.shift_reg[i] * self.coef[i] for i in range(self.tap_num)]
        max_mul_width = self.data_width + self.coef_width
        max_acc_width = max_mul_width + int(self.tap_num).bit_length()
        # 统一 attribute（取最大宽度）
        mul_results = [Cut(m, max_mul_width-1, 0) if m.attribute.width < max_mul_width else m for m in mul_results]
        wire_width = self.data_width * 2
        setattr(self, 'acc_wire_0', Wire(UInt(wire_width)))
        acc_wire = getattr(self, 'acc_wire_0')
        acc_wire += mul_results[0]
        acc_wire_name = 'acc_wire_0'
        for i in range(1, self.tap_num):
            tmp_name = f'acc_wire_{i}'
            setattr(self, tmp_name, Wire(UInt(wire_width)))
            tmp_wire = getattr(self, tmp_name)
            tmp_wire += Cut(getattr(self, acc_wire_name) + mul_results[i], wire_width-1, 0)
            acc_wire_name = tmp_name
        pad_width = self.data_out.attribute.width - wire_width
        if pad_width > 0:
            self.data_out += Combine(UInt(pad_width, 0), getattr(self, acc_wire_name))
        else:
            self.data_out += getattr(self, acc_wire_name)

# 示例：tap_num=8, data_width=16, coef_width=16
if __name__ == "__main__":
    fir = FIRParallel(tap_num=8, data_width=16, coef_width=16)
    print(fir.area_report())
