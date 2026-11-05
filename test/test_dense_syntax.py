"""Tests for the compact syntax: int literals, self.wire/reg/mem/domain,
Input(8), .eq()/.lt()/..., split, Cat, If, Mux, Priority, mem[addr].
Tests that need Verilator are skipped when it is not on PATH."""
import pytest

from uhdl import *
from uhdl.core.UHDLException import ErrUHDLStr

from .test_lint_clean_features import VERILATOR, needs_verilator, lint, sim


class Dense(Component):
    MODULE_NAME = 'dense'

    def circuit(s):
        s.clk, s.rst_n = Input(1), Input(1)
        s.a, s.b = Input(4), Input(4)
        s.we = Input(1)
        s.y, s.z, s.c, s.q = Output(4), Output(1), Output(8), Output(4)
        s.domain(s.clk, s.rst_n)

        cnt = s.reg('cnt', 4, init=5)
        cnt += when(s.a.eq(3)).then(0).when(s.b.lt(5)).then(WrapAdd(cnt, 1))
        ram = s.mem('ram', 4, 5)
        ram.write(s.we, s.b[2:0], s.a)
        x = s.wire('x', Mux(s.a[1:0], [s.b, 2, s.a, cnt]))
        s.y += If(s.a.gt(2), x, 9)
        s.z += Priority([(s.a.eq(0), 1), (s.b.eq(0), 0)], s.a.ne(s.b))
        t = s.wire('t', Mux(s.a[1:0], [1, 2, 3]), width=2)
        s.c += Cat(s.a.split(2)[0], s.b, t)
        s.q += ram[s.b[2:0]]
        s.mark_unused(s.a.split(2)[1])


def test_dense_rtl_text():
    text = '\n'.join(Dense().verilog_def)
    assert "if(~rst_n) cnt <= 4'b101;" in text           # init=5
    assert "if((a == 4'b11)) cnt <= 4'b0;" in text        # int took cnt's width
    assert "else if((b < 4'b101)) cnt <= {(cnt + 4'b1)};" in text
    assert "2'b1 : x = 4'b10;" in text                     # Mux int took the signal width
    assert "default : t = 2'b0;" in text                   # 3 of 4 values -> default 0
    assert "assign c = {t, b, a[1:0]};" in text            # Cat is LSB first
    assert "q = ram[b[2:0]]" in text or "assign q = ram[b[2:0]];" in text


@needs_verilator
def test_dense_lint_and_sim(tmp_path):
    paths = Dense().generate(str(tmp_path / 'out'))
    assert lint(paths, 'dense') == []
    out = sim(tmp_path, paths, '''
        module tb;
          logic clk = 0, rst_n = 0, we = 0; logic [3:0] a = 0, b = 0;
          wire [3:0] y, q; wire z; wire [7:0] c;
          dense u(.*);
          always #5 clk = ~clk;
          int err = 0;
          task chk(input bit ok, input string m); if (!ok) begin err++; $display("ERR %s", m); end endtask
          initial begin
            #1 rst_n = 0; #10 rst_n = 1;
            a = 4'd1; b = 4'd7; #1;
            chk(y == 4'd9, "If else branch");            // a=1 -> not > 2 -> 9
            chk(z == 1'b1, "Priority default a!=b");
            chk(c == {2'd2, 4'd7, 2'd1}, "Cat/split/Mux width=");
            a = 4'd6; b = 4'd2; #1;                        // a[1:0]=2 -> x=a=6, a>2 -> y=x
            chk(y == 4'd6, "Mux signal value");
            a = 4'd5; b = 4'd9; #1;                        // a[1:0]=1 -> x=2
            chk(y == 4'd2, "Mux int value");
            a = 4'd0; #1; chk(z == 1'b1, "Priority first");
            a = 4'd1; b = 4'd0; #1; chk(z == 1'b0, "Priority second");
            // counter: reset 5, b<5 increments
            a = 4'd1; b = 4'd1; @(negedge clk); @(negedge clk);
            a = 4'd7; #1; chk(y == u.cnt, "cnt visible through Mux index 3");
            // memory write / read
            we = 1; a = 4'd11; b = 4'd3; @(negedge clk); we = 0; #1;
            chk(q == 4'd11, "mem write/read");
            $display("RESULT %s", err == 0 ? "PASS" : "FAIL"); $finish;
          end
        endmodule''')
    assert 'RESULT PASS' in out, out


def _comp(body):
    class C(Component):
        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.a = Input(4)
            s.o = Output(4)
            body(s)
    return C()


def test_int_must_fit():
    with pytest.raises(ErrUHDLStr, match='does not fit in 4 bits'):
        _comp(lambda s: s.a.eq(16))
    with pytest.raises(ErrUHDLStr, match='does not fit'):
        _comp(lambda s: s.a.eq(-1))


def test_both_ints_rejected():
    from uhdl.core.UHDLException import ErrExpInTypeWrong
    with pytest.raises(ErrExpInTypeWrong):
        Equal(1, 2)


def test_signal_widths_still_strict():
    from uhdl.core.UHDLException import ErrAttrMismatch
    with pytest.raises(ErrAttrMismatch):
        _comp(lambda s: s.a.eq(s.clk))                 # 4 vs 1 bit: no implicit extension


def test_wire_needs_width_for_int_only_values():
    with pytest.raises(ErrUHDLStr, match='pass width='):
        _comp(lambda s: s.wire('t', Mux(s.a[1:0], [1, 2, 3])))
    with pytest.raises(ErrUHDLStr, match='width=3 but the expression is 4 bits'):
        _comp(lambda s: s.wire('t', s.a, width=3))


def test_reg_without_domain_is_an_error():
    with pytest.raises(ErrUHDLStr, match='call self.domain'):
        _comp(lambda s: s.reg('r', 4))


def test_duplicate_name_is_an_error():
    def body(s):
        s.wire('t', s.a)
        s.wire('t', s.a)
    with pytest.raises(ErrUHDLStr, match='already has a member named "t"'):
        _comp(body)


def test_mux_too_many_values():
    with pytest.raises(ErrUHDLStr, match='reaches only 4'):
        _comp(lambda s: Mux(s.a[1:0], [0, 1, 2, 3, 4]))


def test_split_must_divide():
    with pytest.raises(ErrUHDLStr, match='not a multiple'):
        _comp(lambda s: s.a.split(3))


def test_domain_reg_options_and_explicit_clock():
    def body(s):
        s.clk2 = Input(1)
        s.domain(s.clk, s.rst_n, async_rst=False)
        r1 = s.reg('r1', 4)
        r1 += s.a
        r2 = s.reg('r2', 4, clk=s.clk2)               # other clock: no reset unless given
        r2 += r1
        s.o += r2
    text = '\n'.join(_comp(body).verilog_def)
    assert 'always @(posedge clk) begin' in text and 'if(~rst_n) r1' in text
    assert 'always @(posedge clk2) begin' in text and 'r2 <= r1;' in text


def test_old_style_still_works():
    class Old(Component):
        def circuit(self):
            self.clk = Input(UInt(1)); self.rst_n = Input(UInt(1))
            self.a = Input(UInt(4)); self.o = Output(UInt(4))
            self.r = Reg(UInt(4, 0), self.clk, self.rst_n)
            self.r += when(Equal(self.a, UInt(4, 3))).then(UInt(4, 0)).otherwise(self.a)
            self.o += self.r
    assert "if((a == 4'b11)) r <= 4'b0;" in '\n'.join(Old().verilog_def)
