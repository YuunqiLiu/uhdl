"""Generate /workspace/lwnoc_dev/analysis/axi_splitter_pipeline.html.

Style follows NexEvic/de_cases openc910 fp16_sfu microarchitecture figures:
time flows downward, one green bar per register stage, combinational logic
between bars, dashed stage cuts, plus a LOL (logic levels) column on the right.
"""
import html, sys

OUT = sys.argv[1]
W, H = 1440, 2010
parts = []
E = html.escape


def text_lines(x, y, lines, cls='t', anchor='start', lh=20):
    out = []
    for i, ln in enumerate(lines):
        out.append('<text class="%s" x="%d" y="%d" text-anchor="%s">%s</text>' % (cls, x, y + i * lh, anchor, E(ln)))
    return ''.join(out)


def box(x, y, w, h, lines, kind='comp', first_bold=True, lh=20, pad=12):
    if kind == 'mux':
        d = 'M%d,%d L%d,%d L%d,%d L%d,%d Z' % (x, y, x + w, y, x + w - 28, y + h, x + 28, y + h)
        parts.append('<path class="mux" d="%s"/>' % d)
        cx = x + w / 2
        ty = y + (h - (len(lines) - 1) * lh) / 2 + 5
        for i, ln in enumerate(lines):
            parts.append('<text class="%s" x="%d" y="%d" text-anchor="middle">%s</text>'
                         % ('tb' if (i == 0 and first_bold) else 't', cx, ty + i * lh, E(ln)))
        return
    parts.append('<rect class="%s" x="%d" y="%d" width="%d" height="%d"/>' % (kind, x, y, w, h))
    ty = y + 22
    for i, ln in enumerate(lines):
        parts.append('<text class="%s" x="%d" y="%d">%s</text>'
                     % ('tb' if (i == 0 and first_bold) else 't', x + pad, ty + i * lh, E(ln)))


