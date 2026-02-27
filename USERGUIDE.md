# UHDL 用户指南

## 简介

UHDL (Universal Hardware Description Language) 是一个基于 Python 的硬件描述语言。它能够从 Python 代码生成可综合的 Verilog，让硬件工程师可以利用 Python 的表达能力来设计数字电路。

**核心优势：**

- **Python 的表达能力**：用 Python 的循环、条件、类继承来实现参数化设计
- **类型安全**：编译时检查位宽和类型匹配
- **自动化 Lint**：内置 Lint 检查，编译时自动运行
- **SystemVerilog 互操作**：通过 VComponent 直接导入现有 Verilog/SystemVerilog 模块，支持 struct/enum/union typedef

---

## 安装

```bash
pip install uhdl
```

或者从源码安装：

```bash
git clone <repo-url>
cd uhdl
pip install -e .
```

**依赖：**

- Python 3
- pyslang（用于 VComponent 导入 Verilog，可选）

---

## 核心概念

在开始使用 UHDL 之前，需要理解两个最重要的概念：

### `=` 创建元素

在 Component 内部，`=` 用于创建并命名电路元素：

```python
self.in1 = Input(UInt(1))    # 创建名为 "in1" 的输入端口
self.out = Output(UInt(8))   # 创建名为 "out" 的输出端口
self.w   = Wire(UInt(4))     # 创建名为 "w" 的内部连线
```

UHDL 利用 Python 的 `__setattr__` 魔术方法，自动将属性名设为端口名。

### `+=` 连接电路

`+=` 用于表达信号之间的连接关系：

```python
self.out += self.in1 + self.in2    # 等效于 Verilog: assign out = in1 + in2
```

**切记：`=` 是声明，`+=` 是连接。** 这是 UHDL 最根本的设计规则。

### Component — 基本构建块

Component 是 UHDL 中电路的基本单元，等效于 Verilog 中的 `module`。有两种定义风格：

- **`__init__` 风格**：在构造函数中定义 IO 和逻辑
- **`circuit()` 风格**：在 `circuit()` 方法中定义（更简洁）

---

## 基本 IO 类型

UHDL 提供以下基本 IO 类型：

```python
from uhdl import *

class MyModule(Component):
    def __init__(self):
        super().__init__()

        # 输入端口
        self.data_in  = Input(UInt(8))     # 8 位无符号输入
        self.signed_in = Input(SInt(16))   # 16 位有符号输入

        # 输出端口
        self.data_out = Output(UInt(8))    # 8 位无符号输出

        # 双向端口
        self.bidir    = Inout(UInt(1))     # 1 位双向端口

        # 内部信号
        self.wire_a   = Wire(UInt(4))      # 4 位内部连线

        # 寄存器（需要时钟和复位）
        self.clk      = Input(UInt(1))
        self.rst_n    = Input(UInt(1))
        self.reg_a    = Reg(UInt(8), self.clk, self.rst_n)  # 8 位寄存器
```

| 类型 | 说明 | Verilog 等效 |
|---|---|---|
| `Input(UInt(N))` | N 位无符号输入 | `input [N-1:0]` |
| `Input(SInt(N))` | N 位有符号输入 | `input signed [N-1:0]` |
| `Output(UInt(N))` | N 位无符号输出 | `output [N-1:0]` |
| `Inout(UInt(N))` | N 位双向端口 | `inout [N-1:0]` |
| `Wire(UInt(N))` | N 位内部连线 | `wire [N-1:0]` |
| `Reg(UInt(N), clk, rst)` | N 位寄存器 | `reg [N-1:0]` + always 块 |

---

## 第一个 Component

下面是一个最简单的例子——一个加法器：

```python
from uhdl import *

class Adder(Component):
    def __init__(self):
        super().__init__()
        self.in1 = Input(UInt(1))      # 1 位输入 in1
        self.in2 = Input(UInt(1))      # 1 位输入 in2
        self.out = Output(UInt(2))     # 2 位输出 out

        self.out += self.in1 + self.in2  # out = in1 + in2

# 实例化并生成 Verilog
adder = Adder()
adder.output_dir = 'build'
adder.generate_verilog()
```

