"""Tests for Struct, Stream, slice assignment, implicit clocks and when-blocks / fsm."""
import os, sys
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from uhdl import *
from uhdl.core.UHDLException import ErrUHDLStr
from test_lint_clean_features import needs_verilator, lint, sim

Flit = Struct(last=1, dst=3, data=8)


def comp(body, name='t'):
    class T(Component):
        MODULE_NAME = name

        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.domain(s.clk, s.rst_n)
            body(s)
    return T()


def vtext(c):
    return '\n'.join(c.verilog_def)


# ------------------------------------------------------------------ Struct
def test_struct_layout_and_view():
    assert Flit.width == 12 and Flit.bounds('last') == (11, 11) and Flit.bounds('data') == (7, 0)

    def body(s):
        s.x = Input(Flit.width); s.d = Output(3); s.p = Output(Flit.width)
        s.d += Flit(s.x).dst
        s.p += Flit.pack(last=1, dst=Flit(s.x).dst, data=0x5a)
    t = vtext(comp(body))
    assert 'assign d = x[10:8];' in t
    assert "assign p = {1'b1, x[10:8], 8'b1011010};" in t


def test_struct_errors():
    with pytest.raises(ErrUHDLStr, match='missing data'):
        comp(lambda s: Flit.pack(last=1, dst=2))
    with pytest.raises(ErrUHDLStr, match='as a 12-bit Struct'):
        comp(lambda s: Flit(s.clk))


# ------------------------------------------------------------------ slice assignment
def test_drive_vector_by_slices():
    def body(s):
        s.a, s.b = Input(4), Input(4)
        s.v = Output(10)
        s.v[3:0] += s.a
        s.v[7:4] += s.b
        s.v[9:8] += 2
    assert "assign v = {2'b10, b, a};" in vtext(comp(body))


def test_slice_coverage_errors():
    def hole(s):
        s.v = Output(4); s.v[1:0] += 1
    with pytest.raises(ErrUHDLStr, match='bits 2..3 are not driven'):
        comp(hole)

    def twice(s):
        s.v = Output(2); s.v[1:0] += 1; s.v[0] += 0
    with pytest.raises(ErrUHDLStr, match='bits 0 are driven twice'):
        comp(twice)


def test_struct_field_assignment():
    def body(s):
        s.o = Output(Flit.width)
        f = Flit(s.o)
        f.last += 1
        f.dst += 5
        f.data += 0
    assert "assign o = {1'b1, 3'b101, 8'b0};" in vtext(comp(body))


# ------------------------------------------------------------------ Stream
def test_stream_ports_and_connect():
    def body(s):
        a = s.stream_in('a', Flit)
        b = s.stream_out('b', Flit)
        b += a
    c = comp(body)
    names = [p.name for p in c.input_list + c.output_list]
    for n in ('a_vld', 'a_rdy', 'a_last', 'a_dst', 'a_data', 'b_vld', 'b_rdy', 'b_last', 'b_dst', 'b_data'):
        assert n in names
    t = vtext(c)
    assert 'assign b_vld = a_vld;' in t and 'assign a_rdy = b_rdy;' in t and 'assign b_dst = a_dst;' in t


def test_stream_lane_of_flat_vectors():
    class Core(Component):
        MODULE_NAME = 'core'

        def circuit(s):
            s.l_vld, s.l_rdy = Input(2), Output(2)
            s.l_last, s.l_dst, s.l_data = Input(2), Input(6), Input(16)
            s.l_rdy += Cat(s.l_vld[0], s.l_vld[1])
            s.mark_unused(s.l_last, s.l_dst, s.l_data)

    def body(s):
        s.core = Core()
        for e in range(2):
            src = s.stream_in(f'e{e}', Flit)
            lane = Stream.of(s.core, 'l', Flit, lane=e)
            lane += src
    t = vtext(comp(body))
    assert 'assign core_l_vld = {e1_vld, e0_vld};' in t
    assert 'assign core_l_dst = {e1_dst, e0_dst};' in t


