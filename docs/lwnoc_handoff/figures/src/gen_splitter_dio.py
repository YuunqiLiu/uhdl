"""Burst splitter pipeline as a draw.io page, using the exact cell styles of
fliibs/toy_scalar (branch ooo-main) doc/uarch.drawio, TOP and issue pages.
Output: an uncompressed .drawio file; export with the official draw.io CLI."""
import sys, html
OUT = sys.argv[1]
C = []
n = [100]

# ---- styles copied from the reference page
S_BLOCK = 'rounded=0;whiteSpace=wrap;html=1;strokeWidth=2;fontStyle=1;'
S_THIN = 'rounded=0;whiteSpace=wrap;html=1;'
S_DASH = 'rounded=0;whiteSpace=wrap;html=1;strokeWidth=2;dashed=1;'
S_DASHL = 'rounded=0;whiteSpace=wrap;html=1;dashed=1;align=left;verticalAlign=top;strokeWidth=2;fontStyle=1;fontSize=15;spacingLeft=8;'
S_MUX = 'shape=trapezoid;perimeter=trapezoidPerimeter;whiteSpace=wrap;html=1;fixedSize=1;rotation=90;strokeWidth=2;fontStyle=1'
S_STAGE = 'text;strokeColor=none;align=center;fillColor=none;html=1;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontStyle=1;fontSize=22;'
S_LAB = 'text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;strokeWidth=2;fontSize=%d;fontStyle=1;fontColor=%s;'
S_EDGE = 'endArrow=classic;html=1;strokeWidth=2;fontStyle=1;rounded=0;'
S_REGLINE = 'endArrow=none;html=1;strokeWidth=5;rounded=0;fillColor=#d5e8d4;strokeColor=#666666;opacity=60;fontStyle=1'
S_FLEX = 'shape=flexArrow;endArrow=classic;html=1;rounded=0;fillColor=default;endWidth=14.285714285714285;endSize=2.938095238095238;width=6.666666666666666;strokeWidth=2;fontStyle=1'
BLUE_LINE, BLUE_TXT = '#6c8ebf', '#3333FF'
RED = '#FF0000'


def nid():
    n[0] += 1
    return 'x%d' % n[0]


def esc(s):
    return html.escape(s, quote=True).replace('\n', '&lt;br&gt;')


def vtx(x, y, w, h, val, style):
    C.append('<mxCell id="%s" value="%s" style="%s" vertex="1" parent="1"><mxGeometry x="%g" y="%g" width="%g" height="%g" as="geometry"/></mxCell>'
             % (nid(), esc(val), style, x, y, w, h))


def edge(pts, style=S_EDGE):
    p = pts
    mids = ''.join('<mxPoint x="%g" y="%g"/>' % q for q in p[1:-1])
    C.append('<mxCell id="%s" value="" style="%s" edge="1" parent="1"><mxGeometry width="50" height="50" relative="1" as="geometry">'
             '<mxPoint x="%g" y="%g" as="sourcePoint"/><mxPoint x="%g" y="%g" as="targetPoint"/>%s</mxGeometry></mxCell>'
             % (nid(), style, p[0][0], p[0][1], p[-1][0], p[-1][1], ('<Array as="points">%s</Array>' % mids) if mids else ''))


def block(x, y, w, h, val, reg=False, fs=None, style=S_BLOCK, color=None):
    st = style + ('fontSize=%d;' % fs if fs else '') + ('strokeColor=%s;' % color if color else '')
    vtx(x, y, w, h, val, st)
    if reg:
        edge([(x + w * 0.25, y), (x + w * 0.25, y + h)], S_REGLINE)


def mux(x, y, h, val='mux', w=30):
    """visual box (x, y, w, h); stored pre-rotation as in the reference"""
    vtx(x + w / 2 - h / 2, y + h / 2 - w / 2, h, w, val, S_MUX)


def lab(x, y, s, fs=12, color='#000000', w=None, align='center'):
    w = w or max(60, len(s) * fs * 0.62)
    st = S_LAB % (fs, color) + ('align=%s;' % align if align != 'center' else '')
    x0 = {'left': x, 'right': x - w}.get(align, x - w / 2)
    vtx(x0, y - 15, w, 30, s, st)