生成的 Verilog 代码等效于：

```verilog
module Adder(
    input  [0:0] in1,
    input  [0:0] in2,
    output [1:0] out
);
    assign out = in1 + in2;
endmodule
```

---

## circuit() 风格

除了在 `__init__` 中定义电路，还可以使用更简洁的 `circuit()` 风格：

```python
from uhdl import *

class PassThrough(Component):
    def circuit(self):
        self.din  = Input(UInt(1))
        self.dout = Output(UInt(1))
        Assign(self.dout, self.din)    # dout = din

t = PassThrough()
t.output_dir = 'build'
t.compile()    # compile() = generate_verilog() + generate_filelist() + run_lint()
```

`circuit()` 风格不需要 `super().__init__()`，代码更简洁。使用 `compile()` 代替 `generate_verilog()` 可以同时生成文件列表和运行 Lint 检查。

---

## 寄存器

使用 `Reg` 创建寄存器，需要指定时钟和异步复位信号：

```python
from uhdl import *

class AdderReg(Component):
    def __init__(self):
        super().__init__()

        self.clk   = Input(UInt(1))        # 时钟
        self.rst_n = Input(UInt(1))        # 异步复位（低有效）
        self.in1   = Input(UInt(1))
        self.in2   = Input(UInt(1))
        self.out   = Output(UInt(2))

        # 定义寄存器：Reg(类型, 时钟, 复位)
        self.out_reg = Reg(UInt(2), self.clk, self.rst_n)

        # += 连接到寄存器的输入端（D 端）
        self.out_reg += self.in1 + self.in2

        # 读取寄存器就是读取其输出端（Q 端）
        self.out += self.out_reg

adder_reg = AdderReg()
adder_reg.output_dir = 'build'
adder_reg.generate_verilog()
```

**要点：**

- `Reg(type, clk, rst_n)` — 创建带时钟和异步复位的寄存器
- `reg += expr` — 将表达式连接到寄存器的 D 端输入
- 引用 `self.out_reg` — 读取寄存器的 Q 端输出
- 生成的 Verilog 为 `always @(posedge clk or negedge rst_n)` 块

---

## 表达式与运算符

UHDL 支持丰富的运算符，可以用 Python 运算符语法或函数式调用：

### 算术运算

```python
self.sum  += self.a + self.b       # Add(a, b)     → a + b
self.diff += self.a - self.b       # Sub(a, b)     → a - b
self.prod += self.a * self.b       # Mul(a, b)     → a * b
```

### 比较运算

```python
Equal(self.a, self.b)              # a == b
NotEqual(self.a, self.b)           # a != b
Greater(self.a, self.b)            # a > b
Less(self.a, self.b)               # a < b
GreaterEqual(self.a, self.b)       # a >= b
LessEqual(self.a, self.b)         # a <= b
```

### 逻辑运算

```python
And(self.a, self.b)                # a && b
Or(self.a, self.b)                 # a || b
```

### 位运算

```python
BitAnd(self.a, self.b)             # a & b
BitOr(self.a, self.b)              # a | b
BitXor(self.a, self.b)             # a ^ b
BitXnor(self.a, self.b)            # a ~^ b
```

### 一元运算

```python
Inverse(self.a)                    # ~a  (按位取反)
Not(self.a)                        # !a  (逻辑非)
```

### 归约运算

```python
SelfOr(self.a)                     # |a   (归约或)
SelfAnd(self.a)                    # &a   (归约与)
SelfXor(self.a)                    # ^a   (归约异或)
SelfXnor(self.a)                   # ~^a  (归约同或)
```

### 拼接与切片

```python
# 信号拼接 — 等效于 Verilog {a, b, c}
Combine(self.a, self.b, self.c)

# 位切片 — 等效于 Verilog a[7:4]
Cut(self.data, 7, 4)

# 信号复制 — 等效于 Verilog {N{a}}
Fanout(self.a, 4)
```

