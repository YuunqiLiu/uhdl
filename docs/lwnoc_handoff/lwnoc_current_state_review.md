# lwnoc 现状评审（2026-11-04）

静态阅读，未跑仿真。路径相对 /workspace/lwnoc_dev。

## 总体判断
lwnoc 现在不是“一套 NoC 架构”，而是 5 张各自演化的 NoC（sts / intr / dti / atb / mnoc），只共享了 NIU 的骨架（sys side → async bridge → noc side → network）和 fcip / lowpower 组件。
生成器（UHDL + lwnoc_topo）只是把手写 RTL 连起来的连线工具，它自身的限制又渗进了 RTL（35 个 N-to-1 / 1-to-N wrap 文件）。
真值来源分散，只能靠事后的大量正则检查脚本（约 1 万行）来补。

## 1. 生成器 / 数据模型
- topo_core 是通用的 netlist（Node/Edge/Interface），没有 NIU、路由、地址窗口、ID、时钟域这些 NoC 概念。端口也没有协议、方向和位宽。
- 至少 5 份真值：散文 topo 文件、*UserConfig.py、*Template.py 里的常量、手写的路由分组（STS_SOC_DECODER_ROUTE_GROUPS）、csv/xlsx 快照。几份之间互相矛盾：INTR 和 AGENTS.md 对“谁是权威”的说法相反；STS slot 文档写 96KB，代码是 128KB。
- 路由是手写的，不是从图里推出来的。lwnoc2 原型（uhdl/Demo/lwnoc2/TopoNetwork.py:155-224）里有自动传播 reachable_tgt_id，现在被注释掉了。
- 连线靠“正则匹配端口名 + zip 按位置配对”，长度对不上只报 warning 然后跳过，可能悄悄少接线（uhdlWrapperNode.py:711-751）。
- 生成之后还要后处理改写：gen_sts_soc_topo.py（2375 行，79 处读改写）用 re.sub 改端口名；ATB 要剥掉 uhdl 自动加的 _u/_d/_l 后缀。
- 4 张 NoC 的 Node/Template/Topo/Naming 结构基本一样（IniuNode/TniuNode/... 每张都有），filelist 解析、env、param+macro 双写都是复制粘贴的。RingSpDropNode.py 有两份，各 878 行。
- 测试：生成器几乎没有单元测试。

## 2. RTL
| NoC | 传输 | 头部 |
|---|---|---|
| ring | 单向环，2 VC | srcid/tgtid 4b, qos 4b, 1b vc |
| intr | 两条环 pring/nring | pld 41 = SECDED + 34b |
| mnoc | 两条环 | struct：opcode, src, tgt, txn, addr, ... |
| dti | N→1 switch 树 | payload 98, srcid 6, tgtid 6, qos 只有 1 bit |
| sts | 1→N 地址译码树 | src, txn, tgt, opcode, qos 4 |
| atb | N→1 funnel | 没有路由头 |

- 没有统一的 flit 头部和打包层，字段顺序和 qos 位宽都不一样。
- 35 个固定端口数的 wrap：dti switch 2..10to1、sts dec 1to2..16、atb funnel 2..12to1。原因是 UHDL 按位置连线（SmartAssign）。
- async bridge 有 5 种实现，default slave 5 种，link buf/pipe、reg slice、arb 各自一份。
- 参数化靠 `define/`undef（dti 106 个，sts 152 个，intr 89 个），谁先定义谁生效。`_PREFIX_` 唯一化不完整：dti 27 个模块里 21 个加了前缀，atb 59 个里只有 20 个，多实例会重名。
- 低功耗：都用 P-channel + lwnoc_lp_*，但 DTI/INTR 的 trans_idle 直接 tie 成 1；DTI TNIU sys side 没接 func_tniu，功能逻辑不会被 drain。mnoc 另写了一份私有的 lpctrl（508 行）。
- RAS：ECC 加在哪里各不相同。sts 名为 *_ecc 的信号其实是直通；ring 没有 ECC。DTI switch 遇到 unmapped 请求可能永远 stall（dti_noc_switch.sv:185,283-288，需要仿真确认）。没有事务超时。
- rtl/ 里混着 bak、tb、.vcd、for_dv、xlsx.bak 之类文件。

## 3. 验证 / 流程 / 工程
- 没有共享 VIP，基本都是定向 SV TB。dti 的 TB 主体是一个 5010 行的文件。sts 有三套互相竞争的 TB 目录。
- ring_network 完全没有验证，但它是 mnoc 和 intr 的底层。
- 覆盖率：dti 原始 79.27%，加 waiver 后算成 99%。intr 的 waiver 写死了 butterfly 拓扑。
- intr 的回归脚本是 0 字节空文件；makefile 引用了不存在的 TB top。没有 CI。
- 没有多 NoC 的系统级测试。
- 构建不可复现：gcc-4.8、/home/lgzhu 绝对路径（sts 18 处）、至少 6 种 env 约定；dti prj.env 在 RTL_PATH 赋值前就用了它。
- 依赖：子模块 commit 基本一致，但 URL/org/分支混乱，lowpower 跟的是 feature 分支，intr 的 third_party/lwnoc_mnoc 落后 77 个 commit，还有一个没有 .gitmodules 条目的 gitlink。
- 每个仓库基本只有 1 个作者（bus factor = 1），AI 和 intranet sync 提交占比高。
- noc_hdds 是最好的资产（sts/dti/atb/intr 中英 HDD，约 1.36 万行），名字级抽查和 RTL 一致；mnoc 和 ring 没有 HDD。
