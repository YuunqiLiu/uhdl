# SV vs UHDL 实验结果（2026-11-04）

每道题、每种语言各由 1 个 subagent 实现，同一个模型，题面完全相同。实现者看不到评测用的 testbench（在 `_eval/tb/`）。评分脚本 `_eval/grade.py`：testbench 内置参考模型，随机激励逐拍比对；testbench 本身先用 `_eval/golden/` 的参考实现验证过，8 组配置全部通过。

## 正确性和质量
| 题目 | 配置 | SV 测试 | UHDL 测试 | lint 告警 (SV/UHDL) | yosys cells (SV/UHDL) | DFF |
|---|---|---|---|---|---|---|
| P1 rr_arb | N=4 / N=7 | PASS / PASS | PASS / PASS | 0/0 | 36/35, 83/80 | 相同 |
| P2 sync_fifo | 8x5 / 16x4 | PASS / PASS | PASS / PASS | 0/0 | 130/170, 148/199 | 相同 |
| P3 pkt_mux | 3x8 / 5x16 | PASS / PASS | PASS / PASS | 0/0 | 117/108, 405/303 | 相同 |
| P4 addr_router | A / B | PASS / PASS | PASS / PASS | 0/0 | 57/53, 40/37 | 0 |

yosys 用的是 `synth -flatten -nofsm`。开启 FSM 优化时，yosys 会把 UHDL 版 P1 的 ptr 重新编码，导致 DFF 数量不同，这和设计本身无关。

## 开销
| | SV（4 题合计） | UHDL（4 题合计） | 比值 |
|---|---|---|---|
| tokens | 170,024（平均 42.5k） | 318,061（平均 79.5k） | 1.87x |
| 工具调用 | 43 | 98 | 2.3x |
| 耗时 | 947 s | 1381 s | 1.46x |

逐题明细见 `_eval/usage.tsv`。

## 源码行数（非空、非注释行）
| | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| SV `.sv` | 43 | 53 | 54 | 78 |
| UHDL `gen.py` | 96 | 99 | 116 | 114 |
| UHDL 生成的 `.v` | 40–43 | 102–110 | 111–141 | 33–35 |

## 实验中发现的 UHDL 问题
1. **Bug（会悄悄生成错误逻辑）**：在 Reg 的 when 链里有多个 `Cut(a±b)` 分支时，这些分支共用同一个临时 wire `<reg>_bcut_tmp`，结果每个分支都变成了第一个分支的表达式。已复现，见 `_eval/uhdl_cut_bug_repro.py`：减一分支被生成成了 `c + 1`。
2. 模块名会自动加上 `__init__` 参数作为后缀，没有 API 可以关掉。4 个 subagent 各自想了一种绕法：工厂闭包、`type()` 动态建类、覆盖 `module_name` 属性。
3. `generate_verilog` 固定输出到 `<out>/<module>/`，并且会先删掉这个目录。4 个 subagent 都得绕开这一点。
4. `+`/`-` 的结果总是加宽 1 位，没有回绕加法，截断后会产生 UNUSED 告警，需要单独处理。
5. 比较表达式原样输出，会触发 Verilator 的 CMPCONST 告警；也没法输出 lint pragma。
6. 没有存储阵列原语，P2 的存储只能写成 DEPTH 个寄存器加 Case 读出，带复位，所以面积比 SV 大约多 30%。
7. 会在当前目录写 `UHDL.log`；常量全部以二进制形式输出。

## 需要注意的局限
- 每个格子只有 1 个样本，面积差异主要反映各 subagent 选的算法，不能直接归因于语言。
- 每个 UHDL subagent 都是从零开始读 UHDL 文档，学习成本在每道题里都算了一遍。实际使用时这部分会被分摊。
- 下一轮建议：给 UHDL subagent 一份速查表（API 加上述坑），测“学会之后”的稳态成本；再加一道控制逻辑密集的题（比如 P-channel 状态机）。

---

# 第二轮（UHDL 带速查表 + 控制密集题 P5）

改动：
- UHDL subagent 先读 `specs/UHDL_CHEATSHEET.md`（约 1 页：API、输出骨架、已知的坑）和一个已验证的示例。
- SV subagent 也拿到一份对等的 `specs/SV_NOTES.md`（工具的坑）。
- 新增 P5 `pchan_ctrl`：P-channel 低功耗状态机，带超时和上电等待，SV 和 UHDL 各 2 个样本。
- 产出在 `r2/`，评测数据在 `_eval/usage_r2.tsv` 和 `_eval/results_r2.json`。

