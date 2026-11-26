# 复杂设计题（第三轮）

## 通用规则
- 时钟 `clk`，异步低有效复位 `rst_n`。所有端口都是扁平向量，第 i 路的字段放在 `[i*W +: W]`。
- 端口名、模块名必须和规格完全一致。评测用的是一个你看不到的 testbench，它逐周期检查 D1，按事务和协议检查 D2。
- 必须可综合，能用 Verilator 5.044 编译，能用 Yosys 0.51 综合。不允许用 `initial` 给寄存器赋初值。

---

## D1 `noc_sw`：N 入 M 出的包交换（输入 FIFO + 路由表 + 每个输出口的按包锁定轮询）

配置：`N`（输入数，>=2），`M`（输出数，>=2），`W`（数据位宽），`D`（每个输入 FIFO 的深度，>=2，不一定是 2 的幂），`TW`（目标 ID 位宽），路由表 `ROUTE[t]`（t = 0..2^TW-1，取值 0..M-1）。记 `SW = max(1, clog2(N))`。

| 端口 | 方向 | 位宽 |
|---|---|---|
| clk, rst_n | in | 1 |
| in_vld, in_last | in | N |
| in_rdy | out | N |
| in_tgt | in | N*TW |
| in_data | in | N*W |
| out_vld, out_last | out | M |
| out_rdy | in | M |
| out_data | out | M*W |
| out_src | out | M*SW（第 o 个输出当前这一拍来自哪个输入） |

一个 flit 是 (tgt, data, last)。包由若干个 flit 组成，最后一个 flit 的 last=1。testbench 保证同一个包内所有 flit 的 tgt 相同，并且同一个输入上的包是一个接一个连续发送的。

行为必须做到逐周期精确：

**输入 FIFO**

每个输入 i 有一个深度为 D 的 FIFO，记它的占用数为 `cnt_i`（寄存器）。
- `in_rdy[i] = (cnt_i < D)`，只由寄存器状态决定，不看同一周期的出队。
- 当 `in_vld[i] && in_rdy[i]` 时入队。
- 没有旁路：第 t 周期写入的 flit，最早在 t+1 周期出现在队头。
- 队头有效记为 `hv_i = (cnt_i > 0)`，队头 flit 记为 `(tgt_i, data_i, last_i)`，队头的路由记为 `r_i = ROUTE[tgt_i]`。
- 队头 flit 只在它在某个输出口完成握手的那个周期出队。同一周期可以同时入队和出队。

**输出口 o**

每个输出口有三个寄存器：`locked_o`、`lidx_o`、`ptr_o`，复位值都为 0。
- `req_o[i] = hv_i && (r_i == o)`
- `sel_o = locked_o ? lidx_o : 轮询选择`。轮询选择的规则是：从 `ptr_o` 开始依次往后找，取第一个 `req_o[i] = 1` 的 i；没有请求时取 `ptr_o`。
- `out_vld[o] = locked_o ? req_o[lidx_o] : |req_o`
- `out_data[o]`、`out_last[o]` 取自输入 `sel_o` 的队头，`out_src[o] = sel_o`。
- 握手条件为 `out_vld[o] && out_rdy[o]`。握手时输入 `sel_o` 的队头出队。
- 如果 `out_vld[o] && !(out_rdy[o] && out_last[o])`：下一周期 `locked_o = 1`，`lidx_o = sel_o`。
- 如果 `out_vld[o] && out_rdy[o] && out_last[o]`：下一周期 `locked_o = 0`，`ptr_o = (sel_o + 1) mod N`。

配置：
- A：`{"N":4,"M":3,"W":8,"D":4,"TW":3,"route":[0,1,2,0,1,2,2,1]}`，文件 `specs/d1_cfgA.json`
- B：`{"N":5,"M":4,"W":16,"D":3,"TW":2,"route":[3,0,2,1]}`，文件 `specs/d1_cfgB.json`

传参方式：
- **SV**：模块参数为 `N, M, W, D, TW` 和 `ROUTE`。`ROUTE` 的位宽是 `(2**TW)*8`，第 t 项放在 `[t*8 +: 8]`。testbench 用参数覆盖的方式传入配置。
- **UHDL**：运行 `gen.py --out <dir> --config <json>`，生成 `<dir>/noc_sw.v` 和 `filelist.f`。