def line(pts, color=None, dashed=False, arrow=True, width=2):
    st = 'html=1;rounded=0;fontStyle=1;strokeWidth=%g;' % width
    st += 'endArrow=classic;endFill=1;' if arrow else 'endArrow=none;'
    if color: st += 'strokeColor=%s;' % color
    if dashed: st += 'dashed=1;'
    edge(pts, st)


def flex(x0, x1, y):
    edge([(x0, y), (x1, y)], S_FLEX)


Y0, Y1 = 90, 990          # register bars
def bar(x, val, w=70, color=None, y0=Y0, y1=Y1):
    block(x, y0, w, y1 - y0, val, reg=True, color=color)

# ------------------------------------------------------------ stage names
for x, s in ((270, 'LOAD'), (960, 'CHILD GEN'), (1475, 'STAGE1'), (1665, 'FILL'), (1960, 'DESC Q'), (2330, 'ENTRY / OUT')):
    vtx(x - 90, 20, 180, 40, s, S_STAGE)

# ------------------------------------------------------------ registers
bar(540, 'R0\n\ncurrent\nrequest')
bar(1350, 'stage0')
bar(1530, 'stage1', color=RED)
bar(1780, 'stage2')
bar(2050, 'desc_q\n\nq0 / q1')

# ------------------------------------------------------------ c0 LOAD
lab(55, 525, 's_ax', 15)
flex(20, 110, 560)
line([(110, 560), (268, 560)])
line([(75, 552), (75, 420), (138, 420)])
block(140, 380, 70, 80, 'pending', reg=True)
line([(210, 420), (240, 420), (240, 500), (268, 500)])
mux(270, 470, 120)
lab(285, 425, 'pending_vld', 12, BLUE_TXT)
line([(285, 440), (285, 476)], BLUE_LINE)
line([(300, 530), (538, 530)])
lab(410, 515, 'pld / addr', 12)
line([(320, 530), (320, 645), (338, 645)])
block(340, 600, 100, 100, 'beats\n= len + 1\n\nsplit ?')
line([(440, 630), (538, 630)]); lab(490, 618, 'beats', 12)
line([(440, 670), (538, 670)]); lab(490, 658, 'split', 12)
# load control
block(340, 210, 100, 130, 'load ctrl\n&amp; / ||\n\n!pending_vld\n!has_latched')
line([(340, 260), (30, 260)], RED, width=2.5)
lab(30, 245, 's_axrdy (comb out)', 15, RED, w=180, align='left')
line([(30, 310), (338, 310)], BLUE_LINE)
lab(30, 295, 's_axvld', 12, BLUE_TXT, w=80, align='left')
line([(440, 300), (538, 300)], RED, width=2.5)
lab(490, 288, 'en', 12, RED)

