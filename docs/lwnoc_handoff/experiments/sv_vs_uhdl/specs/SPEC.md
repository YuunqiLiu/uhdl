# SV vs UHDL 对比实验：题目规格

## 通用规则（所有题目）
- 时钟 `clk`，异步低有效复位 `rst_n`。
- 所有端口都是扁平向量，不用 packed 多维数组、struct 或 interface。第 i 路的字段放在 `[i*W +: W]`。
- 端口名、参数名、模块名必须和规格完全一致。评测用的是一个你看不到的 testbench，名字不一致就会编译失败。
- 必须可综合，能通过 Verilator 5.044 编译，也能被 Yosys 0.51 综合。
- 不允许用 `initial` 块给寄存器赋初值，复位值都通过 `rst_n` 给出。

---

## P1 `rr_arb`：N 路轮询仲裁器

参数：`N`（N >= 2，不一定是 2 的幂）

| 端口 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| clk, rst_n | in | 1 | |
| req | in | N | 请求 |
| ack | in | 1 | 本周期的授权被接受 |
| gnt | out | N | one-hot 授权，组合输出；没有请求时为 0 |
| gnt_vld | out | 1 | `= \|req` |

行为：
- 内部有一个优先级指针 `ptr`，取值 0..N-1，复位时为 0。
- 组合逻辑：从下标 `ptr` 开始，依次检查 ptr, ptr+1, ..., N-1, 0, ..., ptr-1，授权给第一个有请求的位置。
- 当 `ack && gnt_vld` 时，下一个周期 `ptr <= (被授权的下标 + 1) mod N`；否则 ptr 保持不变。

测试参数：N=4，N=7

---

## P2 `sync_fifo`：同步 FIFO（show-ahead）

参数：`WIDTH`（>=1），`DEPTH`（>=2，不一定是 2 的幂）

| 端口 | 方向 | 位宽 |
|---|---|---|
| clk, rst_n | in | 1 |
| wr_en | in | 1 |
| wr_data | in | WIDTH |
| full | out | 1 |
| rd_en | in | 1 |
| rd_data | out | WIDTH |
| empty | out | 1 |
| count | out | CW = $clog2(DEPTH+1) |

行为：
- 只在 `wr_en && !full` 时写入。满的时候即使同时有读，写也被忽略。
- 只在 `rd_en && !empty` 时读出。空的时候即使同时有写，读也被忽略，写照常进行。
- show-ahead：只要 `!empty`，`rd_data` 就是当前最老的那一项，可以由寄存器或存储组合输出。读出生效的下一周期切换到下一项。`empty` 时 rd_data 的值不检查。
- `count` 是当前存放的项数，`full = (count == DEPTH)`，`empty = (count == 0)`。
- 复位后为空。

测试参数：(WIDTH=8, DEPTH=5)，(WIDTH=16, DEPTH=4)

---

## P3 `pkt_mux`：N 入 1 的包多路器（按包锁定，轮询）

参数：`N`（>=2），`W`（数据位宽，>=1）

| 端口 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| clk, rst_n | in | 1 | |
| in_vld | in | N | |
| in_rdy | out | N | |
| in_data | in | N*W | 第 i 路数据在 `[i*W +: W]` |
| in_last | in | N | 包的最后一拍 |
| out_vld | out | 1 | |
| out_rdy | in | 1 | |
| out_data | out | W | |
| out_last | out | 1 | |

一个包是若干拍，最后一拍的 `last=1`。输入端保证 valid 稳定：vld 一旦拉高，在握手之前不会撤销，数据也保持不变。

行为（纯组合通路，0 延迟）：
- 内部状态：`locked`、`lock_idx`、轮询指针 `ptr`（复位时 locked=0，ptr=0）。
- 选择：`sel = locked ? lock_idx : 轮询选择`。轮询选择规则和 P1 相同：从 ptr 开始，找第一个 `in_vld` 为 1 的输入。
- `out_vld = locked ? in_vld[lock_idx] : |in_vld`；out_data 和 out_last 取自 sel 那一路；`in_rdy[i] = out_rdy && out_vld && (i == sel)`，其余各路为 0。
- 锁定：如果本周期 `out_vld && !(out_rdy && out_last)`，下一周期 `locked=1`，`lock_idx=sel`。也就是说，从包的第一拍出现在输出上开始锁定，包括被反压的情况。
- 解锁：如果本周期 `out_vld && out_rdy && out_last`，下一周期 `locked=0`，同时 `ptr <= (sel + 1) mod N`。
- 其他情况保持不变。

测试参数：(N=3, W=8)，(N=5, W=16)

---

## P4 `addr_router`：1 出 M 的地址路由器（带 DECERR 端口）

配置：M 个输出端口；一张地址区间表，每一项是 (base, size, port)。区间之间互不重叠；多个区间可以映射到同一个端口；`base + size <= 2^AW`，区间可以一直延伸到地址空间顶端，所以计算区间上界时要注意溢出。

| 端口 | 方向 | 位宽 |
|---|---|---|
| clk, rst_n | in | 1（纯组合模块，也必须保留这两个端口） |
| in_vld | in | 1 |
| in_rdy | out | 1 |
| in_addr | in | AW |
| in_data | in | DW |
| out_vld | out | M |
| out_rdy | in | M |
| out_addr | out | M*AW |
| out_data | out | M*DW |
| err_vld | out | 1 |
| err_rdy | in | 1 |
| err_addr | out | AW |

