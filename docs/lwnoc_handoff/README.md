# lwnoc 重写 / UHDL 工作交接（2026-11-26）

这份文档交接 2026-11-04 至 11-09 一个会话里做的全部工作：用 UHDL 重写 lwnoc 的前期准备、UHDL 本身的改造与打包、把 UHDL 集成进 motryx-toolkit、以及 memnoc（lwnoc_mnoc）的延迟分析和微架构图。接手的 agent 先读这一份，再按需读同目录的其他文件。

## 0. 目录内容

| 文件 | 内容 |
|---|---|
| `README.md` | 本文：现状、决定、未完成事项、后续规划、环境注意事项 |
| `mnoc_latency.md` | memnoc 零负载读写延迟、INIU 15 拍逐拍拆分、优化选项 A–F、拆分器 LOL、发现的疑似 RTL 问题 |
| `lwnoc_current_state_review.md` | lwnoc 现状评审（生成器 / RTL / 真值来源的问题），2026-11-04 |
| `uhdl_evolution_review.md` | UHDL 设计哲学与在 lwnoc 中的演变，2026-11-04 |
| `figures/` | 本地画的微架构图（浏览器直接打开）。`axi_splitter_pipeline_toy.html` 是最终版，`.drawio` 是它的可编辑源文件，`src/gen_splitter_dio.py` 生成该 drawio。其余三张是早期版本 |
| `experiments/` | SV vs UHDL 的 LLM 对比实验结论（`*/RESULTS.md`）和题面；原始数据还在本地 `/workspace/lwnoc_dev/exp`（21MB，没上传） |
| `tniu_port/` | lwnoc_mnoc TNIU 写通道的 UHDL 移植，四级都与 RTL 逐拍等价（原在本地 `/workspace/lwnoc_dev/uhdl_tniu`，未进过仓库） |

## 1. 仓库地图

工作目录统一在 `/workspace/lwnoc_dev`（用户明确要求）。

- `uhdl_work/` → **YuunqiLiu/uhdl**，分支 `lwnoc_rewrite`；默认分支是 `master`（没有 main），两者保持一致，当前都是 `184386d` + 本交接提交。用户允许直接推送。
- `lwnoc/` → GitHub 组织 `lwnoc`：lwnoc_network_demo（集成顶层，子模块拉其余仓库）、lwnoc_{dti,atb,interrupt,sts}_noc、lwnoc_mnoc（**luhz 维护**）、lwnoc_ring_network、noc_hdds（**lgzhu 维护**）、aichip_memnoc、npu_mnoc_example。
- `fliibs/` → 组织 `fliibs`：lwnoc_topo（拓扑生成器）、lwnoc_lowpower_component、noc_draw 等。
- `personal/` → YuunqiLiu：uhdl（主仓库的另一份检出，落后远端 55 提交）、lwmesh、interrupt_noc。
- `wt/uhdl_{master,ai_driven}` → uhdl 的旧工作树（detached），只作对比用。

**不要未经用户同意修改 lwnoc 组织下别人维护的仓库**（lwnoc_mnoc、noc_hdds 等）。

### 推送状态（2026-11-26 核对）
- 所有提交都已在 GitHub 上。
- lwnoc_network_demo main = `3e89aade`；它引用的 lwnoc_topo `10babe3` 在分支 `fix/sts-address-planner-pin-20261012` 上，**没有合进 lwnoc_topo main**（main 已前进 110 个提交）。是否合并要用户决定。
- ip_builder main = `df54434`（TemplateIP 从 uhdl 移到 `ip_builder/uhdl_template_ip.py`）。
- 未提交、也不建议提交：`lwnoc_topo/ip_builder/submodule/fexpand/pcpp/parsetab.py`（PLY 自动生成，可还原）；`wt/uhdl_master/Test/`（11-04 的临时测试文件）。

## 2. 已完成