def store(x, y, w, h, title, sig, hot=False):
    parts.append('<rect class="store%s" x="%d" y="%d" width="%d" height="%d"/>' % (' hotreg' if hot else '', x, y, w, h))
    parts.append('<line class="storeline" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (x + 1, y + h - 3, x + w - 1, y + h - 3))
    parts.append('<text class="tb" x="%d" y="%d">▥ %s</text>' % (x + 12, y + 23, E(title)))
    for i, s in enumerate(sig):
        parts.append('<text class="t" x="%d" y="%d">%s</text>' % (x + 12, y + 44 + i * 19, E(s)))


def cut(y, label, sub=None):
    parts.append('<line class="cut" x1="160" y1="%d" x2="%d" y2="%d"/>' % (y, W - 20, y))
    parts.append('<text class="stage" x="24" y="%d">%s</text>' % (y - 8, E(label)))



def region(y, label):
    parts.append('<text class="region" x="24" y="%d">%s</text>' % (y, E(label)))


def arrow(pts, kind='data'):
    p = ' '.join('%d,%d' % q for q in pts)
    mk = {'data': 'a', 'ctrl': 'c', 'hot': 'h'}[kind]
    parts.append('<polyline class="%s" points="%s" marker-end="url(#%s)"/>' % (kind, p, mk))


def label(x, y, s, cls='lab', anchor='start'):
    parts.append('<text class="%s" x="%d" y="%d" text-anchor="%s">%s</text>' % (cls, x, y, anchor, E(s)))


# ---------------- columns
MX0, MX1 = 190, 760          # main datapath
CX0, CX1 = 795, 1040         # control / ready
WX0, WX1 = 1062, 1252        # W channel
LX0 = 1278                   # LOL bars start
LPX = 5                      # px per logic level

# ---------------- column headers
for x, s in (((MX0 + MX1) // 2, 'AR/AW 子请求通路'), ((CX0 + CX1) // 2, '装载判定与 ready 链'),
             ((WX0 + WX1) // 2, 'W 通道（仅写）'), (LX0 + 70, 'LOL（估算）')):
    label(x, 132, s, 'colh', 'middle')
# LOL scale
for lv in (0, 10, 20):
    x = LX0 + lv * LPX
    parts.append('<line class="tick" x1="%d" y1="140" x2="%d" y2="%d"/>' % (x, x, H - 150))
    label(x, 153, str(lv), 'tickl', 'middle')

LOL = []   # (y, name, levels, hot, extra)

# ---------------- input
box(360, 165, 400, 46, ['s_ax：AR/AW 来自上游（u_ar_fifo / AW 切片）'], 'port', first_bold=False)

# ---------------- cycle 0 region
region(300, '第 0 拍')
store(MX0, 230, 150, 66, 'pending', ['忙时暂存 1 个'])
arrow([(380, 211), (380, 222), (265, 222), (265, 228)])
box(360, 228, 400, 46, ['装载选择：pending_vld ? pending_pld : s_axpld'], 'mux', first_bold=False)
arrow([(340, 262), (358, 262)])
arrow([(560, 211), (560, 226)])
box(360, 290, 400, 66, ['beats = axlen + 1；要不要拆 =', '(INCR 或 WRAP) 且 beats > 4'], 'comp', first_bold=False)
arrow([(560, 274), (560, 288)])
arrow([(560, 356), (560, 374)])
LOL.append((268, '装载数据', 6, False, ''))

box(CX0, 165, CX1 - CX0, 152, ['装载判定', 'needs_load = !has_latched ||', '  (gen_launch && child_is_last)',
                                's_axrdy = !pend_vld || needs_load', 'active_load → R0 写使能'], 'ctrl')
arrow([(CX0, 196), (762, 196)], 'ctrl')
label(778, 188, 's_axrdy', 'labc', 'end')
arrow([(CX0 + 30, 317), (CX0 + 30, 362), (720, 362), (720, 374)], 'ctrl')
label(CX0 + 38, 345, 'active_load', 'labc')
LOL.append((318, '装载使能 / s_axrdy', 20, True, '+扇出'))

# ---------------- R0
store(MX0, 376, MX1 - MX0, 84, 'R0  当前请求寄存器', [
    'latched_pld · orig_beats[5] · split_required · has_latched · gen_first_child',
    'curr_addr_q[40] · remaining_beats_q[5]   （每发一个子请求更新一次）'])
cut(460, '第 0 拍末', 'R0 装载')

# ---------------- cycle 1 region
region(620, '第 1 拍')
box(MX0, 478, 260, 66, ['限长', 'limited = min(remaining, 4)'])
box(480, 478, 280, 80, ['回绕余量（仅 WRAP）', 'slot = (addr≫6) & (orig−1)', 'to_end = orig − slot'], pad=10)
arrow([(320, 544), (320, 566)])
arrow([(620, 558), (620, 566)])
box(MX0, 568, MX1 - MX0, 56, ['child_beats：不拆 → remaining；WRAP 且 to_end < limited → to_end；否则 limited'], 'mux', first_bold=False)
arrow([(300, 624), (300, 646)])
arrow([(600, 624), (600, 646)])
box(MX0, 648, 250, 66, ['child_is_last', 'remaining == child_beats'])
box(470, 648, 290, 86, ['下一地址', '对齐地址 + child_beats≪6（40 位加）', '回绕点处改选 wrap_base', 'remaining −= child_beats'])
parts[-5] = parts[-5].replace('class="comp"', 'class="comp hotbox"')
# loop back into R0
arrow([(760, 700), (778, 700), (778, 420), (762, 420)], 'hot')
label(786, 560, '每拍回送 curr_addr /', 'labh')
label(786, 578, 'remaining（关键环路）', 'labh')
# is_last back to load decision
arrow([(315, 714), (315, 752), (990, 752), (990, 319)], 'ctrl')
label(982, 745, 'child_is_last 组合回到装载判定', 'labc', 'end')
for x in (300, 600):
    arrow([(x, 714 if x == 300 else 734), (x, 776)])
LOL.append((598, '子请求字段 → stage0', 16, False, ''))
LOL.append((690, '下一地址环路 R0 → R0', 23, True, ''))

# ---------------- R1 stage0
store(MX0, 778, MX1 - MX0, 64, 'R1  gen_stage0', ['pld · addr · beats · burst · first_flag · last_flag'])
cut(842, '第 1 拍末', 'stage0')

# ---------------- cycle 2: nothing
region(886, '第 2 拍')
parts.append('<rect class="empty" x="%d" y="858" width="%d" height="44"/>' % (MX0, MX1 - MX0))
label((MX0 + MX1) // 2, 885, '无组合逻辑：stage0 原样打一拍到 stage1', 'labh', 'middle')
arrow([(475, 842), (475, 856)])
arrow([(475, 902), (475, 916)])
LOL.append((882, '原样寄存', 0, True, ''))

store(MX0, 918, MX1 - MX0, 64, 'R2  gen_stage1', ['与 stage0 完全相同'], hot=True)
cut(982, '第 2 拍末', 'stage1')

# ---------------- cycle 3
region(1030, '第 3 拍')
box(MX0, 998, MX1 - MX0, 50, ['axlen = beats − 1；axaddr ← addr；axburst ← burst（填回 payload）'], first_bold=False)
arrow([(475, 982), (475, 996)])
arrow([(475, 1048), (475, 1062)])
LOL.append((1024, 'axlen = beats−1', 3, False, ''))

store(MX0, 1064, MX1 - MX0, 64, 'R3  gen_stage2', ['child_desc = {pld, beats, first_flag, last_flag}'])
cut(1128, '第 3 拍末', 'stage2')

# ---------------- cycle 4
region(1176, '第 4 拍')
box(MX0, 1144, MX1 - MX0, 52, ['desc_q 入队 / 移位：q0、q1 按出队与入队选新值'], 'mux', first_bold=False)
arrow([(475, 1128), (475, 1142)])
arrow([(475, 1196), (475, 1210)])
LOL.append((1172, 'desc_q 选择', 6, False, ''))

store(MX0, 1212, MX1 - MX0, 64, 'R4  desc_q（2 项）', ['q0：队头，等 ROB 表项号     q1：第二项'])
cut(1276, '第 4 拍末', 'desc_q')

# ready chain (control column) from cycle 4 up to the load decision
box(CX0, 1144, CX1 - CX0, 70, ['desc_deq = 表项号握手', 'desc_q_ready = !q1_vld || deq'], 'ctrl')
arrow([(1025, 1144), (1025, 319)], 'ctrl')
for y, s in ((1100, 's2_rdy = !s2_vld || q_rdy'), (958, 's1_rdy = !s1_vld || s2_rdy'),
             (818, 's0_rdy = !s0_vld || s1_rdy'), (836, 'launch = has_latched && s0_rdy')):
    label(1017, y, s, 'labc', 'end')
label(1017, 1062, 'ready 链：全组合，约 6 级', 'labc', 'end')

# ---------------- cycle 5
region(1400, '第 5 拍')
store(MX0, 1292, 175, 64, 'prev_entry_id', ['出队时记下表项号'])
box(390, 1292, 370, 88, ['表项号对接', 's_vld = q0_vld && entry_id_vld', '        && len_fifo_rdy', '拼上 curr = entry_id、prev'])
arrow([(475, 1276), (475, 1290)])
arrow([(365, 1324), (388, 1324)])
box(390, 1396, 370, 44, ['RS2 切片：valid / payload 直通，只寄存 ready'], 'mux', first_bold=False)
arrow([(575, 1380), (575, 1394)])
box(390, 1456, 370, 48, ['m_ax：第 5 拍有效 → 同拍组合进入下游'], 'port', first_bold=False)
arrow([(575, 1440), (575, 1454)])
label(MX0, 1530, '（下游 tgt_resolver / behavior map 在同一拍接着算）', 'note')
LOL.append((1350, '对接 + 切片', 3, False, '+下游'))

box(CX0, 1292, CX1 - CX0, 48, ['entry_id_vld / entry_id', 'ROB 预分配，组合输入'], 'port')
arrow([(CX0, 1316), (762, 1316)])
arrow([(CX0 + 120, 1292), (CX0 + 120, 1216)], 'ctrl')

# W channel
box(WX0, 1292, WX1 - WX0, 72, ['长度 FIFO 入队', 'q0 出队时写 beats'], 'wcomp')
arrow([(762, 1356), (WX0 - 2, 1356)])
label(CX0 + 4, 1350, 'q0.beats', 'lab')
arrow([(WX0, 1372), (778, 1372), (778, 1346), (762, 1346)], 'ctrl')
label(CX0 + 4, 1388, 'len_fifo_rdy（满则不发 AX）', 'labc')
cut(1548, '第 5 拍末', '长度 FIFO')
store(WX0, 1484, WX1 - WX0, 64, '长度 FIFO', ['4 项寄存器 FIFO'])
arrow([(1157, 1364), (1157, 1482)])

region(1604, '第 6 拍')
box(WX0, 1566, WX1 - WX0, 66, ['取出子请求长度', '!active && out_vld'], 'wcomp')
arrow([(1157, 1548), (1157, 1564)])
arrow([(1157, 1632), (1157, 1650)])
store(WX0, 1652, WX1 - WX0, 64, 'W 放行状态', ['w_child_active · 剩余拍数'])
cut(1716, '第 6 拍末', 'W 放行状态')
LOL.append((1600, '取出长度', 2, False, ''))

region(1790, '第 7 拍')
box(390, 1740, 370, 48, ['s_w：W 数据（直通，不寄存）'], 'port', first_bold=False)
box(WX0, 1732, WX1 - WX0, 110, ['W 放行门', 'm_wvld = act && s_wvld', 's_wrdy = act && m_wrdy', 'wlast = 剩余 == 1'], 'wcomp')
arrow([(760, 1764), (WX0 - 2, 1764)])
arrow([(1157, 1716), (1157, 1730)])
box(WX0, 1858, WX1 - WX0, 44, ['m_w：第 7 拍起放行'], 'port', first_bold=False)
arrow([(1157, 1842), (1157, 1856)])
LOL.append((1786, 'W 放行门', 3, False, '+m_wrdy 直通'))

# ---------------- LOL bars
for y, name, lv, hot, extra in LOL:
    label(LX0, y - 10, name, 'loln')
    if lv:
        parts.append('<rect class="%s" x="%d" y="%d" width="%d" height="13"/>' % ('lolh' if hot else 'lolb', LX0, y - 4, lv * LPX))
    label(LX0 + max(lv * LPX, 2) + 6, y + 7, ('%d' % lv) + ((' ' + extra) if extra else ''), 'lolv')

svg = ''.join(parts)

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#fff;color:#17344b;font-family:"Noto Sans CJK SC","Source Han Sans SC","PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1440px;margin:0 auto;padding:20px 16px 40px}
h1{font-size:26px;margin:0 0 6px}
.sub{margin:0 0 4px;color:#45606f;font-size:15px;line-height:1.6;max-width:110ch}
.fig{overflow-x:auto}
svg{display:block;width:100%;min-width:1100px;height:auto}
svg text{font-family:inherit}
.t{font-size:14px;fill:#17344b}
.tb{font-size:14px;font-weight:700;fill:#17344b}
.comp{fill:#fff0db;stroke:#c79961;stroke-width:1.5}
.hotbox{fill:#fde3d3;stroke:#b4531c;stroke-width:2.2}
.wcomp{fill:#eef6ee;stroke:#86a98a;stroke-width:1.5}
.ctrl{fill:#fff8e6;stroke:#bc965d;stroke-width:1.5}
polyline.ctrl{fill:none;stroke:#9c6828;stroke-width:1.8;stroke-dasharray:7 5}
.port{fill:#eaf3ff;stroke:#7099bb;stroke-width:1.5}
.mux{fill:#ffe8be;stroke:#d2a75d;stroke-width:1}
.store{fill:#e6f1df;stroke:#769568;stroke-width:1.5}
.hotreg{stroke:#b4531c;stroke-width:2.4}
.storeline{stroke:#c9ddbd;stroke-width:5}
.empty{fill:none;stroke:#b4531c;stroke-width:1.5;stroke-dasharray:5 4}
.cut{stroke:#93a5b3;stroke-width:1.6;stroke-dasharray:7 6}
.stage{font-size:15px;font-weight:700;fill:#244f6c}
.region{font-size:13px;fill:#8195a3}
.note{font-size:12.5px;fill:#6a7f8d}
.colh{font-size:15px;font-weight:700;fill:#244f6c}
.tick{stroke:#e3e9ee;stroke-width:1}
.tickl{font-size:12px;fill:#8195a3}
.data{fill:none;stroke:#24628a;stroke-width:2}
.hot{fill:none;stroke:#b4531c;stroke-width:2.4}
.lab{font-size:12.5px;fill:#24628a}
.labc{font-size:12.5px;fill:#9c6828}
.labh{font-size:13px;fill:#b4531c;font-weight:700}
.loln{font-size:12px;fill:#45606f}
.lolv{font-size:12.5px;fill:#17344b;font-weight:700}
.lolb{fill:#7f9fb8}
.lolh{fill:#d0763d}
.foot{font-size:14px;line-height:1.75;color:#334e5f;max-width:120ch}
.foot ul{margin:6px 0 0;padding-left:1.2em}
code{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:.92em}
"""

doc = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>突发拆分器逐拍微架构</title><style>%s</style></head>
<body><div class="wrap">
<h1>突发拆分器｜逐拍寄存与组合逻辑</h1>
<p class="sub">时间向下。第 0 拍收下 AR/AW；每条绿色横条是一级寄存器，横条之间是这一拍的组合逻辑；最右列是每段组合逻辑的级数（LOL）。源码 <code>niu_base/lwmnoc_axi_splitter.sv</code>，读写各一份，W 通道只在写侧。</p>
<p class="sub">LOL 估算参数：ARLEN 4 位（最长 16 拍）、数据 512 位（地址步进左移 6）、地址 40 位、ROB 64 项。</p>
<div class="fig"><svg viewBox="0 105 %d %d" role="img" aria-label="突发拆分器逐拍图：R0 当前请求寄存器、stage0、stage1、stage2、desc_q 五级寄存器，第 5 拍输出子请求；第 2 拍没有组合逻辑；最长的组合逻辑是 R0 到 R0 的下一地址环路，约 23 级。写通道的 W 从第 7 拍开始放行。">
<defs>
<marker id="a" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#24628a"/></marker>
<marker id="c" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="8" markerHeight="8" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#9c6828"/></marker>
<marker id="h" viewBox="0 0 8 8" refX="8" refY="4" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#b4531c"/></marker>
</defs>
%s
</svg></div>
<div class="foot">
<p>▥：寄存器；橙色方框：组合逻辑；梯形：选择器；蓝线：数据；棕色虚线：控制 / ready；橙红：关键路径或冗余的一级。</p>
<ul>
<li><b>关键路径在第 1 拍的下一地址环路（约 23 级）</b>：R0 → 限长 / 回绕余量 → child_beats → 40 位加法 → 回绕选择 → 写回 R0。拆分时每拍出一个子请求靠的就是这个环路，不能简单插寄存器。</li>
<li><b>装载使能和 s_axrdy 约 20 级，并且 s_axrdy 是组合输出</b>：它经过 child_is_last，再加上 ready 链（约 6 级，起点是 ROB 的 entry_id_vld），直接送到上游，跨模块串成一条组合路径。active_load 还要驱动 R0 几百位寄存器的写使能，扇出大。</li>
<li><b>第 2 拍没有任何组合逻辑</b>：stage1 只是把 stage0 原样打一拍，第 3 拍也只有 axlen = beats−1 一个 4 位减法（约 3 级）。按逻辑量看，第 2、3 拍可以并成一拍，或把 stage0 的字段直接算好，省掉 1 拍。</li>
<li><b>第 5 拍的输出不寄存</b>：切片是 RS_TYPE=2，valid 和 payload 直通，所以 m_ax 在第 5 拍组合进入下游的 tgt_resolver / behavior map，那一侧的逻辑要接着算在同一拍里。</li>
<li><b>W 通道</b>：子请求在第 5 拍发出时写长度 FIFO，第 6 拍取出，第 7 拍起放行 W。W 数据本身不寄存，s_wrdy 组合依赖下游的 m_wrdy。</li>
<li>LOL 按 2 输入门等效粗估：5 位比较 / 加减约 3–4 级，40 位加法按前缀加法器约 8 级，2 选 1 约 1 级；综合结果会有出入。现在的示例配置 <code>INIU_AXI_MAX_BURST_LEN=4</code> 下请求永远不拆，第 1 拍的逻辑大部分会被常量化简，但 5 拍延迟照样存在。</li>
</ul>
<p>参考画法：<code>NexEvic/de_cases</code> openc910 fp16_sfu 的微架构图（时间向下、每拍一条边界、寄存器横条 + 组合逻辑框）。</p>
</div>
</div></body></html>
""" % (CSS, W, H - 105, svg)

open(OUT, 'w', encoding='utf-8').write(doc)
print('wrote', OUT, len(doc))
