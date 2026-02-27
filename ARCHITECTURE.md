# UHDL 架构文档

## 项目概述

UHDL (Universal Hardware Description Language) 是一个基于 Python 的硬件描述语言框架，能够生成可综合的 Verilog 代码。它利用 Python 的语法特性（运算符重载、`__setattr__`、类继承）来自然地表达硬件电路结构，使工程师可以用 Python 的表达能力来描述参数化、可复用的数字电路设计。

核心设计理念：

- **`=` 创建元素**：利用 `__setattr__` 魔术方法，在 Component 中用 `self.xxx = Input(...)` 自动命名并注册端口
- **`+=` 连接电路**：利用 `__iadd__` 运算符重载，用 `self.out += expr` 表示信号赋值
- **表达式树**：利用 `__add__`、`__sub__` 等运算符重载，自动构建电路表达式树
- **树形层次结构**：每个信号和组件都有 `name` 和 `father`，形成与 Verilog module 层次对应的树

---

## 目录结构

```
uhdl/
├── uhdl/
│   ├── __init__.py              # 包入口，re-exports core + extension
│   ├── core/                    # 核心 HDL 框架
│   │   ├── __init__.py          # 公开 API 导出 (__all__)
│   │   ├── Root.py              # 基础树节点 (~148 行)
│   │   ├── Variable.py          # IO 类型、表达式、值 (~2740 行)
│   │   ├── Component.py         # 模块容器、Verilog 代码生成 (~755 行)
│   │   ├── VComponent.py        # 通过 pyslang 导入 Verilog (~368 行)
│   │   ├── Operator.py          # 运算符函数式 API 封装 (~674 行)
│   │   ├── Function.py          # SmartAssign, Assign, LCA 等 (~223 行)
│   │   ├── types.py             # 类型描述符 (TypeKernel, StructType, EnumType, UnionType) (~367 行)
│   │   ├── TemplateIP.py        # 模板 IP 支持
│   │   ├── Config.py            # 配置管理
│   │   ├── Terminal.py          # 日志/终端输出
│   │   ├── MultiFileCoop.py     # 多文件协作
│   │   ├── Lint.py              # Lint 基础设施
│   │   ├── AreaCalculator.py    # 面积估算
│   │   ├── BasicFunction.py     # 基础工具函数 (join_name 等)
│   │   └── UHDLException.py     # 异常定义
│   ├── extension/
│   │   ├── __init__.py          # 扩展模块入口
│   │   └── PerfectAssign.py     # 智能接口连接 (~304 行)
│   └── Demo/                    # 示例项目
│       ├── Bitfield/
│       ├── Crossbar/
│       ├── DynamicPipeline/
│       ├── FIR/
│       ├── lwnoc/
│       ├── lwnoc2/
│       ├── RomFromFile/
│       └── SparseSwitch/
├── test/                        # 测试套件 (190 项, 178 通过, 12 跳过)
├── docs/                        # Sphinx 文档
└── README.md
```

---

## 核心类层次结构

### 信号与表达式层次

