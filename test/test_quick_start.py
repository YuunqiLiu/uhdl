import os,sys
import unittest

# pylint: disable =unused-wildcard-import
from uhdl import *
# pylint: enable  =unused-wildcard-import

# from uhdl.core.Exception import ErrAttrMismatch         ,\
#                                 ErrExpInTypeWrong       ,\
#                                 ErrListExpNeedMultiOp   ,\
#                                 ErrCutExpSliceInvalid   ,\
#                                 ErrAttrTypeWrong        ,\
#                                 ErrBitsValOverflow      ,\
#                                 ErrBitsInvalidStr

# from ..core             import InternalTool as IT

class TestQuickStart(unittest.TestCase):

    def test_basic_io(self):
        class Adder(Component):                     #与verilog中的module类似，UHDL中电路的最小集合为Component
                                                    #在开始描述电路前，要声明一个Component，这句话就声明了一个名为"Adder"的Component
    
            def __init__(self):                     #这是一个"惯例"，请原封不动放在这里     
                super().__init__()                    #这也是一个"惯例"

                self.in1 = Input(UInt(1))           #这句话为Adder添加了一个input in1，位宽为1
                                                    #等效于verilog中的"input [0:0] in1"
                self.in2 = Input(UInt(1))           #这句话为Adder添加了一个input in2，位宽为1
                                                    #等效于verilog中的"input [0:0] in2"
                self.out = Output(UInt(2))          #这句话为Adder添加了一个output out，位宽为2
                                                    #等效于verilog中的"output [1:0] out"
                
                self.out += self.in1 + self.in2     #这句话表达了out与in1/in2之间的逻辑关系
                                                    #即表达了一个加法器，将in1和in2相加，其输出连接到out
                                                    #在verilog中即为out赋值，out的值为in1+in2
                                                    #等效为assign out = in1 + in2
                                                    #请注意UHDL中"="和"+="的不同，UHDL不需要专门的声明语句，
                                                    #在Component中直接用"="就可以创建一个元素，例如input、output
                                                    #而"+="则用来完成元素之间的连接

        inst_adder = Adder()                        #实例化模块
        inst_adder.output_dir = 'test_build'
        inst_adder.generate_verilog()               #生成verilog

    def test_basic_reg(self):
        
        class AdderReg(Component):

            def __init__(self):
                super().__init__()

                self.clk   = Input(UInt(1))                     #这部分和上个例子一样进行了IO定义
                self.rst_n = Input(UInt(1))                     #不过多了clk和rst_n，即时钟和复位输入
                self.in1   = Input(UInt(1))
                self.in2   = Input(UInt(1))
                self.out   = Output(UInt(2))

                self.out_reg = Reg(UInt(2),self.clk,self.rst_n) #这句话定义了一个寄存器out_reg
                                                                #并将寄存器的clock连接为输入信号clk
                                                                #寄存器的reset连接为rst_n

                self.out_reg += self.in1 + self.in2             #与上个例子相似，
                                                                #这句话将寄存器的输入端连接到
                                                                #组合逻辑in1+in2的输出端

                self.out += self.out_reg                        #这句话将寄存器out_reg的输出端连接到out

        inst_adder = AdderReg()                         #实例化模块
        inst_adder.output_dir = 'test_build'
        inst_adder.generate_verilog()                   #生成verilog

    def test_basic_when(self):

        class Mux(Component):

            def __init__(self):
                super().__init__()
                
                self.in1 = Input(UInt(1))           #IO定义
                self.in2 = Input(UInt(1))
                self.sel = Input(UInt(1))
                self.out = Output(UInt(1))

                self.out += when(Equal(self.sel,UInt(1,0))).then(self.in1).otherwise(self.in2)

                #与上例类似，UHDL描述一个电路的方式是声明电路结构，
                #这里直接声明了out连接到一个mux的输出端
                #这句话与verilog中的
                # assign out = (sel==1'b0)?in1:in2 实现了一样的结构
                #在UHDL中判断语句的关键词为when/then/otherwise
                #多个when(x).then(x).when(x).then(x).otherwise同样是支持的

        inst_adder = Mux()                              #实例化模块
        inst_adder.output_dir = 'test_build'
        inst_adder.generate_verilog()                   #生成verilog

    def test_py_dynamic_io(self):
        
        import math

        class DynamicMux(Component):

            def __init__(self,CHANNEL_NUM = 4,DW= 32):
                super().__init__()

                if (CHANNEL_NUM*(CHANNEL_NUM-1) ==0 ):                      #对输入参数做检查
                    raise Exception('log2(CHANNEL_NUM) is not an integer')  #如果通道数不为2的n次方则报错

                CH_LOG2 = int(math.log(CHANNEL_NUM,2))                      #计算内部参数

                for i in range(0,CHANNEL_NUM):                              #根据参数实例化同样数量的输入端口
                    self.set('in%d' % i,Input(UInt(DW)))

                self.sel = Input(UInt(CH_LOG2))                             #根据参数实例化指定位宽的选择信号
                self.out = Output(UInt(DW))                                 #定义输出端口

                sel_circuit = EmptyWhen()                                   #声明一个选择电路

                for i in range(0,CHANNEL_NUM):                              #为选择电路定义不同的条件和结果
                    sel_circuit.when(Equal(self.sel,UInt(CH_LOG2,i))).then(self.get('in%d' % i))

                sel_circuit.otherwise(UInt(DW,0))                           #定义选择电路的默认结果

                self.out += sel_circuit                                     #将选择电路的输出端接到端口out上

        inst_dynamic_mux = DynamicMux()                                     #实例化模块
        inst_dynamic_mux.output_dir = 'test_build'
        inst_dynamic_mux.generate_verilog()                                 #生成verilog

        Not,Inverse,Add
        BitXor,Mul,SelfXnor