### 2.1 UHDL 改造（`lwnoc_rewrite`，均已推送）
- 修 bug、加功能：Cut #17、MODULE_NAME、`generate(out_dir)`、Mem、latch / 多驱动报错、紧凑语法（`s.wire/s.reg/s.mem/s.domain`、`Input(8)`、`If/Mux/Priority` 等）、Struct、Stream、部分位驱动、`with s.when/elsewhen/otherwise`、`s.fsm`、隐式子模块时钟复位、`check_cdc` 与 CDC 单元（CdcSync/CdcBus/AsyncFifo）。用法写在 `docs/LLM_GUIDE.md`。
- 源码定位（`uhdl/core/SrcLoc.py`）：报错以 `file:line` 开头，生成的 Verilog 带 `// file.py:line` 注释（用户要求默认开启，便于从仿真追回源码）。冻结版里也指向用户的源码行。
- 打包：`pyproject.toml`，核心只依赖标准库，Python 3.8+。
- **SystemVerilog 读入改用自己的 `libuhdl_slang.so`**，不再依赖 pyslang：`native/uhdl_slang.cpp` 把 slang v10.0 包成 C API（结果以 JSON 放在内存里返回，不落盘），Python 侧用 ctypes 加载（`uhdl/core/_slang.py`）。与 Python 版本无关；静态链接 libstdc++，只导出 5 个函数，GLIBC_2.17。子模块 `third_party/slang`（v10.0）、`third_party/fmt`（12.1.0）。用户决定：design_reader 和 uhdl 各自维护自己的 slang 封装。
- 回归：`pytest` 270 个用例通过；lwnoc_network_demo 的 ATB/DTI/STS/INTR 生成结果与旧 uhdl 逐字节一致；TNIU 10 个文件与 pyslang 版逐字节一致。

### 2.2 Agent Skill 与 toolkit 组件
- Skill：`skill/uhdl-design/SKILL.md`，测试在 `skill/tests`（含带隐藏 TB 的 e2e t1/t2；`run_headless.sh` 由用户用 `!` 自己跑过，opus/haiku 都通过）。
- 组件：`packaging/build_component.py` 产出冻结的 `uhdl` 命令（`uhdl run|check|python|pythonpath|version`）+ `_uhdl/` 运行时 + `skill/` + `component-manifest.json`（schema 1），可复现 tar 包 + `.sha256`。保留 ssl、strip 二进制：解包 35MB、压缩包 14.7MB、GLIBC_2.17。同时保留 Python 源码（`uhdl pythonpath`），agent 可以在用户自己的 Python 上用 uhdl。
- 已用 toolkit 自己的代码验证合约：`skill/tests/check_toolkit_contract.py`（调用 toolkit 的 `update_component_lock.py` 和 `package_toolkit.verify_component_archive`，再按 toolkit 的方式安装并运行）。
- Motryx 上实测：t1/t2 × 两个模型 6/6 通过。Skill 根目录要注册成 `<toolkit>/skills`；注册成 `skills/<component>` 时 agent 会读错路径。
- 本地构建产物：`uhdl_work/dist/component/uhdl-0.9.0-linux-x86_64.tar.gz`（gitignore，不入库）。

### 2.3 实验结论（`experiments/`）
- 小设计（单模块）上，弱模型写 SV 并不比写 UHDL 更容易出错，"弱模型需要 UHDL 护栏"的假设不成立；把规则写下来后各组都能做对。
- UHDL 的价值在规模和可修改性：8×8 mesh 展平 RTL 约 1.1M token，UHDL 源 2.5k；在展平 RTL 上做修改花约 2.2 倍 token。不规则拓扑上 UHDL 源码小 30–35%。
- 紧凑语法让 UHDL 总 token 从 SV 的 1.06–1.33 倍降到 0.90–1.05 倍；when 块 / fsm 需要指南里写明规则 agent 才会用；寄存器类逻辑要靠标准库（TODO 第 4 项）才能再省。
- 教训：隐藏 TB 不能放在 scratchpad（子 agent 会把它当工作目录看到）；并行 agent 要各给一个全新的输出目录。

### 2.4 TNIU 写通道移植（`tniu_port/`）
rob_entry → write_rob → write_buffer（含 sender）→ write_channel，四级都与 lwnoc_mnoc RTL 逐拍等价（Verilator 20 万拍随机 + 闭环流量 TB，变异体能抓出来）。源码 13.9k → 8.2k token（−41%），lint 0 条（RTL 有 7 条告警）。类型和参数用 `import_sv_package` 从 `lwmnoc_pack.sv` 读取；fcip IP 以 VComponent 引入（需要 `--single-unit` 处理 `_PREFIX_` 宏）。README 里的路径是本机绝对路径。

### 2.5 MNOC 分析与图
见 `mnoc_latency.md` 和 `figures/`。

## 3. 等待中 / 未决事项

