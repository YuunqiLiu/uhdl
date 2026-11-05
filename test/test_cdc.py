"""Tests for check_cdc() and the CDC cells (CdcSync, CdcBus, AsyncFifo)."""
import os, sys
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from uhdl import *
from uhdl.core.UHDLException import ErrUHDLStr
from test_lint_clean_features import needs_verilator, lint, sim


def two_clock(body):
    class T(Component):
        MODULE_NAME = 'cdc_t'

        def circuit(s):
            s.clka, s.rsta_n, s.clkb, s.rstb_n = Input(1), Input(1), Input(1), Input(1)
            body(s)
    return T()


def good(s):
    s.a_in = Input(4, domain=s.clka)
    s.b_out = Output(1, domain=s.clkb)
    s.b_cnt = Output(4, domain=s.clkb)
    s.b_dat = Output(4, domain=s.clkb)
    s.b_vld = Output(1, domain=s.clkb)
    s.domain(s.clka, s.rsta_n)
    flag = s.reg('flag', 1)
    flag += s.a_in.eq(3)
    cnt = s.reg('cnt', 4)
    cnt += WrapAdd(cnt, 1)
    s.sync = CdcSync()
    s.sync.clk += s.clkb; s.sync.rst_n += s.rstb_n; s.sync.d += flag
    s.bus = CdcBus(4)
    s.bus.src_clk += s.clka; s.bus.src_rst_n += s.rsta_n; s.bus.src_data += cnt
    s.bus.dst_clk += s.clkb; s.bus.dst_rst_n += s.rstb_n
    s.fifo = AsyncFifo(4, 4)
    s.fifo.wclk += s.clka; s.fifo.wrst_n += s.rsta_n; s.fifo.w_vld += 1; s.fifo.w_data += s.a_in
    s.fifo.rclk += s.clkb; s.fifo.rrst_n += s.rstb_n; s.fifo.r_rdy += 1
    s.domain(s.clkb, s.rstb_n)
    r = s.reg('r', 1)
    r += s.sync.q
    s.b_out += r
    s.b_cnt += s.bus.dst_data
    s.b_dat += s.fifo.r_data
    s.b_vld += s.fifo.r_vld
    s.mark_unused(s.fifo.w_rdy)


def test_good_design_is_clean(tmp_path):
    t = two_clock(good)
    assert t.check_cdc() == []
    t.generate(str(tmp_path / 'o'))                  # cdc_check runs inside generate()


def _bad(body, pattern):
    t = two_clock(body)
    v = t.check_cdc()
    assert any(pattern in x for x in v), v
    with pytest.raises(ErrUHDLStr, match='clock-domain crossing'):
        t.generate('/nonexistent_dir_never_written')


def test_direct_reg_to_reg():
    def body(s):
        s.domain(s.clka, s.rsta_n); a = s.reg('a', 1); a += ~a
        s.domain(s.clkb, s.rstb_n); b = s.reg('b', 1); b += a
        s.o = Output(1); s.o += b
    _bad(body, 'unsynchronized crossing: TOP.a')


def test_logic_before_sync():
    def body(s):
        s.domain(s.clka, s.rsta_n)
        a1, a2 = s.reg('a1', 1), s.reg('a2', 1); a1 += ~a1; a2 += a1
        s.sync = CdcSync(); s.sync.clk += s.clkb; s.sync.rst_n += s.rstb_n
        s.sync.d += a1 | a2
        s.o = Output(1); s.o += s.sync.q
    _bad(body, 'logic in front of a synchronizer')


def test_reconvergent_syncs():
    def body(s):
        s.domain(s.clka, s.rsta_n)
        c = s.reg('c', 2); c += WrapAdd(c, 1)
        for i in range(2):
            x = s.create(f's{i}', CdcSync()); x.clk += s.clkb; x.rst_n += s.rstb_n; x.d += c[i]
        s.domain(s.clkb, s.rstb_n)
        b = s.reg('b', 2); b += Cat(s.s0.q, s.s1.q)
        s.o = Output(2); s.o += b
    _bad(body, 'reconvergent synchronizers')


