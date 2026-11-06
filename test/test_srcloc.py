"""Errors and generated Verilog point back at the Python line that caused them (uhdl.core.SrcLoc)."""
import os, re, sys
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from uhdl import *
from uhdl.core.UHDLException import ErrUHDL

HERE = os.path.abspath(__file__)
SRC = open(HERE).read().splitlines()


def line_of(marker):
    '''Line number of the (single) source line ending with the comment `# @marker`.'''
    hits = [i + 1 for i, l in enumerate(SRC) if l.rstrip().endswith('# @' + marker)]
    assert len(hits) == 1, marker
    return hits[0]


def loc(marker):
    return '%s:%d' % (os.path.basename(HERE), line_of(marker))


def err_of(make):
    with pytest.raises(ErrUHDL) as e:
        make()
    return str(e.value)


def first_line(msg):
    return msg.splitlines()[0]


# ---------------------------------------------------------------- errors raised at once
def test_width_mismatch_points_at_the_assignment():
    class T(Component):
        def circuit(s):
            s.a = Input(2); s.y = Output(1)
            s.y += s.a  # @width
    msg = err_of(T)
    assert first_line(msg).endswith('%s: s.y += s.a  # @width' % loc('width')), msg
    assert 'Attribute Mismatch' in msg or 'attribute' in msg


def test_second_driver_names_both_lines():
    class T(Component):
        def circuit(s):
            s.a, s.b = Input(1), Input(1); s.y = Output(1)
            s.y += s.a  # @drv1
            s.y += s.b  # @drv2
    msg = err_of(T)
    assert loc('drv2') in first_line(msg)
    assert re.search(r'first driver: .*%s' % re.escape(loc('drv1')), msg), msg


def test_error_inside_a_child_points_at_the_child_line():
    class Leaf(Component):
        def circuit(s):
            s.a = Input(4); s.y = Output(4)
            s.y += s.a[5:2]  # @leaf
    class Top(Component):
        def circuit(s):
            s.u = Leaf()
    assert loc('leaf') in first_line(err_of(Top))


def test_error_in_a_user_helper_points_at_the_helper():
    def connect(dst, src):
        dst += src  # @helper
    class T(Component):
        def circuit(s):
            s.a = Input(3); s.y = Output(1)
            connect(s.y, s.a)
    assert loc('helper') in first_line(err_of(T))


# ---------------------------------------------------------------- errors found after circuit()
def test_latch_points_at_the_when_assignments():
    class T(Component):
        def circuit(s):
            s.c, s.a = Input(1), Input(1); s.y = Output(1)
            with s.when(s.c):
                s.y <<= s.a  # @latch
    msg = err_of(T)
    assert loc('latch') in first_line(msg) and 'latch' in msg
    assert 'declared:' in msg


def test_width_mismatch_inside_when_points_at_the_block():
    class T(Component):
        def circuit(s):
            s.c, s.a = Input(1), Input(3); s.y = Output(1)
            s.y <<= 0  # @wdef
            with s.when(s.c):
                s.y <<= s.a  # @wbad
    msg = err_of(T)
    assert loc('wbad') in first_line(msg) and '3-bit value' in msg, msg


def test_slice_coverage_lists_the_slice_lines():
    class T(Component):
        def circuit(s):
            s.a = Input(2); s.y = Output(4)
            s.y[1:0] += s.a  # @sl1
            s.y[2:1] += s.a  # @sl2
    msg = err_of(T)
    assert 'driven twice' in msg and loc('sl1') in msg and loc('sl2') in msg, msg


def test_half_connected_clock_points_at_the_instance():
    class Leaf(Component):
        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1); s.d = Input(1); s.q = Output(1)
            s.domain(s.clk, s.rst_n)
            r = s.reg('r', 1); r += s.d; s.q += r
    class Top(Component):
        def circuit(s):
            s.clk, s.rst_n, s.d = Input(1), Input(1), Input(1); s.q = Output(1)
            s.u = Leaf()  # @inst
            s.u.clk += s.clk; s.u.d += s.d; s.q += s.u.q
    assert loc('inst') in first_line(err_of(Top))


