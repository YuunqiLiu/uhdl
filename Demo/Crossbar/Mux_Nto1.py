# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import

class Mux_Nto1(Component):
    
    def __init__(self,src_num,dat_width,priority_sel):
        super().__init__()
#参数定义
        self.src_num = src_num
        self.dat_width = dat_width
        self.priority_sel = priority_sel
        vld_comb_width = self.src_num
#接口定义
        if self.priority_sel == 1:
            self.clk = Input(UInt(1))
            self.rst_n = Input(UInt(1))

        self.vld_src_lst = [self.set("vld_src%d"%i,Input(UInt(1))) for i in range(0,self.src_num)] 
        self.pld_src_lst = [self.set("pld_src%d"%i,Input(UInt(self.dat_width))) for i in range(0,self.src_num)]
        self.rdy_src_lst = [self.set("rdy_src%d"%i,Output(UInt(1))) for i in range(0,self.src_num)]

        self.vld_dst  = Output(UInt(1)) 
        self.pld_dst  = Output(UInt(self.dat_width)) 
        self.rdy_dst  = Input(UInt(1))
# 声明类型
        self.priority = Wire(UInt(self.src_num))
        self.vld_src  = Wire(UInt(self.src_num))
# 逻辑主体
        self.vld_src  = Combine(*self.vld_src_lst)

        #常用逻辑定义为函数       
        def always_low(input_signal):
            self.pre_inv_add  = Wire(UInt(vld_comb_width+1))

            input_inv = Inverse(input_signal)
            self.pre_inv_add  += Add(input_inv,UInt(vld_comb_width,1))
            return BitAnd(self.pre_inv_add[vld_comb_width-1:0],input_signal)
        
        #根据参数选择生成不同逻辑
        def priority_select(select):
            # 0 -> always low
            if   select == 0:
                return always_low(self.vld_src)
            # 1 -> round robin
            elif select == 1:
                self.pre_high     = Wire(UInt(vld_comb_width))
                self.pre_add      = Wire(UInt(vld_comb_width+1))
                self.pre_vld      = Wire(UInt(vld_comb_width)) 
                self.pre_high_vld = Wire(UInt(vld_comb_width))
                self.pre_low_vld  = Wire(UInt(vld_comb_width))
                self.pre_priority = Reg(UInt(vld_comb_width,0),self.clk,self.rst_n)

                pre_priority_inv  = Inverse(self.pre_priority)
                self.pre_add      += Add(pre_priority_inv,UInt(vld_comb_width,1))
                self.pre_high     += BitOr(self.pre_add[vld_comb_width-1:0],self.pre_priority)
                self.pre_high_vld += BitAnd(self.pre_high,self.vld_src)
                self.pre_low_vld  += BitAnd(Inverse(self.pre_high),self.vld_src)

                self.pre_priority += Combine(self.priority[vld_comb_width-2:0],self.priority[vld_comb_width-1:vld_comb_width-1])
                result = When(SelfOr(self.pre_high_vld)).Then(always_low(self.pre_high_vld)).Ohterwise(always_low(self.pre_high_vld))
                return result

        self.priority += priority_select(self.priority_sel)
        self.vld_dst  += SelfOr(self.vld_src)

        pld_dst_case  =[(UInt(self.src_num,1<<i),self.pld_src_lst[i]) for i in range(self.src_num)]
        self.pld_dst  += Case(self.priority,pld_dst_case,UInt(self.dat_width,0))

        for i in range(self.src_num):
            self.rdy_src_lst[i] += And(self.priority[i:i],self.rdy_dst)

#实例化模块
#inst_Mux_Nto1 = Mux_Nto1(4,4,1)
#生成verilog
#inst_Mux_Nto1.generate_verilog()