1. **motryx-toolkit 集成**：已提 NexEvic/motryx-toolkit#16（2026-11-08，截至 11-26 仍 OPEN、无回复；toolkit 的 `components.lock.json` 里还没有 uhdl）。toolkit 侧需要：allowlist 加 uhdl、4 组件门禁改为 5 个、uhdl 仓库缺 CI `release.yml`（打包、qualification 记录、发布到 release）、glibc 2.17 工具链、skill 根目录注册为 `<toolkit>/skills`。#15 已关闭（不再需要）。**uhdl 仓库这边还没有 `.github/workflows/release.yml`**，这是接下来最可能要补的东西。
2. **INIU 优化 A/D 是否实施**：见 `mnoc_latency.md`。改的是 lwnoc_mnoc（luhz 维护），用户未批准。
3. **lwnoc_topo 分支是否合入 main**：见 §1。
4. **疑似 RTL 问题**（`mnoc_latency.md` 末尾）：未确认，未报告给维护者。
5. 本地大目录是否删除：`/workspace/lwnoc_dev/_mtx`（607MB，Motryx 验证批次）、`_lwgen`（14MB 生成回归数据）。用户没表态，先别删。

## 4. 后续规划

- **UHDL 标准库**（`docs/TODO.md` 第 4 项）：`rr_arbiter`、`s.counter`、`RegBank`、Stream 组合子（fifo/pipe/skid/map/mux/arbitrate）、归约工具。实验里 agent 反复手写这些。
- **自动跨时钟** `s.cross(x, to=clk)`（TODO 第 5 项），需要公开的 `domain_of()`。
- **toolkit 集成跟进**：补 `release.yml`，按 #16 的回复调整。
- **lwnoc 重写本身**：用户已定"不需要保持现有 SoC 外部接口兼容"。现状问题见 `lwnoc_current_state_review.md`（5 张各自演化的 NoC、生成器只是连线工具、真值来源分散）。TNIU 移植证明了"手写 RTL → UHDL 逐拍等价移植"的路子可行，下一步可以继续移植 INIU 或者从统一的 flit / NIU 抽象开始设计。尚未与用户讨论具体路线。
- 未测试：在不规则、更大的真实设计上做修改任务的效果。

## 5. 环境与操作注意事项

- **回答用户一律用中文。**
- **不要做 RTL 仿真**来分析 lwnoc_mnoc（用户明确要求；仓库 AGENTS.md 也禁止本地跑 Verilator / 大型 EDA）。
- **画图只画在本地文件里**（独立 HTML + 内嵌 SVG），不发布成在线页面，画完告诉用户完整路径（用户全局 CLAUDE.md 规定）。
- 用户参考的画图风格是 **fliibs/toy_scalar `ooo-main` 分支 `doc/uarch.drawio`** 的 TOP / issue 页（不是默认分支）：竖长条寄存器带灰线、竖梯形 mux、功能块粒度、粗体英文标签。要看清原图必须用官方 drawio 导出，自写渲染器差距很大。本机装法：下载 drawio-desktop AppImage → `--appimage-extract`；用 conda 装 `gtk3 atk-1.0 at-spi2-atk at-spi2-core libcups libgbm nss` 到一个前缀；`LD_LIBRARY_PATH=<前缀>/lib DISPLAY=:N`（先起 `Xvfb :N`）运行 `drawio --no-sandbox --disable-gpu --disable-dev-shm-usage -x -f png|svg -p <页号，从 1 开始> -o out in.drawio`。/dev/shm 只有 63MB，不加 `--disable-dev-shm-usage` 渲染进程会崩。本机没有中文字体，检查 PNG 时中文显示为方块。
- **磁盘紧**：`/tmp` 是 256MB tmpfs，临时构建放 `/workspace` 下，用完清理。
- **git**：仓库属主是 uid 1010，git 会报 dubious ownership，单条命令用 `git -c safe.directory='*'`，不要改全局配置。提交身份要显式传：`GIT_AUTHOR_NAME=Liuyunqi GIT_AUTHOR_EMAIL=15517439+YuunqiLiu@users.noreply.github.com`，COMMITTER 同值。
- **构建 libuhdl_slang**：`CXX=/workspace/tmp/toolchain/bin/x86_64-conda-linux-gnu-g++ PATH=/workspace/tmp/toolchain/bin:$PATH python native/build.py`（gcc 13 + glibc 2.17 sysroot，构建目录 `native/build`）。冻结组件用 `/workspace/tmp/toolchain/bin/python3`（3.12，glibc 2.17）跑 `packaging/build_component.py`。
- Python 环境：`/workspace/lwnoc_dev/.venv`（system-site-packages，有 yosys、verilator）。
- lwnoc_network_demo 子模块用 ssh URL，克隆时加 `git -c url.https://github.com/.insteadOf=git@github.com:`。
- Motryx 启动常报 "workspace routing discovery failed"：归档该 run 和 claim，删 `/tmp/rv-<sha12(run 路径)>` 后重试。