def test_cdc_violation_names_the_registers(tmp_path):
    class T(Component):
        def circuit(s):
            s.ca, s.ra, s.cb, s.rb = Input(1), Input(1), Input(1), Input(1)
            s.d = Input(1); s.q = Output(1)
            s.domain(s.ca, s.ra)
            a = s.reg('a', 1)  # @cdc_src
            a += s.d
            s.domain(s.cb, s.rb)
            b = s.reg('b', 1)
            b += a  # @cdc_dst
            s.q += b
    t = T()
    msg = err_of(lambda: t.generate(str(tmp_path)))
    assert 'unsynchronized crossing' in msg and loc('cdc_src') in msg and loc('cdc_dst') in msg, msg


# ---------------------------------------------------------------- comments in generated Verilog
class Leaf(Component):
    def circuit(s):
        s.a = Input(4); s.y = Output(4)
        s.y += ~s.a  # @v_assign


class Top(Component):
    def circuit(s):
        s.clk, s.rst_n = Input(1), Input(1)
        s.domain(s.clk, s.rst_n)
        s.a, s.c = Input(4), Input(1); s.y, s.z, s.m_o = Output(4), Output(4), Output(4)  # @v_ports
        s.u = Leaf()  # @v_inst
        s.u.a += s.a  # @v_subin
        s.y += s.u.y  # @v_out
        r = s.reg('r', 4)  # @v_regdecl
        with s.when(s.c):
            r <<= s.a  # @v_reg1
        with s.elsewhen(s.a.eq(3)):
            r <<= 0  # @v_reg2
        s.z += r
        m = s.mem('m', 4, 4)
        m.write(s.c, s.a[1:0], s.a)  # @v_mem
        s.m_o += m[s.a[1:0]]


def _gen(tmp_path, **kw):
    paths = Top().generate(str(tmp_path), **kw)
    return {os.path.basename(p): open(p).read() for p in paths}


def _line_with(text, needle):
    hits = [l for l in text.splitlines() if needle in l]
    assert hits, needle
    return hits[0]


def test_generated_verilog_names_the_python_lines(tmp_path):
    v = _gen(tmp_path)
    leaf, top = v['Leaf.v'], v['Top.v']
    f = os.path.basename(HERE)
    assert _line_with(leaf, 'assign y').endswith('// %s:%d' % (f, line_of('v_assign')))
    assert _line_with(top, 'Leaf u').endswith('// %s:%d' % (f, line_of('v_inst')))
    assert _line_with(top, '.a(a)').endswith('// %s:%d' % (f, line_of('v_subin')))
    assert _line_with(top, '.y(y)').endswith('// %s:%d' % (f, line_of('v_out')))
    assert _line_with(top, 'always @(posedge clk').endswith('// %s:%d,%d' % (f, line_of('v_reg1'), line_of('v_reg2')))
    assert _line_with(top, '] <= a;').endswith('// %s:%d' % (f, line_of('v_mem')))
    assert re.search(r'input\s+\[3:0\]\s+a\s*,\s*// %s:%d$' % (f, line_of('v_ports')), _line_with(top, ' a ')), _line_with(top, ' a ')
    assert _line_with(top, 'reg ').endswith('// %s:%d' % (f, line_of('v_regdecl')))


def test_comments_can_be_turned_off_and_do_not_leak(tmp_path):
    assert '// test_srcloc.py' not in ''.join(_gen(tmp_path, src_comments=False).values())
    assert '// test_srcloc.py' not in '\n'.join(Top().verilog_def)   # only generate() adds them


def test_generated_verilog_with_comments_lints_clean(tmp_path):
    from test_lint_clean_features import VERILATOR, lint
    if VERILATOR is None:
        pytest.skip('verilator not installed')
    paths = Top().generate(str(tmp_path / 'o'))
    assert lint(paths, 'Top') == []