## 正确性
第二轮 8 份全部 PASS，Verilator `-Wall` 0 告警。P5 每组配置跑 3 万拍，覆盖 accept、deny、超时、wake 各分支。

## 开销对比（P1–P4 合计）
| | SV（第一轮） | UHDL 不带速查表（第一轮） | UHDL 带速查表（第二轮） |
|---|---|---|---|
| tokens | 170k | 318k | **173k**（是 SV 的 1.02x） |
| 工具调用 | 43 | 98 | 32 |
| 耗时 | 947 s | 1381 s | 617 s |

SV 第一轮没有拿到 SV_NOTES，所以 SV 那一列的工具调用和耗时偏高，这两项的对比对 UHDL 有利。token 的对比基本不受影响。

## P5（控制逻辑为主，每种语言 2 个样本）
| | tokens | 工具调用 | 耗时 | cells (3/8/3, 4/20/1) | 源码行数 |
|---|---|---|---|---|---|
| SV a | 38.3k | 6 | 113 s | 119 / 139 | 108 |
| SV b | 39.0k | 6 | 167 s | 119 / 139 | 108 |
| UHDL a | 47.5k | 7 | 202 s | 95 / 116 | 160 |
| UHDL b | 45.5k | 6 | 207 s | 87 / 107 | 120 |

UHDL 平均是 SV 的约 1.2 倍 token、1.45 倍耗时。同一语言的两个样本之间 token 差距不到 5%，两份 SV 代码的相似度为 75%。

## 第二轮面积（cells）
| | P1 N=4/7 | P2 | P3 | P4 |
|---|---|---|---|---|
| SV（第一轮） | 36/83 | 130/148 | 117/405 | 57/40 |
| UHDL 第二轮 | 28/58 | 182/198 | 95/283 | 55/39 |

P1 的 UHDL 版选了“温度计掩码”方案，触发器多、组合逻辑少，这是写法上的选择。P2 仍然因为没有存储阵列原语而偏大。

## 结论
1. 第一轮 UHDL 多出来的约 1.9 倍 token，基本都是学习和踩坑的成本。有一页速查表之后，偏数据通路的题和 SV 持平（1.02x），控制逻辑为主的题约 1.2x。
2. 两种语言的质量（正确性、lint）一样。面积差异主要来自写法选择；唯一稳定的劣势是 UHDL 没有存储阵列原语（P2）。
3. UHDL 的源码行数约为 SV 的 1.1–1.5 倍，主要是生成器骨架和 Wire 声明。
4. 速查表里列的坑（模块名、输出目录、回绕加法、存储阵列、Cut bug）应该在 UHDL 里直接修掉，并维护一份面向 LLM 的官方指南。

---

# 第三轮：复杂设计 + lint “自觉性”（改进版 UHDL）

设置：
- 题目：D1 `noc_sw`（N 入 M 出包交换，带输入 FIFO、路由表和按包锁定的轮询仲裁）、D2 `axil_regs`（寄存器表驱动的 AXI4-Lite 从设备，端口随配置变化），规格见 `specs/SPEC2.md`。每题每种语言 2 个样本，共 8 个 subagent。
- UHDL 用 `lwnoc_rewrite` 分支修过的版本，并附 LLM 指南。
- **题面和资料里完全不提 lint。** 指南和 SV 注意事项都用的是删掉 lint 相关内容的副本（`specs/UHDL_GUIDE_r3.md`、`specs/SV_NOTES_r3.md`）。
- 要求每个 subagent 在跑任何工具之前先保存一份初稿 `draft1/`。评测脚本和数据在 `_eval/r3/`。

## 正确性
- 终稿：8/8 在两组配置下都通过隐藏 testbench。
  - D1 逐周期精确比对 2 万拍。
  - D2 跑 3000 个随机 AXI 事务，检查协议规则、响应码，以及第一次 bvalid 时寄存器输出是否已更新。
- 初稿（没跑过任何工具）：
  - SV：4/4 功能正确。
  - UHDL：3/4 功能正确。D1b 编译失败，原因是 UHDL 的一个新 bug：子模块输出直接赋给父模块 Wire 时，会生成一句引用未声明线网的 assign。已在 `289c8db` 修复，修复后这份初稿也能通过。

## lint：初稿 vs 终稿（verilator -Wall，配置 A/B）
| 样本 | SV 初稿 | SV 终稿 | UHDL 初稿 | UHDL 终稿 |
|---|---|---|---|---|
| D1a | 1（DECLFILENAME） | 0，用了 2 处 lint_off | 0 | 0，没有任何抑制 |
| D1b | 1（DECLFILENAME） | 0，用了 2 处 lint_off | 编译失败（UHDL bug） | 0，没有任何抑制 |
| D2a | 3/4（UNUSEDSIGNAL） | 0，用了 2 处 lint_off | 0（用了 1 次 mark_unused） | 0，用了 1 次 mark_unused |
| D2b | 2/2（UNUSEDSIGNAL） | 0，用了 2 处 lint_off | 2/3（UNUSEDSIGNAL） | 0，用了 1 次 mark_unused |

