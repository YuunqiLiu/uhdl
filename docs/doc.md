## 安装
从[https://github.com/YuunqiLiu/uhdl_core.git](https://github.com/YuunqiLiu/uhdl_core.git)获取源代码，将源代码添加到工程文件夹或`PYTONPATH`搜索目录下，并使用`import`语句导入uhdl库。
```
from uhdl            import *
```
## 创建module
udhl中module作为python类存在：
* 用户创建的module必须继承`Component`
* 在`__init__`方法对端口、内部信号等进行描述

下方代码是一个2选1 Mux module。用户必须在`__init__`中首先显式调用父类的`__init__`方法，对module进行初始化。随后，可以进行module内部信号声明与赋值。
```
class Mux(Component):

    def __init__(self):
        # initialization
        super().__init__() 

        # ports
        self.op1 = Input(UInt(31))
        self.op2 = Input(UInt(31))
        self.aclk = Input(UInt(1))
        self.arst = Input(UInt(1))
        self.res = Output(UInt(31))

        # internal signal
        self.sel = Wire(UInt(1))
        
        # assign
        self.sel += Equal(self.op1,self.op2)
        self.res += when(self.sel).then(self.op1).otherwise(self.op2)
        )
```

## 数据类型
### 使用UInt创建常数值
使用`UInt`可以创建指定位宽的常数变量，并设置该变量的值
```
UInt(32) // 32bit, value = 0
UInt(16,255) // 16bit, value = 255
```
通过UInt创建的常数变量只能作为其他变量赋值表达式的右值，并且该变量不会在生成的Verilog中出现
```
class Adder(Component):
    def __init__(self):
        super().__init__()
        self.op1 = Input(UInt(31)) # define op1 as input [30:0] 
        self.op2 = Input(UInt(31))
        self.aclk = Input(UInt(1))
        self.arst = Input(UInt(1))
        self.res = Output(UInt(33)) # define res as output [31:0]
        
        self.op3 = UInt(31,15)

        self.res += self.op1 + self.op2 + self.op3
```
上述代码生成的Verilog中并不包含`op3`
```
module Adder (
	input  [30:0] op1 ,
	input  [30:0] op2 ,
	input         aclk,
	input         arst,
	output [32:0] res );

	//Wire define for this module.

	//Wire define for sub module.

	//Wire sub module connect to this module and inter module connect.
	assign res = ((op1 + op2) + 31'b1111);
	

	//Wire this module connect to sub module.

	//module inst.

endmodule
```
### 声明Port
在以上的例子中，使用了`Input`与`Output`来声明module的端口。
```
Input(template)
Output(template)
```
module的端口声明时需要传入`template`作为模板，例如：`UInt`、`Wire`、`Reg`或者其他的`Input`、`Output`类型的信号，声明的port将于模板拥有相同的位宽。
```
arst = Input(UInt(1))
res = Output(UInt(33)) # define res as output 
```
### 生成Reg与Wire
使用`Reg`与`Wire`生成相应的Verilog变量
```
Reg(template,clk,rst,async_rst,rst_active_low,clk_active_neg)
Wire(template)
```
`Reg`、`Wire`与port相同必须传入`template`作为生成变量的模板。
```
Reg(UInt(32),aclk,arst) # 32bit register with clcok and reset
Wire(UInt(32)) # 32bit wire
```
`Reg`拥有更多的参数对时钟、复位等进行配置，详见下表
|名称|说明|
:--:|:--|
|clk|必要参数，寄存器时钟信号|
|rst|可选参数，寄存器复位信号，默认为空|
|async_rst|可选参数，用来指示复位信号为异步复位或同步复位，默认为True（异步复位）|
|rst_active_low|可选参数，用来指示复位信号有效电平，默认为True（低电平有效）|
|clk_active_neg|可选参数，用来指示时钟信号敏感边沿，默认为False（上升沿敏感）|

## 赋值
uhdl使用`+=`对信号进行赋值操作