行为（纯组合）：
- 命中条件：`base <= in_addr < base + size`。
- 命中某个区间时，`out_vld[port] = in_vld`，其余输出的 vld 为 0，`err_vld = 0`，`in_rdy = out_rdy[port]`。
- 一个区间都没命中时，`err_vld = in_vld`，所有 out_vld 为 0，`in_rdy = err_rdy`。
- out_addr、out_data、err_addr 可以直接广播 in_addr 和 in_data；testbench 只在对应的 vld 为 1 时检查这些值。

两组测试配置：

配置 A：M=3, AW=16, DW=8
| base | size | port |
|---|---|---|
| 0x0000 | 0x1000 | 0 |
| 0x1000 | 0x0800 | 1 |
| 0x2000 | 0x2000 | 0 |
| 0x8000 | 0x8000 | 2 |

配置 B：M=2, AW=12, DW=4
| base | size | port |
|---|---|---|
| 0x100 | 0x100 | 1 |
| 0x400 | 0x400 | 0 |
| 0x900 | 0x700 | 1 |

配置方式：
- **SV**：模块参数为 `M, AW, DW, NR`（区间数），以及
  - `REGION_BASE`，位宽 NR*AW，第 i 个区间在 `[i*AW +: AW]`
  - `REGION_SIZE`，位宽 NR*(AW+1)，第 i 个在 `[i*(AW+1) +: AW+1]`。多 1 位是为了能表示 2^AW
  - `REGION_PORT`，位宽 NR*8，第 i 个在 `[i*8 +: 8]`

  testbench 会用参数覆盖的方式传入配置 A 和配置 B。
- **UHDL**：配置用 JSON 文件给出，格式如下，生成脚本读取它：
  `{"M":3,"AW":16,"DW":8,"regions":[{"base":0,"size":4096,"port":0}, ...]}`

---

## P5 `pchan_ctrl`：P-channel 低功耗控制器（控制逻辑为主）

参数：`CW`（未完成事务计数器的位宽，>=2）、`TIMEOUT`（静默等待的超时周期数，>=1）、`WAKE_CYC`（上电等待周期数，>=1）

功耗状态编码（2 bit）：`0 = OFF`，`1 = RET`，`2 = ON`，`3 = 非法`。数值越大，功耗越高。

| 端口 | 方向 | 位宽 | 说明 |
|---|---|---|---|
| clk, rst_n | in | 1 | |
| preq | in | 1 | P-channel 请求 |
| pstate | in | 2 | 请求的目标状态，preq 为高期间保持不变 |
| paccept | out | 1 | 寄存器输出 |
| pdeny | out | 1 | 寄存器输出 |
| pactive | out | 1 | 组合输出：`outstanding != 0` |
| cur_state | out | 2 | 寄存器输出，当前功耗状态，复位为 ON(2) |
| stall | out | 1 | 寄存器输出，为 1 时阻止新事务进入，复位为 0 |
| txn_start | in | 1 | 本周期有一个新事务开始 |
| txn_done | in | 1 | 本周期有一个事务完成 |
| outstanding | out | CW | 寄存器输出，未完成事务数，复位为 0 |

环境保证（testbench 遵守）：
- stall=1 时 txn_start 一定为 0；只有 outstanding>0 时才会有 txn_done；outstanding 不会溢出。
- preq 拉高以后，pstate 保持不变，直到 testbench 看到 paccept 或 pdeny 为 1。之后 testbench 会拉低 preq，并且只在 paccept 和 pdeny 都为 0 时才会发起下一次请求。

计数器：每个周期 `outstanding <= outstanding + txn_start - txn_done`（两者同时为 1 时保持不变）。

状态机有四个状态：IDLE、QUIESCE、WAKE、RESP，复位进入 IDLE。另有内部寄存器 `target`（2 位）和 `timer`。所有寄存器都在时钟沿更新，下面的“进入 X”都是指下一个周期生效。

- **IDLE**（此时 paccept=pdeny=0）：如果 `preq=1`，记 `t = pstate`，同时 `target <= t`：
  - t == 3：进入 RESP，`pdeny <= 1`
  - t == cur_state：进入 RESP，`paccept <= 1`
  - t < cur_state（降功耗）：进入 QUIESCE，`stall <= 1`，`timer <= 0`
  - t > cur_state（升功耗）：进入 WAKE，`timer <= 0`
- **QUIESCE**：
  - 如果 `outstanding == 0`：进入 RESP，`paccept <= 1`，`cur_state <= target`（stall 保持 1）
  - 否则如果 `timer == TIMEOUT-1`：进入 RESP，`pdeny <= 1`，`stall <= (cur_state != ON)`
  - 否则 `timer <= timer + 1`

  这样 QUIESCE 最多停留 TIMEOUT 个周期。进入 QUIESCE 的第一个周期就检查 outstanding。
- **WAKE**：
  - 如果 `timer == WAKE_CYC-1`：进入 RESP，`paccept <= 1`，`cur_state <= target`，`stall <= (target != ON)`
  - 否则 `timer <= timer + 1`

  这样 WAKE 恰好停留 WAKE_CYC 个周期，期间 stall 保持原值。
- **RESP**：paccept/pdeny 保持原值。如果 `preq == 0`：进入 IDLE，`paccept <= 0`，`pdeny <= 0`。

没有提到的寄存器一律保持原值。

测试参数：(CW=3, TIMEOUT=8, WAKE_CYC=3)，(CW=4, TIMEOUT=20, WAKE_CYC=1)