- 8 个 subagent 在没有任何提示的情况下，**都自己跑了 `verilator -Wall`，并把告警清到 0**。
- SV 初稿里**没有出现**任何会影响功能的告警类别（WIDTH、LATCH、MULTIDRIVEN、CASEINCOMPLETE 等）。出现的只有“未使用信号”和“一个文件放了多个模块”这两类。
- SV 终稿做到 0 告警，有一部分靠的是 `lint_off` 压制（4/4 都用了）。UHDL 一方对应的手段是 `mark_unused`（2/4 用了）。“一个文件多个模块”这类告警，UHDL 因为 `generate()` 每个模块单独一个文件，天然不会出现。

## 开销
| | SV（2 个样本平均） | UHDL（2 个样本平均） | 比值 |
|---|---|---|---|
| D1 tokens | 59.5k | 63.0k | 1.06x |
| D2 tokens | 51.1k | 67.9k | 1.33x |

## 面积（yosys cells，A/B）
| | SV a | SV b | UHDL a | UHDL b |
|---|---|---|---|---|
| D1 | 1115 / 2361 | 1074 / 2718 | 1104 / 2333 | 1115 / 2225 |
| D2 | 1112 / 1393 | 1048 / 1396 | 981 / 1359 | 820 / 1102 |

## 评测隔离问题（如实记录）
- 隐藏的 testbench 原本放在 scratchpad 里，而 subagent 也把 scratchpad 当成自己的工作区。
- 一个 SV subagent 报告说，它看到了隐藏 testbench 的前 3 行（只是参数声明）。另一个 SV subagent 的自测 testbench 和隐藏 testbench 的命名有重合，可能是巧合。
- 两份 D1-SV 的初稿都是在跑任何工具之前保存的，终稿和初稿相比只多了 lint pragma，设计逻辑完全一样。所以正确性结论不受影响。
- 后来已经把隐藏文件移出 scratchpad。下一轮应该一开始就放在 subagent 访问不到的位置。

## 结论（第三轮）
1. **“框框”确实有用，但这次主要体现在设计上，不在 lint 告警上。** 这个模型写的 SV 初稿，本来就不会出现会导致功能错误的告警类别。UHDL 在这些类别上的优势（位宽、锁存器、多驱动在生成阶段就直接报错）是一种结构性的保证：不管是谁、用什么模型来写，都成立。SV 要达到同样效果，得靠模型自己的习惯，或者靠 CI 里的 lint 门禁。
2. **“自觉性”这次是存在的**：8/8 都主动去做了 lint。但 SV 一方做到 0 告警，有一部分靠的是压制，`lint_off` 需要人工审查。UHDL 的 `mark_unused` 本质上也是同一回事，只是写法更显式。
3. 复杂设计上，UHDL 的 token 开销是 SV 的 1.06–1.33 倍，面积持平或略小，正确性一样。
4. 测试又暴露出一个 UHDL bug（子模块输出连到父模块 Wire），已修复并补了测试。

---

# 第四轮：弱模型（Haiku 5.5 / Sonnet 5.5）

目的：验证"UHDL 的框框在弱模型上更有价值"这个假设。题目（D1 `noc_sw`、D2 `axil_regs`）、prompt、指南都和第三轮完全相同，只把 subagent 换成 Haiku 和 Sonnet，每个组合 1 个样本。
隔离：开跑前把 `_eval/`、之前几轮的答案和本文件都移到了 subagent 访问不到的目录，跑完再放回。评分脚本 `_eval/r4/grade4.py`（第三轮评分脚本只改了路径）。

## 正确性（隐藏 testbench，A/B 两个配置）
| | SV 初稿 | SV 终稿 | UHDL 初稿 | UHDL 终稿 |
|---|---|---|---|---|
| Haiku D1 | PASS | PASS | PASS | PASS |
| Haiku D2 | PASS | PASS | PASS | PASS |
| Sonnet D1 | PASS | PASS | PASS | PASS |
| Sonnet D2 | PASS | PASS | PASS | PASS |

16/16 全部通过，包括所有还没跑过任何工具的初稿。