def test_syncs_from_different_domains_may_meet():
    def body(s):
        s.clkc, s.rstc_n = Input(1), Input(1)
        s.domain(s.clka, s.rsta_n); a = s.reg('a', 1); a += ~a
        s.domain(s.clkc, s.rstc_n); c = s.reg('c', 1); c += ~c
        for n, src in (('sa', a), ('sc', c)):
            x = s.create(n, CdcSync()); x.clk += s.clkb; x.rst_n += s.rstb_n; x.d += src
        s.domain(s.clkb, s.rstb_n); b = s.reg('b', 1); b += s.sa.q | s.sc.q
        s.o = Output(1); s.o += b
    assert two_clock(body).check_cdc() == []


def test_annotated_input_to_other_domain():
    def body(s):
        s.ain = Input(1, domain=s.clka)
        s.domain(s.clkb, s.rstb_n); b = s.reg('b', 1); b += s.ain
        s.o = Output(1); s.o += b
    _bad(body, 'TOP.ain (clock TOP.clka) -> TOP.b')


def test_mem_read_in_other_domain():
    def body(s):
        s.domain(s.clka, s.rsta_n)
        m = s.mem('m', 4, 4); m.write(1, 0, 5)
        s.domain(s.clkb, s.rstb_n); b = s.reg('b', 4); b += m[0]
        s.o = Output(4); s.o += b
    _bad(body, 'unsynchronized crossing')


def test_annotated_output_driven_from_other_domain():
    def body(s):
        s.o = Output(1, domain=s.clkb)
        s.domain(s.clka, s.rsta_n); a = s.reg('a', 1); a += ~a
        s.o += a
    _bad(body, '-> TOP.o (clock TOP.clkb)')


def test_cdc_check_can_be_disabled(tmp_path):
    def body(s):
        s.domain(s.clka, s.rsta_n); a = s.reg('a', 1); a += ~a
        s.domain(s.clkb, s.rstb_n); b = s.reg('b', 1); b += a
        s.o = Output(1); s.o += b
    two_clock(body).generate(str(tmp_path / 'o'), cdc_check=False)


@needs_verilator
def test_cells_simulate(tmp_path):
    paths = two_clock(good).generate(str(tmp_path / 'o'))
    assert lint(paths, 'cdc_t') == []
    out = sim(tmp_path, paths, '''
        module tb;
          logic clka = 0, clkb = 0, rsta_n = 0, rstb_n = 0; logic [3:0] a_in = 0;
          wire b_out, b_vld; wire [3:0] b_cnt, b_dat;
          cdc_t u(.*);
          always #5 clka = ~clka;
          always #7 clkb = ~clkb;
          int err = 0, ebus = 0, efifo = 0, got = 0, steps = 0; logic [3:0] last = 0, expect_dat = 0;
          initial begin
            #30 rsta_n = 1; rstb_n = 1;
          end
          always @(negedge clka) if (rsta_n && u.fifo.w_rdy) a_in <= a_in + 1;   // stream 0,1,2,... into the fifo
          always @(posedge clkb) if (rstb_n) begin
            // CdcBus: dst value only moves forward (mod 16) by less than half the range
            if (b_cnt != last) begin
              if (4'(b_cnt - last) > 4'd7) ebus++;
              steps++;
            end
            last <= b_cnt;
            if (b_vld) begin
              if (got > 0 && b_dat != expect_dat) efifo++;
              expect_dat <= b_dat + 1; got++;
            end
          end
          initial begin
            #20000;
            err = ebus + efifo + (got < 50) + (steps < 50);
            $display("RESULT %s ebus=%0d efifo=%0d got=%0d steps=%0d", err == 0 ? "PASS" : "FAIL", ebus, efifo, got, steps); $finish;
          end
        endmodule''')
    assert 'RESULT PASS' in out, out