```
Root (Root.py)
│   基础树节点。提供 name、father、层次遍历 (father_until_component 等)。
│
├── Variable (Variable.py)
│   所有信号的基类。提供 attribute (类型信息)、verilog_def 等属性。
│   │
│   ├── IOSig — 标量 IO 端口基类
│   │   ├── Input  (使用 InputLikeMixin)    — 输入端口
│   │   ├── Output (使用 OutputLikeMixin)   — 输出端口
│   │   └── Inout                           — 双向端口
│   │
│   ├── Wire      — 内部连线
│   ├── Reg       — 寄存器 (带时钟/复位)
│   └── Parameter — 模块参数
│
├── StructIO — 结构体 IO 基类
│   ├── InputStructIO  (InputLikeMixin)    — 结构体输入
│   └── OutputStructIO (OutputLikeMixin)   — 结构体输出
│
├── EnumIO — 枚举 IO 基类
│   ├── InputEnumIO  (InputLikeMixin)      — 枚举输入
│   └── OutputEnumIO (OutputLikeMixin)     — 枚举输出
│
├── UnionIO — 联合体 IO 基类
│   ├── InputUnionIO  (InputLikeMixin)     — 联合体输入
│   └── OutputUnionIO (OutputLikeMixin)    — 联合体输出
│
├── Bundle    — IO 分组
├── IOGroup   — IO 组
│
└── Value — 表达式层次 (所有运算结果的基类)
    ├── Add, Sub, Mul                          — 算术运算
    ├── And, Or                                — 逻辑运算
    ├── Greater, Less, GreaterEqual,           — 比较运算
    │   LessEqual, Equal, NotEqual
    ├── BitAnd, BitOr, BitXor, BitXnor         — 位运算
    ├── SelfOr, SelfAnd, SelfXor, SelfXnor     — 归约运算
    ├── Inverse, Not                           — 一元运算
    ├── Combine                                — 拼接 (concatenation)
    ├── Cut                                    — 位切片 (bit slicing)
    ├── When / EmptyWhen / Case                — 条件选择
    └── Fanout                                 — 信号复制
```

### 组件层次

```
Component (Component.py)
│   模块容器。管理 IO 列表、内部信号、子模块实例、Verilog 代码生成。
│
├── VComponent (VComponent.py)
│   通过 pyslang 解析导入 Verilog/SystemVerilog 模块。
│
└── TemplateIP (TemplateIP.py)
    模板 IP 支持。
```

### Mixin 类

- **InputLikeMixin**：为 Input、InputStructIO、InputEnumIO、InputUnionIO 提供输入方向行为
- **OutputLikeMixin**：为 Output、OutputStructIO、OutputEnumIO、OutputUnionIO 提供输出方向行为

这两个 Mixin 决定了 `+=` 运算符在连接时的方向推断逻辑。

---

## 类型系统

类型描述符定义在 `core/types.py` 中，为所有信号提供类型信息。

### TypeKernel

所有类型的基类，定义了 `width` 属性。

- **UInt(width)** — 无符号整数类型，指定位宽
- **SInt(width)** — 有符号整数类型，指定位宽

### StructType

结构体类型描述符。

- 包含字段信息 (`fields` 字典)、包名 (`package`)、类型名
- 通过 `StructType.get_or_create()` 实现单例注册，保证同名 typedef 共享同一实例
- `width` 属性为所有字段位宽之和

### StructConstant

作为 StructIO 的 `attribute` 属性，携带对应 StructType 的引用。

### EnumType

枚举类型描述符。

- 包含成员字典 (`members`: name → int value)、位宽、符号性
- 支持属性访问成员值：`enum_type.IDLE` 返回对应整数值
- 通过注册机制保证同名 typedef 共享同一实例

### EnumConstant

作为 EnumIO 的 `attribute` 属性，携带对应 EnumType 的引用。

### UnionType

联合体类型描述符。

- 包含字段信息 (`fields` 字典)
- `width` 属性为所有字段位宽的最大值
- 字段可以嵌套 struct 类型信息

### UnionConstant

作为 UnionIO 的 `attribute` 属性，携带对应 UnionType 的引用。

---

## Python Magic 机制

UHDL 的核心设计依赖于 Python 的几个魔术方法。

### `Root.__setattr__` — 自动命名

当一个 `Root` 子类实例被赋值给另一个 `Root` 实例的属性时，`__setattr__` 会自动：

1. 设置被赋值对象的 `name` 为属性名
2. 设置被赋值对象的 `father` 为宿主对象

```python
self.in1 = Input(UInt(1))
# 等效于：
# tmp = Input(UInt(1))
# tmp.name = 'in1'
# tmp.father = self
```

这就是为什么 `self.in1 = Input(UInt(1))` 能够自动将端口命名为 `"in1"` 并注册到 Component 中。

### `Variable.__iadd__` (`+=`) — 电路赋值

`+=` 运算符被重载为电路连接操作：

```python
self.out += self.in1 + self.in2
# 等效于 Verilog: assign out = in1 + in2
```

`+=` 将右侧表达式连接到左侧信号的输入端。这是 UHDL 中最核心的操作。

