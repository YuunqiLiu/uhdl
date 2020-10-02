from uhdl            import *
class Mux_Nto1(Component):
    
    def __init__(self,src_num,dat_width):
        super().__init__()
#参数定义
        self.src_num = src_num
        self.dat_width = dat_width
        vld_comb_width = self.src_num
#接口定义
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
# 逻辑主体
        vld_src       = Combine(*self.vld_src_lst)
        vld_src_inv   = Inverse(vld_src)
        self.priority += BitAnd(Add(vld_src_inv,UInt(vld_comb_width,1))[vld_comb_width-1:0],vld_src)
        self.vld_dst  += SelfOr(vld_src)

        pld_dst_case  =[(UInt(self.src_num,1<<i),self.pld_src_lst[i]) for i in range(self.src_num)]
        self.pld_dst  += Case(self.priority,pld_dst_case,UInt(self.dat_width,0))

        for i in range(self.src_num):
            self.rdy_src_lst[i] += And(self.priority[i:i],self.rdy_dst)

#实例化模块
#inst_Mux_Nto1 = Mux_Nto1(10,4)
#生成verilog
#inst_Mux_Nto1.generate_verilog()