---

## 条件逻辑 (When/Case)

### when/then/otherwise — 三目运算

```python
# 等效于 Verilog: assign out = (sel == 1'b0) ? in1 : in2
self.out += when(Equal(self.sel, UInt(1, 0))).then(self.in1).otherwise(self.in2)
```

### 多条件选择

```python
# 等效于嵌套三目运算
self.out += when(Equal(self.sel, UInt(2, 0))).then(self.in0) \
           .when(Equal(self.sel, UInt(2, 1))).then(self.in1) \
           .when(Equal(self.sel, UInt(2, 2))).then(self.in2) \
           .otherwise(self.in3)
```

### EmptyWhen — 程序化构建条件

当条件数量不固定时，使用 `EmptyWhen` 动态构建：

```python
sel_circuit = EmptyWhen()

for i in range(CHANNEL_NUM):
    sel_circuit.when(Equal(self.sel, UInt(CH_LOG2, i))).then(self.get('in%d' % i))

sel_circuit.otherwise(UInt(DW, 0))    # 默认值

self.out += sel_circuit
```

### Case 选择

```python
# Case(选择信号, {值: 结果, ...}, 默认值)
self.out += Case(self.sel, {0: self.in0, 1: self.in1, 2: self.in2}, self.in3)
```

---

## 参数化设计

UHDL 的一大优势是利用 Python 的表达能力实现参数化设计。以下是一个参数化多路选择器的例子：

```python
from uhdl import *
import math

class DynamicMux(Component):
    def __init__(self, CHANNEL_NUM=4, DW=32):
        super().__init__()

        # 参数检查
        if CHANNEL_NUM * (CHANNEL_NUM - 1) == 0:
            raise Exception('CHANNEL_NUM must be a power of 2')

        CH_LOG2 = int(math.log(CHANNEL_NUM, 2))    # 计算选择信号位宽

        # 根据参数动态创建输入端口
        for i in range(CHANNEL_NUM):
            self.set('in%d' % i, Input(UInt(DW)))   # 动态命名端口

        self.sel = Input(UInt(CH_LOG2))              # 选择信号
        self.out = Output(UInt(DW))                  # 输出

        # 动态构建选择逻辑
        sel_circuit = EmptyWhen()
        for i in range(CHANNEL_NUM):
            sel_circuit.when(Equal(self.sel, UInt(CH_LOG2, i))).then(self.get('in%d' % i))
        sel_circuit.otherwise(UInt(DW, 0))

        self.out += sel_circuit

# 实例化不同配置
mux_4ch = DynamicMux(CHANNEL_NUM=4, DW=32)
mux_8ch = DynamicMux(CHANNEL_NUM=8, DW=16)
```

**关键 API：**

- `self.set(name, io)` — 动态设置端口（用于变量名不固定的场景）
- `self.get(name)` — 动态获取端口

---

## 子模块实例化

在 UHDL 中，一个 Component 可以包含其他 Component 作为子模块：

```python
from uhdl import *

# 先定义子模块
class Adder(Component):
    def __init__(self):
        super().__init__()
        self.in1 = Input(UInt(8))
        self.in2 = Input(UInt(8))
        self.out = Output(UInt(9))
        self.out += self.in1 + self.in2

# 在顶层模块中实例化
class Top(Component):
    def __init__(self):
        super().__init__()
        self.a   = Input(UInt(8))
        self.b   = Input(UInt(8))
        self.sum = Output(UInt(9))

        # 实例化子模块
        self.adder = Adder()

        # 连接：父模块 input → 子模块 input
        self.adder.in1 += self.a
        self.adder.in2 += self.b

        # 连接：子模块 output → 父模块 output
        self.sum += self.adder.out

top = Top()
top.output_dir = 'build'
top.generate_verilog()    # 会同时生成 Top.v 和 Adder.v
```

**连接规则：**

| 场景 | 写法 | 说明 |
|---|---|---|
| 父 input → 子 input | `child.in += parent.in` | 父端口驱动子端口 |
| 子 output → 父 output | `parent.out += child.out` | 子端口驱动父端口 |