### 运算符重载 — 表达式树

`Value` 及其子类重载了 Python 运算符，自动构建表达式树：

| Python 运算符 | UHDL 表达式 | Verilog 等效 |
|---|---|---|
| `a + b` | `Add(a, b)` | `a + b` |
| `a - b` | `Sub(a, b)` | `a - b` |
| `a * b` | `Mul(a, b)` | `a * b` |
| `a & b` | `BitAnd(a, b)` | `a & b` |
| `a \| b` | `BitOr(a, b)` | `a \| b` |
| `a ^ b` | `BitXor(a, b)` | `a ^ b` |

### `=` vs `+=` — 核心区别

| 操作 | 含义 | 示例 |
|---|---|---|
| `=` | 创建并命名元素 | `self.in1 = Input(UInt(1))` |
| `+=` | 连接电路信号 | `self.out += self.in1 + self.in2` |

这是 UHDL 最根本的设计理念：**`=` 声明，`+=` 连接**。

---

## 导入关系

经过重构后，模块间的导入关系为单向链，消除了循环依赖：

```
types.py (独立，无外部依赖)
    ↑
    │ import
    │
Variable.py ←── Operator.py
    ↑               ↑
    │ lazy import    │ import
    │               │
Component.py ←── Function.py
    ↑
    │ import
    │
VComponent.py
```

### 关键导入策略

- **Component → Variable → Root**：单向导入链，无循环
- **Variable.py → Component**：使用方法级惰性导入 (`from .Component import Component`)，共 5 处
- **Root.py → Component**：在 `father_until_component()` 方法中使用惰性导入
- **types.py**：完全独立模块，被 Variable.py 导入，无反向依赖
- **`uhdl/__init__.py`**：通过 `from .core import *` 和 `from .extension import *` 统一导出

---

## 代码生成流水线

```
用户定义 Component 子类
        │
        ▼
    实例化 Component
        │
        ▼
component.compile()
    ├── generate_verilog()    ──→  .v 文件
    ├── generate_filelist()   ──→  .f 文件列表
    └── run_lint()            ──→  Lint 检查
```

### 详细流程

1. **用户定义** Component 子类，在 `__init__` 或 `circuit()` 中声明 IO 和逻辑
2. **实例化** Component，触发 `__setattr__` 完成信号注册和层次构建
3. **调用 `compile()`**，依次执行：
   - `generate_verilog()` — 生成 Verilog 源文件
   - `generate_filelist()` — 生成文件列表 (.f)
   - `run_lint()` — 运行 Lint 检查
4. **`generate_verilog()`** 内部通过 `verilog_def` 属性收集：
   - `io_list` — 所有 IO 端口声明
   - `inter_sig_list` — 内部信号 (Wire/Reg) 声明
   - `lvalue_list` — 所有赋值语句 (assign / always 块)
   - `component_list` — 子模块实例化
5. **每个 Variable/Expression** 提供：
   - `verilog_def_as_list` — Verilog 端口/信号声明
   - `verilog_assignment` — Verilog 赋值语句
   - `verilog_inst` — Verilog 模块实例化代码
6. **输出**：递归生成所有子模块的 `.v` 文件和 `.f` 文件列表

---

## 连接模型

UHDL 提供多层次的连接 API，从底层到高层：

### Assign — 显式赋值

```python
Assign(lhs, rhs)
# 等效于
lhs += rhs
```

最基础的连接操作，直接将 `rhs` 的值赋给 `lhs`。

### SmartAssign — 智能方向推断

```python
SmartAssign(op1, op2)
```

基于信号在层次树中的位置，自动推断连接方向：

- 使用 **LCA (Lowest Common Ancestor)** 算法确定两个信号的最近公共祖先
- 根据信号相对于 LCA 的位置和 InputLikeMixin/OutputLikeMixin 类型自动决定谁是驱动端、谁是被驱动端
- 典型场景：父模块 input → 子模块 input，子模块 output → 父模块 output

### PerfectAssign — 批量接口连接