## lint（`verilator -Wall`，cfgA / cfgB 的告警数）
| | SV 初稿 | SV 终稿 | UHDL 初稿 | UHDL 终稿 |
|---|---|---|---|---|
| Haiku D1 | 1/1（DECLFILENAME） | 1/1（DECLFILENAME，没清） | 3/4（UNUSEDSIGNAL） | 0 |
| Haiku D2 | 1/1（UNUSEDSIGNAL） | 0，2 处 lint_off | 3/4（UNUSEDSIGNAL） | 0，1 次 mark_unused |
| Sonnet D1 | 0 | 0 | 0 | 0 |
| Sonnet D2 | 3/4（UNUSEDSIGNAL） | 0，2 处 lint_off | 1/2（UNUSEDSIGNAL） | 0，1 次 mark_unused |

- 即使是 Haiku，SV 初稿里也**没有任何会影响功能的告警**（WIDTH、LATCH、MULTIDRIVEN、CASEINCOMPLETE 都没出现）。只有"未使用信号"和"一个文件多个模块"。
- 唯一一份没清到 0 的终稿是 Haiku 的 SV D1（剩一条 DECLFILENAME，纯风格）。Haiku 在报告里自己说了"only DECLFILENAME"，是有意保留。
- UHDL 初稿的 UNUSEDSIGNAL 反而比 SV 多：把 flit 打包成一个宽信号后只用其中一部分位，UHDL 生成的中间线会暴露这个问题。

## token
| | SV | UHDL | 比值 |
|---|---|---|---|
| Haiku D1 | 81.4k | 88.0k | 1.08x |
| Haiku D2 | 85.8k | 127.8k | 1.49x |
| Sonnet D1 | 56.1k | 62.7k | 1.12x |
| Sonnet D2 | 46.1k | 49.8k | 1.08x |

## 面积（yosys cells，A/B）
| | SV | UHDL |
|---|---|---|
| Haiku D1 | 967 / 2705 | 1044 / 2189 |
| Haiku D2 | 784 / 1061 | 984 / 1359 |
| Sonnet D1 | 1054 / 3078 | 1047 / 2178 |
| Sonnet D2 | 984 / 1362 | 820 / 1102 |

## 结论（第四轮）
1. **"弱模型更需要框框"这个假设没有得到支持。** 在这两道题上，Haiku 和 Sonnet 写 SV 同样不犯位宽、锁存器、多驱动这类错，初稿正确率 100%。
2. UHDL 的保证仍然是结构性的，但在这个规模的题目上，各档模型都没有犯会被它拦住的错误，所以它的价值目前只停留在"保险"层面，没有体现为实测收益。
3. token：UHDL 是 SV 的 1.08–1.49 倍，最差的是 Haiku 写 D2（配置驱动的端口），和第三轮的结论一致：配置驱动的设计在 UHDL 里写起来更贵。
4. 面积没有稳定的规律：D1 配置 B 上 UHDL 一致更小（约 20–30%），D2 两边各有大小。

# lwnoc 生成器回归（UHDL 77d05c9 → lwnoc_rewrite 289c8db）
在 `lwnoc_network_demo` 上，分别用原版 UHDL 和 `lwnoc_rewrite` 跑 ATB、DTI、STS、INTR 四个生成器（脚本 `_eval/r4/run_all.sh`）：
- 4 个生成器都正常结束，新增的多驱动和锁存器检查都没有报错。
- 生成的 RTL 和 filelist 共约 1.13 万个文件，只有 4 个有变化，都是同一个 regbank 模块：单参数的 `Combine` 不再输出多余的花括号（`{x}` → `x`），功能等价。

---

# 第五轮：紧凑语法（lwnoc_rewrite cac136c / 0442185）

UHDL 新增：整数常量自动取位宽、`s.wire/s.reg/s.mem/s.domain`、`Input(8)`、`.eq/.lt/...`、`split`、`Cat/If/Mux/Priority`。指南 `specs/UHDL_GUIDE_r5.md`（由 `docs/LLM_GUIDE.md` 去掉 lint 字样得到，做法同第三轮）。题目、prompt 与第三轮相同，模型同为默认（Opus），每题 2 个样本，只跑 UHDL；SV 基线用第三轮。评分 `_eval/r5/grade5b.py`。

## 正确性与 lint
| | 初稿 | 终稿 | 初稿 lint | 终稿 lint |
|---|---|---|---|---|
| D1a | PASS | PASS | 0 | 0 |
| D1b | 生成失败：`Mux(..., width=1)` 不被接受 | PASS | — | 0 |
| D2a | PASS | PASS | 1/2（UNUSEDSIGNAL） | 0 |
| D2b | PASS | PASS | 0 | 0 |