`generate_verilog()` 会递归生成所有子模块的 Verilog 文件。

---

## VComponent (导入 Verilog)

UHDL 支持通过 `VComponent` 直接导入现有的 Verilog/SystemVerilog 模块：

```python
from uhdl import *

# 导入 Verilog 模块
vc = VComponent(file='path/to/my_module.v', top='my_module')

# 现在可以像普通 Component 一样使用
class Top(Component):
    def __init__(self):
        super().__init__()
        self.clk = Input(UInt(1))
        self.din = Input(UInt(8))
        self.dout = Output(UInt(8))

        self.sub = VComponent(file='path/to/sub.v', top='sub_module')
        self.sub.clk += self.clk
        self.sub.din += self.din
        self.dout += self.sub.dout
```

**参数说明：**

- `file` — Verilog 源文件路径
- `top` — 顶层模块名称
- `struct_mode` — 结构化类型处理模式：
  - `'auto'`（默认）— 自动识别 struct/enum/union typedef，创建结构化 IO
  - `'packed'` — 将所有端口展平为位向量

VComponent 使用 pyslang 解析 Verilog AST，自动创建与 Verilog 模块端口对应的 Input/Output。

---

## Struct/Enum/Union IO

UHDL 支持 SystemVerilog 的结构化类型，通过 VComponent 自动识别。

### StructIO — 结构体

当 VComponent 遇到 `typedef struct packed` 的端口时，自动创建 `InputStructIO` / `OutputStructIO`：

```python
# 假设 Verilog 中有：
# typedef struct packed { logic [3:0] a; logic signed [7:0] b; logic c; } my_struct_t;
# module struct_user(input my_struct_t s_in, output my_struct_t s_out);

vc = VComponent(file='struct_ports.v', top='struct_user', struct_mode='auto')

# 点号访问字段
ref_a = vc.s_in.a          # StructFieldRef, 位宽 4, 无符号
ref_b = vc.s_in.b          # StructFieldRef, 位宽 8, 有符号

# 获取类型信息
st = vc.s_in.struct_type   # StructType 对象
print(st.width)            # 13 (4+8+1)
print(st.fields)           # {'a': ..., 'b': ..., 'c': ...}

# 类型一致性：同名 typedef 共享同一 StructType 实例
assert vc.s_in.struct_type is vc.s_out.struct_type
```

### EnumIO — 枚举

```python
# 假设 Verilog 中有：
# typedef enum logic [1:0] { IDLE, RUN, DONE, ERR } state_t;
# module enum_user(input state_t state_in, output state_t state_out);

vc = VComponent(file='enum_ports.v', top='enum_user', struct_mode='auto')

# 获取枚举类型
et = vc.state_in.enum_type    # EnumType 对象
print(et.width)               # 2
print(et.members)             # {'IDLE': 0, 'RUN': 1, 'DONE': 2, 'ERR': 3}

# 属性访问成员值
print(et.IDLE)                # 0
print(et.RUN)                 # 1
```

### UnionIO — 联合体

```python
# 假设 Verilog 中有：
# typedef union packed { logic [7:0] byte_val; point_t as_point; } my_union_t;
# module union_user(input my_union_t u_in, output my_union_t u_out);

vc = VComponent(file='union_ports.v', top='union_user', struct_mode='auto')

# 点号访问字段
ref_byte  = vc.u_in.byte_val    # UnionFieldRef, 位宽 8
ref_point = vc.u_in.as_point    # UnionFieldRef, 位宽 8

# 获取类型信息
ut = vc.u_in.union_type         # UnionType 对象
print(ut.width)                 # 8 (最大字段位宽)
```

### 通用操作

所有结构化 IO 类型都支持以下操作：

```python
# 翻转方向：Input ↔ Output
rev = vc.s_in.reverse()      # InputStructIO → OutputStructIO

# 创建同类型副本
tmpl = vc.s_in.template()    # 新的 InputStructIO，保留类型信息

# 类型一致性检查
assert vc.s_in.struct_type is vc.s_out.struct_type  # 同名 typedef 共享实例
```

