# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import

import math

from . import Mux_1toM
from . import Mux_Nto1

class Crossbar(Component):
    
    def __init__(self,src_num,dst_num,dat_width,priority_sel):
        super().__init__()
#参数定义
        self.src_num = src_num
        self.dst_num = dst_num
        self.dat_width = dat_width
        self.priority_sel = priority_sel
        sel_width = math.ceil(math.log(self.dst_num,2))
#接口定义
        if self.priority_sel == 1:
                self.clk = Input(UInt(1))
                self.rst_n = Input(UInt(1))

        vld_src_lst = [self.set("vld_src%d"%i,Input(UInt(1))) for i in range(0,self.src_num)]
        pld_src_lst = [self.set("pld_src%d"%i,Input(UInt(self.dat_width))) for i in range(0,self.src_num)]
        rdy_src_lst = [self.set("rdy_src%d"%i,Output(UInt(1))) for i in range(0,self.src_num)]
        sel_src_lst = [self.set("sel_src%d"%i,Input(UInt(sel_width))) for i in range(0,self.src_num)]

        vld_dst_lst = [self.set("vld_dst%d"%i,Output(UInt(1))) for i in range(0,self.dst_num)] 
        pld_dst_lst = [self.set("pld_dst%d"%i,Output(UInt(self.dat_width))) for i in range(0,self.dst_num)]
        rdy_dst_lst = [self.set("rdy_dst%d"%i,Input(UInt(1))) for i in range(0,self.dst_num)]
# #实例化模块
        Mux_1toM_lst = [self.set("inst_Mux_1toM_%d"%i,Mux_1toM.Mux_1toM(self.dst_num,self.dat_width)) for i in range(0,self.src_num)]
        Mux_Nto1_lst = [self.set("inst_Mux_Nto1_%d"%i,Mux_Nto1.Mux_Nto1(self.src_num,self.dat_width,self.priority_sel)) for i in range(0,self.dst_num)]
# 接口连接
        for i in range(self.dst_num):
            for j in range(self.src_num):
                Mux_Nto1_lst[i].vld_src_lst[j] += Mux_1toM_lst[j].vld_dst_lst[i]
                Mux_Nto1_lst[i].pld_src_lst[j] += Mux_1toM_lst[j].pld_dst_lst[i]
                Mux_1toM_lst[j].rdy_dst_lst[i] += Mux_Nto1_lst[i].rdy_src_lst[j]

        for i in range(self.src_num):
            Mux_1toM_lst[i].vld_src += vld_src_lst[i]
            Mux_1toM_lst[i].pld_src += pld_src_lst[i]
            Mux_1toM_lst[i].sel_src += sel_src_lst[i]
            rdy_src_lst[i] += Mux_1toM_lst[i].rdy_src

        for i in range(self.dst_num):
            vld_dst_lst[i] += Mux_Nto1_lst[i].vld_dst
            pld_dst_lst[i] += Mux_Nto1_lst[i].pld_dst
            Mux_Nto1_lst[i].rdy_dst += rdy_dst_lst[i]
            if self.priority_sel == 1:
                Mux_Nto1_lst[i].clk += self.clk
                Mux_Nto1_lst[i].rst_n += self.rst_n
        


#实例化Top模块
#inst_Crossbar_NtoM = Crossbar(4,2,4,1) # src number, dst number, data width, priority select :0->always low 1->RR
#生成verilog
#inst_Crossbar_NtoM.generate_verilog(True)