def test_fifo_stream_ends_and_fire():
    def body(s):
        s.clk2, s.rst2_n = Input(1), Input(1)
        a = s.stream_in('a', Flit, domain=s.clk)
        b = s.stream_out('b', Flit, domain=s.clk2)
        s.f = AsyncFifo(Flit, 4, w=(s.clk, s.rst_n), r=(s.clk2, s.rst2_n))
        s.f.w += a
        b += s.f.r
        s.domain(s.clk2, s.rst2_n)
        n = s.reg('n', 4)
        n += When(b.fire).then(WrapAdd(n, 1))
        s.mark_unused(n)
    c = comp(body)
    assert c.check_cdc() == []
    t = vtext(c)
    assert '.wclk(clk)' in t.replace(' ', '') or 'assign f_wclk = clk;' in t


# ------------------------------------------------------------------ implicit clocks
class Child(Component):
    MODULE_NAME = 'child'

    def circuit(s):
        s.clk, s.rst_n = Input(1), Input(1)
        s.d, s.q = Input(1), Output(1)
        s.domain(s.clk, s.rst_n)
        r = s.reg('r', 1); r += s.d; s.q += r


def test_implicit_clock_follows_domain_at_attach():
    def body(s):
        s.clk2, s.rst2_n = Input(1), Input(1)
        s.o = Output(2)
        s.u0 = Child()                              # domain clk
        s.domain(s.clk2, s.rst2_n)
        s.u1 = Child()                              # domain clk2
        s.u0.d += 1; s.u1.d += 0
        s.o += Cat(s.u0.q, s.u1.q)
    t = vtext(comp(body))
    assert ('assign u0_clk = clk;' in t or '.clk(clk)' in t.replace(' ', '')) and \
           ('assign u1_clk = clk2;' in t or '.clk(clk2)' in t.replace(' ', ''))


def test_explicit_clock_wins():
    def body(s):
        s.clk2, s.rst2_n = Input(1), Input(1)
        s.u = Child(); s.u.clk += s.clk2; s.u.rst_n += s.rst2_n; s.u.d += 1
        s.o = Output(1); s.o += s.u.q
    t = vtext(comp(body)).replace(' ', '')
    assert '.clk(clk2)' in t and '.rst_n(rst2_n)' in t


def test_half_connected_clock_pair_is_an_error():
    def body(s):
        s.clk2 = Input(1)
        s.u = Child(); s.u.clk += s.clk2; s.u.d += 1
        s.o = Output(1); s.o += s.u.q
    with pytest.raises(ErrUHDLStr, match='rst_n is not'):
        comp(body)


# ------------------------------------------------------------------ when-blocks
def test_when_blocks_multiple_targets_priority():
    def body(s):
        s.a, s.b = Input(1), Input(1)
        x, y = s.reg('x', 4), s.reg('y', 4)
        with s.when(s.a):
            x <<= 1
            y <<= 2
        with s.when(s.b):
            x <<= 3                                  # later block wins when both a and b
    t = vtext(comp(body))
    assert "if(b) x <= 4'b11;" in t and "else if(a) x <= 4'b1;" in t
    assert "if(a) y <= 4'b10;" in t


def test_elsewhen_otherwise_nested_and_default():
    def body(s):
        s.a, s.b, s.c = Input(1), Input(1), Input(1)
        s.o = Output(2)
        s.o <<= 0                                    # default for a combinational target
        with s.when(s.a):
            with s.when(s.c):
                s.o <<= 3
        with s.elsewhen(s.b):
            s.o <<= 2
        with s.otherwise():
            s.o <<= 1
    t = vtext(comp(body))
    assert "else o = 2'b0;" in t
    assert 'if(' in t and "o = 2'b11" in t and "o = 2'b10" in t and "o = 2'b1" in t


def test_comb_without_default_is_a_latch_error():
    def body(s):
        s.a = Input(1); s.o = Output(1)
        with s.when(s.a):
            s.o <<= 1
    with pytest.raises(ErrUHDLStr, match='would be a latch'):
        comp(body)


def test_block_ordering_errors():
    def body(s):
        s.a = Input(1); x = s.reg('x', 1)
        with s.elsewhen(s.a):
            x <<= 1
    with pytest.raises(ErrUHDLStr, match='must directly follow'):
        comp(body)


def test_mixing_plus_and_block_is_multi_driver():
    def body(s):
        s.a = Input(1); x = s.reg('x', 1)
        x += s.a
        with s.when(s.a):
            x <<= 0
    with pytest.raises(ErrUHDLStr, match='already has a driver'):
        comp(body)


