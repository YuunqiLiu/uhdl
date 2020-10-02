from uhdl            import *
import math

class Mux_1toM(Component):
    
    def __init__(self,dst_num,dat_width):
        super().__init__()
#参数定义
        self.dst_num = dst_num
        self.dat_width = dat_width
        sel_width = math.ceil(math.log(self.dst_num,2))
#接口定义
        self.vld_src  = Input(UInt(1)) 
        self.pld_src  = Input(UInt(self.dat_width)) 
        self.rdy_src  = Output(UInt(1))
        self.sel_src  = Input(UInt(sel_width))

        self.vld_dst_lst = [self.set("vld_dst%d"%i,Output(UInt(1))) for i in range(0,self.dst_num)] 
        self.pld_dst_lst = [self.set("pld_dst%d"%i,Output(UInt(self.dat_width))) for i in range(0,self.dst_num)]
        self.rdy_dst_lst = [self.set("rdy_dst%d"%i,Input(UInt(1))) for i in range(0,self.dst_num)]
# 声明类型
        self.vld_mask = Wire(UInt(self.dst_num))
        self.rdy_dst  = Wire(UInt(self.dst_num))
# 逻辑主体
        self.vld_mask += Combine(UInt(self.dst_num-1,0),self.vld_src) << self.sel_src
        self.rdy_dst  += Combine(*self.rdy_dst_lst)     
        self.rdy_src  += SelfOr(BitAnd(self.vld_mask,self.rdy_dst))

        for i in range(self.dst_num):
            self.vld_dst_lst[i] += And(self.vld_mask[i:i],self.vld_src)
            self.pld_dst_lst[i] += when(self.vld_mask[i:i]).then(self.pld_src).otherwise(UInt(self.dat_width,0))

#实例化模块
#inst_Mux_1toM = Mux_1toM()
#生成verilog
#inst_Mux_1toM.generate_verilog()