D1b 的失败暴露的是 API 不顺手：agent 很自然地把 `width=` 写在 `Mux` 上。已在 16edcfc 让 `Mux` 接受 `width=`。

## 开销（总 token，2 个样本平均）
| | SV（第三轮） | UHDL 旧语法（第三轮） | UHDL 新语法（第五轮） |
|---|---|---|---|
| D1 | 59.5k | 63.0k（1.06x） | 53.8k（0.90x） |
| D2 | 51.1k | 67.9k（1.33x） | 53.7k（1.05x） |

## 源码大小（去掉注释和空行，o200k token，样本平均）
| | SV（第三轮） | UHDL 旧语法 | UHDL 新语法 |
|---|---|---|---|
| D1 | 1621 | 2090 | 1387 |
| D2 | 3566（Python 模板 + SV 文本） | 2219 | 1862 |

## 面积（yosys cells，A/B）
D1：1124/2328、1108/2349；D2：774/1052、773/1051。与前几轮同一量级，D2 比第三轮 UHDL（981/1359、820/1102）更小。

## 结论（第五轮）
1. 紧凑语法让 UHDL 的总开销从 SV 的 1.06–1.33 倍降到 0.90–1.05 倍，基本持平。
2. 源码比旧语法少 16–34%，D1 比 SV 少 14%，D2 比"Python 模板生成 SV"少 48%。
3. 保证没有变：所有终稿 0 告警，位宽检查、锁存器和多驱动检查照旧。

---

# 第六轮：第 1–3 项新语法（lwnoc_rewrite b79211e / fdb67e8），Opus，UHDL

| | 上一版（第五轮 D2 / CDC 轮） | 第六轮 | 变化 |
|---|---|---|---|
| CDC 源码 token | 1792 / 1838 | 1163 / 1120 | **-37%** |
| CDC 总 token（均值） | 89.3k | 69.6k | **-22%** |
| CDC 时长（均值） | 1416s | 633s | -55% |
| CDC 结果 | 仿真全过，CDC 0 违例 | 仿真全过（A/B/C），CDC 0 违例 | 不变 |
| D2 源码 token | 2002 / 1732 | 1781 / 1696 | -7% |
| D2 总 token（均值） | 53.7k | 64.1k | +19%（样本波动） |
| D2 结果 | 终稿全过，lint 0 | 初稿、终稿全过，终稿 lint 0，面积 773–775 / 1051–1052 | 不变 |

## 新功能被用了多少
- **CDC**：两份都用了 Struct、stream_in/stream_out/Stream.of（各 4 处）、AsyncFifo 的 .w/.r 以及切片赋值；一份还用了构造时指定时钟（w=/r=）。都没用条件块，这道题也用不上。
- **D2**：两份**完全没用**条件块、状态机、`<<=` 和 Struct，仍然是每个寄存器一条 when 链。

## 结论
1. 第 1、2 项（Struct、Stream、整组连接、时钟继承）被 agent 自然采用，源码少 37%，总 token 少 22%，正确性不变。这是目前实测效果最大的一次改进。
2. 第 3 项（条件块）在 D2 上没有被采用。D2 的控制逻辑以"每个寄存器各管各的"为主，agent 觉得 when 链已经够用。我自己用条件块写 D2 能少 41%，说明写法本身有效，但 agent 默认不会选它。如果要推广，指南需要明确规定"一个条件同时驱动多个信号时用块写法"，或者用更典型的状态机题来测。

## 第七轮：指南加上"一个条件驱动多个信号时用 when-block"的规则（4311a79），D2 重跑
| | 第五轮（紧凑语法） | 第六轮（有 block，没规则） | 第七轮（有规则） |
|---|---|---|---|
| 采用 when-block | — | 0/2 | **2/2（每份 6 个块、14 处 `<<=`，只剩 1 条 when 链）** |
| 源码 token | 1867 | 1739 | 1700（1721 / 1680） |
| 总 token（均值） | 53.7k | 64.1k | 61.9k |
| 结果 | 全过 | 全过 | 初稿、终稿全过，终稿 lint 0，面积 776 / 1054 |

结论：
- 加了规则后 agent 全部改用块写法，正确性不变。但源码只比上一轮少 2%，比第五轮少 9%，总 token 在样本波动范围内。
- 对 D2 这种以"寄存器各管各"为主的设计，块写法带来的是可读性（一个事件的效果写在一处），不是明显更短的代码。
- 我自己写的 1097 token 版本，省下来的主要不在块写法，而在少写辅助线、直接用 Priority/Mux、自定义小 helper 等编码风格。要靠语言特性把这部分省下来，需要第 4 项的标准库（比如 RegBank）。