@needs_verilator
def test_fsm_blocks_and_streams_simulate(tmp_path):
    """A tiny packet counter: IDLE -> BUSY on a's first flit, back on last; counts packets."""
    def body(s):
        a = s.stream_in('a', Flit)
        s.npkt = Output(4)
        s.busy = Output(1)
        a.rdy += 1
        st = s.fsm('st', ['IDLE', 'BUSY'])
        n = s.reg('n', 4)
        with st.state('IDLE'):
            with s.when(a.fire & ~a.field('last')):
                st.goto('BUSY')
            with s.elsewhen(a.fire):
                n <<= WrapAdd(n, 1)
        with st.state('BUSY'):
            with s.when(a.fire & a.field('last')):
                st.goto('IDLE')
                n <<= WrapAdd(n, 1)
        s.npkt += n
        s.busy += st.is_('BUSY')
        s.mark_unused(a.field('dst'), a.field('data'))
    c = comp(body, 'pktcnt')
    paths = c.generate(str(tmp_path / 'o'))
    assert lint(paths, 'pktcnt') == []
    out = sim(tmp_path, paths, '''
        module tb;
          logic clk = 0, rst_n = 0, a_vld = 0, a_last = 0; logic [2:0] a_dst = 0; logic [7:0] a_data = 0;
          wire a_rdy, busy; wire [3:0] npkt;
          pktcnt u(.*);
          always #5 clk = ~clk;
          int err = 0;
          task send(input int len); for (int i = 0; i < len; i++) begin
            @(negedge clk); a_vld = 1; a_last = (i == len - 1); end
            @(negedge clk); a_vld = 0; endtask
          initial begin
            #12 rst_n = 1;
            send(1); if (npkt != 1 || busy) err++;
            send(3); if (npkt != 2 || busy) err++;
            @(negedge clk); a_vld = 1; a_last = 0; @(negedge clk); a_vld = 0; #1 if (!busy) err++;
            send(1); if (npkt != 3 || busy) err++;
            $display("RESULT %s err=%0d n=%0d", err == 0 ? "PASS" : "FAIL", err, npkt); $finish;
          end
        endmodule''')
    assert 'RESULT PASS' in out, out


def test_stream_with_named_packed_payload():
    def body(s):
        a = s.stream_in('rx_req', Flit, data='pld')         # one packed port rx_req_pld
        b = s.stream_out('tx', Flit, data='pld')
        b += a
        s.d = Output(3); s.d += a.payload.dst
    c = comp(body)
    names = [p.name for p in c.input_list + c.output_list]
    assert 'rx_req_pld' in names and 'tx_pld' in names and 'rx_req_dst' not in names
    assert 'assign d = rx_req_pld[10:8];' in vtext(c)


@needs_verilator
def test_reg_without_reset_multiline(tmp_path):
    def body(s):
        s.a, s.b = Input(1), Input(1); s.o = Output(4)
        r = s.reg('r', 4, rst=None)
        with s.when(s.a):
            r <<= 1
        with s.when(s.b):
            r <<= 2
        s.o += r
        s.mark_unused(s.rst_n)
    c = comp(body, 'norst')
    t = vtext(c)
    assert "if(b) r <= 4'b10;" in t and "else if(a) r <= 4'b1;" in t
    assert lint(c.generate(str(tmp_path / 'o')), 'norst') == []


def test_own_output_read_inside_while_parent_uses_it():
    """A child reads its own Output to drive a grandchild input; the parent also reads that Output."""
    class Leaf(Component):
        MODULE_NAME = 'leaf'

        def circuit(s):
            s.i, s.o = Input(1), Output(1)
            s.o += s.i

    class Mid(Component):
        MODULE_NAME = 'mid'

        def circuit(s):
            s.a, s.v, s.q = Input(1), Output(1), Output(1)
            s.v += s.a
            s.leaf = Leaf()
            s.leaf.i += s.v & s.a                 # reads its own output v
            s.q += s.leaf.o

    def body(s):
        s.x, s.y, s.z = Input(1), Output(1), Output(1)
        s.m = Mid()
        s.m.a += s.x
        s.y += s.m.v                              # the parent reads v too
        s.z += s.m.q
    t = comp(body, 'own_out')
    mid = '\n'.join(t.m.verilog_def)
    assert 'm_v' not in mid and '(v & a)' in mid