# ------------------------------------------------------------ c1 CHILD GEN
block(660, 290, 640, 530, '', style=S_DASH)
lab(670, 305, 'child gen (comb)', 15, align='left', w=200)
line([(610, 420), (678, 420)]); lab(645, 408, 'rem', 12)
block(680, 380, 100, 80, 'limit\nmin(rem, 4)')
line([(610, 545), (678, 545)]); lab(645, 533, 'orig', 12)
line([(610, 700), (1000, 700)]); lab(660, 688, 'curr_addr', 12)
line([(650, 700), (650, 595), (678, 595)])
block(680, 520, 100, 100, 'wrap\nbudget\n\nslot / to_end')
line([(610, 330), (818, 330)], BLUE_LINE); lab(700, 318, 'split_required', 12, BLUE_TXT)
line([(780, 560), (800, 560), (800, 345), (818, 345)], BLUE_LINE)
block(820, 310, 40, 50, '&amp;')
line([(860, 335), (915, 335), (915, 378)], BLUE_LINE)
lab(890, 375, 'sel', 11, BLUE_TXT)
mux(900, 380, 200)
line([(780, 420), (898, 420)])
line([(780, 600), (840, 600), (840, 540), (898, 540)]); lab(840, 615, 'to_end', 12)
line([(930, 480), (1348, 480)], width=2.5); lab(1300, 468, 'beats', 12)
# last
line([(630, 420), (630, 370), (1025, 370), (1025, 383)])
line([(960, 480), (960, 400), (998, 400)])
block(1000, 385, 50, 40, '==')
line([(1050, 405), (1348, 405)]); lab(1300, 393, 'last', 12)
line([(1070, 405), (1070, 140), (390, 140), (390, 218)], RED, dashed=True, width=2.5)
lab(730, 125, 'child_is_last -&gt; load ctrl (comb)', 15, RED, w=320)
# remaining update
line([(1025, 370), (1175, 370), (1175, 428)])
line([(1120, 480), (1120, 450), (1148, 450)])
block(1150, 430, 50, 40, '−')
# address
line([(960, 480), (960, 660), (998, 660)]); lab(975, 645, '≪6', 12)
block(1000, 620, 90, 120, 'addr\nadder\n\n40 bit')
mux(1150, 640, 120)
line([(1090, 680), (1148, 680)])
line([(730, 620), (730, 780), (1130, 780), (1130, 730), (1148, 730)])
lab(800, 768, 'wrap_base', 12)
lab(1200, 600, 'aligned / wrap sel', 11, BLUE_TXT, w=140)
# critical loops back into R0
line([(1180, 700), (1270, 700), (1270, 910), (515, 910), (515, 700), (538, 700)], RED, width=3)
line([(1200, 450), (1290, 450), (1290, 930), (500, 930), (500, 420), (538, 420)], RED, width=3)
lab(900, 955, 'next addr / remaining -&gt; R0 every child: critical loop, LOL ≈ 23', 15, RED, w=640)
# straight to stage0
line([(610, 220), (1348, 220)]); lab(1300, 208, 'first', 12)
line([(640, 700), (640, 800), (1348, 800)]); lab(1300, 788, 'addr', 12)
flex(610, 1350, 860); lab(980, 840, 'latched_pld', 12)
# launch
line([(610, 270), (1288, 270)], BLUE_LINE); lab(700, 258, 'has_latched', 12, BLUE_TXT)
block(1290, 250, 40, 45, '&amp;')
line([(1310, 295), (1310, 355), (400, 355), (400, 342)], BLUE_LINE, dashed=True)
lab(1230, 343, 'gen_launch', 12, BLUE_TXT)

# ------------------------------------------------------------ ready chain
for x, s in ((2005, 'q_rdy'), (1735, 's2_rdy'), (1460, 's1_rdy'), (1295, 's0_rdy')):
    block(x, 115, 30, 45, '||')
    lab(x + 15, 100, s, 11, BLUE_TXT)
for a, b in ((2005, 1852), (1780, 1767), (1735, 1602), (1530, 1492), (1460, 1422), (1350, 1327)):
    line([(a, 138), (b, 138)], BLUE_LINE, dashed=True, arrow=a in (2005, 1735, 1460, 1350))
line([(1310, 160), (1310, 248)], BLUE_LINE, dashed=True)
lab(1700, 70, 'ready chain: all comb, LOL ≈ 6', 13, BLUE_TXT, w=260)

# ------------------------------------------------------------ c2 STAGE1 (nothing)
for y in (220, 405, 480, 800):
    line([(1420, y), (1528, y)])
flex(1420, 1530, 860)
lab(1475, 600, 'no\nlogic', 15, RED)

# ------------------------------------------------------------ c3 FILL
for y in (220, 405, 800):
    line([(1600, y), (1778, y)])
flex(1600, 1780, 860)
line([(1600, 480), (1638, 480)])
block(1640, 450, 90, 60, 'axlen\n= beats − 1')
line([(1730, 480), (1778, 480)])

# ------------------------------------------------------------ c4 DESC Q
flex(1850, 1935, 600)
line([(1900, 600), (1900, 760), (1938, 760)])
mux(1940, 540, 120, 'q0 next')
mux(1940, 700, 120, 'q1 next')
line([(1970, 600), (2048, 600)]); line([(1970, 760), (2048, 760)])
lab(1955, 850, 'q1 -&gt; q0 shift', 11, w=110)