---

## D2 `axil_regs`：寄存器表驱动的 AXI4-Lite 从设备

配置 JSON：`{"AW":8,"regs":[{"name":"ctrl","offset":0,"access":"RW","reset":1}, ...]}`
- access 有三种：`RW`、`RO`、`W1C`。
- 所有寄存器都是 32 位，offset 是 4 的倍数且互不重叠。
- RO 寄存器没有 reset 字段。

**AXI 端口**（AXI4-Lite，`s_axi_` 前缀）：

| 端口 | 方向 | 位宽 |
|---|---|---|
| s_axi_awvalid / s_axi_wvalid / s_axi_bready / s_axi_arvalid / s_axi_rready | in | 1 |
| s_axi_awready / s_axi_wready / s_axi_bvalid / s_axi_arready / s_axi_rvalid | out | 1 |
| s_axi_awaddr, s_axi_araddr | in | AW |
| s_axi_wdata | in | 32 |
| s_axi_wstrb | in | 4 |
| s_axi_bresp, s_axi_rresp | out | 2 |
| s_axi_rdata | out | 32 |
| irq | out | 1 |

**每个寄存器对应的硬件侧端口**（`<name>` 是表里的寄存器名）：
- RW：输出 `<name>_o[31:0]`，即寄存器当前值。
- RO：输入 `<name>_i[31:0]`。读这个寄存器时返回该输入当前的值。
- W1C：输入 `<name>_set[31:0]`，每个周期把其中为 1 的位置位，下一周期生效；输出 `<name>_o[31:0]`，即当前状态。

**行为**：
- 地址比较 `addr[AW-1:2]` 和 `offset[AW-1:2]`，低 2 位忽略。
- **写**：
  - AW 和 W 两个通道各自独立接收：先后顺序任意，也可以同一周期到达。
  - 两者都收到之后执行写操作，再给出 `bvalid`。
  - RW：wstrb 为 1 的字节被替换为 wdata 对应的字节。
  - W1C：在 wstrb 为 1 的字节里，wdata 为 1 的位被清零；如果同一周期该位也被 set，set 优先。
  - 写的是 RO 地址或未映射地址时，不产生任何效果，bresp 返回 SLVERR (2)；其余情况返回 OKAY (0)。
  - 同一时间最多只有一个写事务在进行：在 B 完成握手之前，从设备可以拉低 awready/wready。
- **读**：AR 握手之后给出 `rvalid`。rdata 是寄存器的值（RO 寄存器返回输入值）。未映射地址返回 rdata=0 和 SLVERR，其余情况返回 OKAY。
- **AXI 规则**：bvalid/rvalid 拉高之后，必须保持到对应的 ready 为止，期间 resp 和 data 不能变。
- **时序要求**：
  - `<name>_o` 必须在 bvalid 第一次拉高的那个周期（或更早）就反映出这次写入的结果。
  - 在主机及时给出 ready 的前提下，每个事务从请求到完成不超过 16 个周期。
- **中断**：`irq = |{所有 W1C 寄存器的所有位}`，可以是组合输出，也可以晚 1 个周期。
- **复位**：RW 和 W1C 寄存器恢复为表里的 reset 值。

**testbench 保证**：
- 读事务和写事务不会同时在进行。
- 只有在没有任何事务进行的空闲窗口里，RO 输入才会变化，`_set` 才会出现脉冲。

**配置**：
- A：`specs/d2_cfgA.json`
- B：`specs/d2_cfgB.json`

**交付方式**（两种语言都一样，因为端口随配置变化）：运行 `gen.py --out <dir> --config <json>`，生成 `<dir>/axil_regs.v`（UHDL）或 `<dir>/axil_regs.sv`（SV），外加 `filelist.f`。
- **SV 一方**：怎么从配置得到 SV 自己决定。可以用 Python 模板生成 SV 文本，也可以写一个通用的参数化 SV 核心，再配一层薄的生成包装；但最终交付的必须是 SV 源码。
- **UHDL 一方**：必须用 UHDL 描述电路。