---

## 连接方式

UHDL 提供三种连接方式，适用于不同场景：

### Assign — 显式赋值

最基本的连接方式：

```python
Assign(self.dout, self.din)    # 等效于 self.dout += self.din
self.out += self.in1 + self.in2  # 直接用 +=
```

### SmartAssign — 智能方向推断

自动根据信号的层次位置推断连接方向：

```python
SmartAssign(self.a, self.sub.in1)    # 自动识别：父 input → 子 input
SmartAssign(self.sub.out, self.b)    # 自动识别：子 output → 父 output
```

SmartAssign 使用 LCA (最近公共祖先) 算法来确定信号的层次关系，自动决定驱动方向。

### perfect_assign — 批量接口连接

当两个组件有大量同名端口需要连接时：

```python
from uhdl import *

# perfect_assign(src, dst, io_list)
# 按名称匹配 io_list 中的端口，在 src 和 dst 之间建立连接
perfect_assign(self.sub1, self.sub2, self.sub1.io_list)
```

这在连接具有相同接口的模块时非常方便，避免逐个端口连接。

---

## 编译与生成

UHDL 提供多种输出方法：

```python
from uhdl import *

class MyDesign(Component):
    def __init__(self):
        super().__init__()
        self.din  = Input(UInt(8))
        self.dout = Output(UInt(8))
        self.dout += self.din

design = MyDesign()

# 设置输出目录
design.output_dir = 'build'

# 方法 1：仅生成 Verilog
design.generate_verilog()          # 生成 .v 文件

# 方法 2：仅生成文件列表
design.generate_filelist()         # 生成 .f 文件

# 方法 3：完整编译（推荐）
design.compile()                   # generate_verilog() + generate_filelist() + run_lint()
```

**推荐使用 `compile()`**，它会：

1. 生成所有 Verilog 文件（包括子模块，递归生成）
2. 生成文件列表 (.f)
3. 运行 Lint 检查

输出目录中会包含所有子模块的 `.v` 文件。

---

## 最佳实践

### 1. 优先使用 `circuit()` 风格

```python
# 推荐
class MyModule(Component):
    def circuit(self):
        self.din = Input(UInt(8))
        self.dout = Output(UInt(8))
        self.dout += self.din
```

`circuit()` 风格更简洁，不需要 `super().__init__()` 样板代码。

### 2. 使用 `compile()` 而非 `generate_verilog()`

```python
# 推荐
design.compile()          # 包含 Lint 检查

# 不推荐（仅开发调试时）
design.generate_verilog()  # 不包含 Lint 检查
```

### 3. 参数化设计使用 `__init__` 参数

```python
class FIFO(Component):
    def __init__(self, DEPTH=16, WIDTH=8):
        super().__init__()
        # 根据参数构建电路...
```

### 4. VComponent 使用 `struct_mode='auto'`

```python
# 推荐：保留类型信息
vc = VComponent(file='module.v', top='mod', struct_mode='auto')

# 仅在不需要类型信息时使用
vc = VComponent(file='module.v', top='mod', struct_mode='packed')
```

### 5. 利用 Python 类继承

```python
class BaseProcessor(Component):
    """处理器基类，定义公共接口"""
    def __init__(self):
        super().__init__()
        self.clk   = Input(UInt(1))
        self.rst_n = Input(UInt(1))
        self.din   = Input(UInt(32))
        self.dout  = Output(UInt(32))

class ALU(BaseProcessor):
    """算术逻辑单元，继承公共接口"""
    def __init__(self):
        super().__init__()
        self.op = Input(UInt(4))
        # 定义 ALU 特有的逻辑...
```

### 6. 动态端口命名使用 `set`/`get`

```python
# 当端口名需要动态生成时
for i in range(N):
    self.set('ch%d_data' % i, Input(UInt(DW)))
    self.set('ch%d_valid' % i, Input(UInt(1)))

# 后续引用
data = self.get('ch0_data')
```