# ------------------------------------------------------------ c5 ENTRY / OUT
lab(2240, 80, 'entry_id_vld / entry_id  (ROB pre-alloc)', 13, BLUE_TXT, w=330)
line([(2180, 95), (2180, 278)], BLUE_LINE)
line([(2300, 95), (2300, 640), (2160, 640), (2160, 710), (2178, 710)], BLUE_LINE)
line([(2300, 560), (2368, 560)], BLUE_LINE); lab(2335, 548, 'curr_idx', 11, BLUE_TXT)
line([(2120, 295), (2158, 295)], BLUE_LINE); lab(2140, 283, 'q0_vld', 11, BLUE_TXT)
block(2160, 280, 40, 60, '&amp;')
line([(2200, 310), (2368, 310)], BLUE_LINE); lab(2330, 298, 's_vld', 11, BLUE_TXT)
line([(2220, 310), (2220, 240), (1955, 240), (1955, 538)], BLUE_LINE, dashed=True)
line([(2020, 240), (2020, 162)], BLUE_LINE, dashed=True)
lab(2090, 228, 'desc_deq', 11, BLUE_TXT)
flex(2120, 2370, 600); lab(2245, 580, 'q0: pld / first / last', 12, w=160)
block(2180, 680, 90, 60, 'prev\nentry id', reg=True)
line([(2270, 710), (2368, 710)])
block(2370, 260, 80, 600, 'RS2\nslice\n\nvld / pld\npass\n\nready\nreg', style=S_DASH + 'fontStyle=1;')
flex(2450, 2600, 560)
lab(2530, 520, 'm_ax', 15)
lab(2530, 600, 'valid in c5', 12, w=110)

# ------------------------------------------------------------ W lane
block(1600, 1030, 1010, 200, 'W channel (write side only)', style=S_DASHL)
line([(2140, 600), (2140, 1100), (2168, 1100)]); lab(2105, 1088, 'q0.beats', 11)
block(2170, 1080, 40, 45, '&amp;')
line([(2210, 1100), (2238, 1100)])
block(2240, 1045, 55, 170, 'len\nFIFO\n\n4', reg=True)
line([(2268, 1045), (2268, 1005), (2190, 1005), (2190, 342)], BLUE_LINE, dashed=True)
lab(2300, 990, 'len_fifo_rdy (full: hold AX)', 11, BLUE_TXT, w=190)
line([(2295, 1100), (2323, 1100)])
block(2325, 1080, 40, 45, '&amp;'); lab(2345, 1065, '!active', 11, BLUE_TXT)
line([(2365, 1100), (2393, 1100)])
block(2395, 1070, 90, 60, 'w_active\nremaining', reg=True)
line([(2485, 1100), (2500, 1100), (2500, 1140), (2518, 1140)])
block(2520, 1125, 45, 30, '==1')
line([(2565, 1140), (2600, 1140)]); lab(2585, 1125, 'wlast', 11, w=50)
line([(2500, 1140), (2500, 1185), (2518, 1185)])
block(2520, 1170, 45, 40, '&amp;')
line([(2565, 1190), (2600, 1190)]); lab(2585, 1175, 'm_w', 11, w=50)
line([(1620, 1205), (2518, 1205)]); lab(1680, 1192, 's_w (not registered)', 12, w=170)

# ------------------------------------------------------------ LOL row
line([(20, 1255), (2620, 1255)], '#999999', dashed=True, arrow=False, width=1)
lab(40, 1285, 'LOL', 18, w=60)
for x, s, c in ((270, 'data ≈ 6 · load en / s_axrdy ≈ 20 + fanout', RED), (960, '-&gt; stage0 ≈ 16 · R0 -&gt; R0 loop ≈ 23', RED),
                (1475, '0', RED), (1665, '≈ 3', '#000000'), (1960, '≈ 6', '#000000'), (2330, '≈ 3 (+ downstream)', '#000000')):
    lab(x, 1285, s, 15, c, w=440 if len(s) > 12 else 160)

xml = ('<mxfile host="Electron"><diagram id="splitter" name="axi_splitter"><mxGraphModel dx="2600" dy="1300" grid="1" gridSize="10" guides="1" '
       'tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
       '%s</root></mxGraphModel></diagram></mxfile>\n') % ''.join(C)
open(OUT, 'w', encoding='utf-8').write(xml)
print('wrote', OUT, len(C), 'cells')
