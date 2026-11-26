# UHDL 设计哲学与在 lwnoc 中的演变（2026-11-04）

## UHDL 的三层能力（按时间）
1. 2020 起，Python 嵌入式 HDL（类似 Chisel / MyHDL）
   - 基本元素：Component / Input / Output / Wire / Reg / when / Case / 表达式，用 `+=` 连接，输出可读的 Verilog。
   - Component 通过 inspect 捕获构造参数，再自动生成模块名（`_PARAM._caculate_name`），所以“一组参数 = 一个模块”。
   - Bundle 用来表示带字段的接口，支持 reverse()。
2. 2023-07 起，VComponent：用 slang 解析手写的 Verilog，当黑盒例化。
   - 配套的集成语法糖：expose_io、get_io（正则匹配）、perfect_assign（按 AXI 信号名表）。
3. 2025-10 起，TemplateIP / Template Component（只在 slangv8 / ai_driven 分支，master 上没有）。
   - 做法：手写 IP 加前缀复制一份 + 用宏 yaml 配置，以此解决“多实例、多配置”。

## lwnoc 原型（uhdl/Demo/lwnoc, lwnoc2，2023）
- 拓扑即电路：Network / Node 描述拓扑，传播 reachable_tgt_id / src_id 来推导路由。
- DArb / DDec 根据 `num = len(node.tgt_list)` 直接生成恰好 N 入的仲裁器和译码器，内部用 age matrix 仲裁，按包锁定。
- BasicHdsk 是 Bundle，字段为 vld / rdy / head / tail / pld / src_id / tgt_id / txn_id。

## 生产版的偏移
- RTL 改成手写 SV，UHDL 只剩“导入 + 连线 + 唯一化”的作用。
- 原型的优势随之丢失：
  - 导入时只能拿到扁平端口，Bundle 结构没了，topo 层只好用正则去“猜”接口。
  - `Bundle.connect()` 本身是 `pass`；`as_list()` 按声明顺序排，再用 zip 配对，等于按位置连线。
  - 不能直接生成 N 路的模块了，结果多出 35 个 wrap 文件。
  - ID 传播被注释掉，路由改成手写。

## 初衷的价值评估
| 初衷 | 现在是否有价值 | 重写时 |
|---|---|---|
| 从拓扑推导路由、ID、地址、路数 | 很高，而且现在正缺 | 保留，作为核心 |
| 带类型的接口（Bundle） | 高，但 UHDL 的实现不完整 | 保留理念，重做实现 |
| 用 Python 写电路逻辑（Reg / when） | 对 lwnoc 来说下降了：SV 的参数化已经够用，低功耗 / RAS / CDC 的逻辑用 SV 写更容易做 DV 和 review | 降级为可选 |
| 用 slang 解析已有 RTL | 有价值，可以用来校验端口、提取接口 | 直接用 pyslang |
| 自动唯一化（参数→模块名，前缀复制） | 是现在问题的来源之一 | 交给构建流程，并且只在确实需要时做 |