```python
# 单个连接
single_assign(op1, op2)

# 批量按名称匹配连接
perfect_assign(src, dst, io_list)
```

- `single_assign` 在 SmartAssign 基础上增加了 VComponent 感知能力
- `perfect_assign` 通过端口名称匹配，批量连接两个组件之间的同名端口
- 支持所有 IO 类型：标量 IO、StructIO、EnumIO、UnionIO

### InputLikeMixin / OutputLikeMixin

这两个 Mixin 类决定了 `+=` 运算符的方向行为：

- **InputLikeMixin**：被 Input、InputStructIO、InputEnumIO、InputUnionIO 使用
- **OutputLikeMixin**：被 Output、OutputStructIO、OutputEnumIO、OutputUnionIO 使用

连接规则：

| 场景 | 连接方向 |
|---|---|
| 父 Input → 子 Input | 父端口驱动子端口 |
| 子 Output → 父 Output | 子端口驱动父端口 |
| 同层 Output → Input | Output 驱动 Input |

---

## VComponent (Verilog 导入)

`VComponent` 使用 [pyslang](https://github.com/MikePopoloski/pyslang) 解析 Verilog/SystemVerilog 源文件，自动创建对应的 UHDL 端口。

### 工作流程

1. 调用 pyslang 解析 Verilog 文件，获取 AST
2. 遍历顶层模块的端口声明
3. 根据端口方向创建 Input/Output/Inout
4. 检测 `typedef struct packed`、`typedef enum`、`typedef union packed` 端口

### struct_mode 参数

| 模式 | 行为 |
|---|---|
| `'auto'`（默认） | 自动识别 struct/enum/union typedef，创建对应的结构化 IO 类型 |
| `'packed'` | 将所有端口展平为位向量，不保留类型信息 |

### 结构化端口创建

在 `struct_mode='auto'` 模式下：

- **typedef struct packed** → `InputStructIO` / `OutputStructIO`
  - 支持点号字段访问：`vc.s_in.field_a` 返回 `StructFieldRef`
  - 字段保留位宽和符号性信息
  - 同名 typedef 共享 `StructType` 单例

- **typedef enum** → `InputEnumIO` / `OutputEnumIO`
  - 通过 `enum_type` 属性访问 `EnumType` 对象
  - 支持成员属性访问：`enum_type.IDLE`

- **typedef union packed** → `InputUnionIO` / `OutputUnionIO`
  - 支持点号字段访问：`vc.u_in.byte_val` 返回 `UnionFieldRef`
  - 联合体字段可以嵌套 struct 类型

### 通用操作

所有结构化 IO 类型都支持：

- `.reverse()` — 翻转方向 (Input ↔ Output)
- `.template()` — 创建同类型副本
- 类型一致性检查 — 连接时验证 typedef 身份

---

## 扩展系统

扩展模块位于 `uhdl/extension/`，通过 `uhdl/__init__.py` 中的 `from .extension import *` 自动导出。

### PerfectAssign.py

提供智能接口连接功能：

#### `single_assign(op1, op2)`

连接两个 IO 端口，具备：
- 方向自动推断
- VComponent 感知（处理 VComponent 端口的特殊连接逻辑）
- 支持标量 IO、StructIO、EnumIO、UnionIO

#### `perfect_assign(src, dst, io_list)`

批量接口连接：
- 遍历 `io_list`，按端口名称在 `src` 和 `dst` 中查找匹配端口
- 对每对匹配的端口调用 `single_assign`
- 适用于将两个具有相同接口的组件快速连接

#### IO 类型识别

PerfectAssign 内部使用以下函数识别端口类型：

- `_is_input_like(io)` — 检测 Input、InputStructIO、InputEnumIO、InputUnionIO
- `_is_output_like(io)` — 检测 Output、OutputStructIO、OutputEnumIO、OutputUnionIO
- `_is_io_like(io)` — 检测所有 IO 类型

---

## 公开 API

以下是 `core/__init__.py` 中 `__all__` 导出的完整 API 列表：

### 组件

| API | 说明 |
|---|---|
| `Component` | 模块容器基类 |
| `VComponent` | Verilog 导入组件 |
| `TemplateIP` | 模板 IP |
| `Circuit` | `Root` 的别名 |

### IO 类型

| API | 说明 |
|---|---|
| `Input` | 输入端口 |
| `Output` | 输出端口 |
| `Inout` | 双向端口 |
| `Wire` | 内部连线 |
| `Reg` | 寄存器 |
| `Parameter` | 模块参数 |
| `IOGroup` | IO 组 |
| `Bundle` | IO 分组 |

### 类型描述符

| API | 说明 |
|---|---|
| `UInt` | 无符号整数类型 |
| `SInt` | 有符号整数类型 |
| `AnyConstant` | 任意类型常量 |

### 结构化 IO

| API | 说明 |
|---|---|
| `InputStructIO` / `OutputStructIO` | 结构体 IO |
| `InputEnumIO` / `OutputEnumIO` | 枚举 IO |
| `InputUnionIO` / `OutputUnionIO` | 联合体 IO |
| `StructType` / `StructConstant` / `StructFieldRef` | 结构体类型系统 |
| `EnumType` / `EnumConstant` | 枚举类型系统 |
| `UnionType` / `UnionConstant` / `UnionFieldRef` | 联合体类型系统 |

### 算术运算符

| API | Verilog 等效 |
|---|---|
| `Add` | `+` |
| `Sub` | `-` |
| `Mul` | `*` |

### 比较与逻辑运算符

| API | Verilog 等效 |
|---|---|
| `Equal` | `==` |
| `NotEqual` | `!=` |
| `Greater` | `>` |
| `Less` | `<` |
| `GreaterEqual` | `>=` |
| `LessEqual` | `<=` |
| `And` | `&&` |
| `Or` | `\|\|` |

### 位运算符

| API | Verilog 等效 |
|---|---|
| `BitAnd` | `&` |
| `BitOr` | `\|` |
| `BitXor` | `^` |
| `BitXnor` | `~^` |

### 一元与归约运算符

| API | Verilog 等效 |
|---|---|
| `Inverse` | `~` (按位取反) |
| `Not` | `!` (逻辑非) |
| `SelfOr` | `\|a` (归约或) |
| `SelfAnd` | `&a` (归约与) |
| `SelfXor` | `^a` (归约异或) |
| `SelfXnor` | `~^a` (归约同或) |

### 组合与选择

| API | 说明 |
|---|---|
| `Combine` | 信号拼接 `{a, b, ...}` |
| `Cut` | 位切片 `a[h:l]` |
| `When` / `EmptyWhen` | 条件选择 (三目运算) |
| `Case` | Case 选择 |
| `Fanout` | 信号复制 `{N{a}}` |
| `BitMask` | 位掩码 |

### 列表运算符

| API | 说明 |
|---|---|
| `BitXnorList` / `BitXorList` | 多操作数位运算 |
| `BitOrList` / `BitAndList` | 多操作数位运算 |
| `OrList` / `AndList` | 多操作数逻辑运算 |

### 连接函数

| API | 说明 |
|---|---|
| `Assign` | 显式赋值 |
| `SmartAssign` | 智能方向推断赋值 |
| `assign` | `Assign` 的小写别名 |
| `smart_assign` | `SmartAssign` 的小写别名 |

### 工具

| API | 说明 |
|---|---|
| `Config` | 配置管理 |
| `MultiFileExec` | 多文件执行 |
| `MultiFileScope` | 多文件作用域 |
| `Unpack` | 信号解包 |
| `Linkable` / `Exclude` | 连接辅助 |
| `get_circuit` / `set_circuit` | 电路上下文管理 |
| `UHDLException` | 异常基类 |

---

## 测试

项目包含完整的测试套件：

- **总计**：190 项测试
- **通过**：178 项
- **跳过**：12 项
- **失败**：0 项

测试覆盖：基本 IO、寄存器、表达式运算、条件逻辑、Component 定义、VComponent 导入、StructIO/EnumIO/UnionIO、嵌套结构体、类型系统、组合集成测试等。
