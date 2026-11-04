"""Tests for the lwnoc_rewrite fixes: Cut temp-wire reuse (#17), module naming,
flat generate(), WrapAdd/WrapSub, Mem, compare folding, Combine(1 arg),
mark_unused, Case default warning and the opt-in log file.

Tests that need Verilator are skipped when it is not on PATH."""
import os, shutil, subprocess, sys, textwrap
import pytest

from uhdl import *
from uhdl.core.UHDLException import ErrUHDLStr

VERILATOR = shutil.which('verilator')
needs_verilator = pytest.mark.skipif(VERILATOR is None, reason='verilator not installed')


def lint(paths, top):
    """Run verilator -Wall; return the list of %Warning/%Error lines."""
    r = subprocess.run([VERILATOR, '--lint-only', '-Wall', '--top-module', top] + list(paths),
                       capture_output=True, text=True)
    return [l for l in (r.stdout + r.stderr).splitlines() if l.startswith(('%Warning', '%Error'))]


def sim(tmp_path, dut_paths, tb_text):
    """Build and run a Verilator --binary testbench; return stdout."""
    tb = tmp_path / 'tb.sv'
    tb.write_text(textwrap.dedent(tb_text))
    obj = tmp_path / 'obj'
    r = subprocess.run([VERILATOR, '--binary', '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-style',
                        '--top-module', 'tb', '-Mdir', str(obj), str(tb)] + list(dut_paths),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return subprocess.run([str(obj / 'Vtb')], capture_output=True, text=True).stdout


# ---------------------------------------------------------------- issue #17
class UpDown(Component):
    MODULE_NAME = 'updown'

    def circuit(self):
        self.clk = Input(UInt(1)); self.rst_n = Input(UInt(1))
        self.inc = Input(UInt(1)); self.dec = Input(UInt(1))
        self.c = Reg(UInt(4), self.clk, self.rst_n)
        self.c += when(self.inc).then(Cut(self.c + UInt(4, 1), 3, 0)) \
                  .when(self.dec).then(Cut(self.c - UInt(4, 1), 3, 0))
        self.o = Output(UInt(4)); self.o += self.c


def test_cut_branches_get_distinct_temp_wires():
    text = '\n'.join(UpDown().verilog_def)
    assert "c_bcut_tmp = (c + 4'b1)" in text
    assert "c_bcut_tmp_1 = (c - 4'b1)" in text
    assert 'else if(dec) c <= c_bcut_tmp_1[3:0];' in text


def test_cut_temp_wire_stable_across_renders():
    comp = UpDown()
    assert comp.verilog_def == comp.verilog_def


# ---------------------------------------------------------------- naming / generate
class Leaf(Component):
    def __init__(self, W):
        super().__init__()

    def circuit(self):
        self.a = Input(UInt(4)); self.y = Output(UInt(4)); self.y += self.a


def test_module_name_override():
    assert UpDown().module_name == 'updown'
    leaf = Leaf(4)
    assert leaf.module_name == 'Leaf_W_4'
    leaf.set_module_name('leaf4')
    assert leaf.module_name == 'leaf4'
    with pytest.raises(ValueError):
        leaf.set_module_name('bad name')


def test_generate_flat_with_filelist(tmp_path):
    class Top(Component):
        MODULE_NAME = 'top'

        def circuit(self):
            self.a = Input(UInt(4)); self.y = Output(UInt(4))
            self.u0 = Leaf(4); self.u1 = Leaf(4)          # same module twice -> one file
            self.u0.a += self.a; self.u1.a += self.u0.y; self.y += self.u1.y

    keep = tmp_path / 'keep.txt'; keep.write_text('x')
    paths = Top().generate(tmp_path)
    assert [os.path.basename(p) for p in paths] == ['Leaf_W_4.v', 'top.v']
    assert keep.exists()                                   # not wiped
    flist = (tmp_path / 'filelist.f').read_text().split()
    assert [p for p in flist if p.endswith('.v')] == [str(p) for p in paths]


def test_generate_rejects_name_collision(tmp_path):
    class A(Component):
        MODULE_NAME = 'same'
        def circuit(self):
            self.a = Input(UInt(1)); self.y = Output(UInt(1)); self.y += self.a

    class B(Component):
        MODULE_NAME = 'same'
        def circuit(self):
            self.a = Input(UInt(2)); self.y = Output(UInt(2)); self.y += self.a

    class Top(Component):
        def circuit(self):
            self.a = Input(UInt(1)); self.b = Input(UInt(2))
            self.x = Output(UInt(1)); self.z = Output(UInt(2))
            self.ua = A(); self.ub = B()
            self.ua.a += self.a; self.ub.a += self.b; self.x += self.ua.y; self.z += self.ub.y

    with pytest.raises(ErrUHDLStr):
        Top().generate(tmp_path)


# ---------------------------------------------------------------- WrapAdd / WrapSub
class Ptr(Component):
    MODULE_NAME = 'ptr'

    def circuit(self):
        self.clk = Input(UInt(1)); self.rst_n = Input(UInt(1))
        self.up = Input(UInt(1)); self.dn = Input(UInt(1))
        self.p = Reg(UInt(3), self.clk, self.rst_n)
        self.p += when(self.up).then(WrapAdd(self.p, UInt(3, 1))).when(self.dn).then(WrapSub(self.p, UInt(3, 1)))
        self.wide = Output(UInt(4))
        self.wide += WrapAdd(self.p, UInt(3, 7)) + UInt(3, 0)   # wrap must hold inside a wider expression
        self.o = Output(UInt(3)); self.o += self.p


def test_wrap_add_width_and_text():
    expr = WrapAdd(UInt(3, 1), UInt(3, 2))
    assert expr.attribute.width == 3
    assert '{(p + 3\'b1)}' in '\n'.join(Ptr().verilog_def)


@needs_verilator
def test_wrap_add_lint_and_sim(tmp_path):
    paths = Ptr().generate(tmp_path / 'rtl')
    assert lint(paths, 'ptr') == []
    out = sim(tmp_path, paths, '''
        module tb;
          logic clk=0, rst_n=0, up=0, dn=0; logic [2:0] o; logic [3:0] wide; int err=0;
          always #5 clk=~clk;
          ptr dut(.*);
          initial begin
            #12 rst_n=1;
            @(negedge clk) dn=1; @(negedge clk) dn=0; #1 if (o!==3'd7) err++;      // 0-1 wraps to 7
            if (wide!==4'd6) err++;                                               // {(7+7)} = 6, not 14
            @(negedge clk) up=1; @(negedge clk) up=0; #1 if (o!==3'd0) err++;      // 7+1 wraps to 0
            $display("ERR=%0d", err); $finish;
          end
        endmodule''')
    assert 'ERR=0' in out


# ---------------------------------------------------------------- Mem
class Ram(Component):
    MODULE_NAME = 'ram'

    def circuit(self):
        self.clk = Input(UInt(1))
        self.we = Input(UInt(1)); self.waddr = Input(UInt(3)); self.wdata = Input(UInt(8))
        self.raddr = Input(UInt(3)); self.rdata = Output(UInt(8))
        self.mem = Mem(UInt(8), 5, self.clk)
        self.mem.write(self.we, self.waddr, self.wdata)
        self.rdata += self.mem.read(self.raddr)


def test_mem_text():
    text = '\n'.join(Ram().verilog_def)
    assert 'reg  [7:0] mem [0:4]' in text or 'reg [7:0] mem [0:4]' in text
    assert 'if(we) mem[waddr] <= wdata;' in text
    assert 'assign rdata = mem[raddr];' in text


def test_mem_checks():
    class Bad(Component):
        def circuit(self):
            self.clk = Input(UInt(1)); self.a = Input(UInt(2))
            self.m = Mem(UInt(8), 5, self.clk)
            self.m.read(self.a)                 # 2 bits cannot address 5 words
    with pytest.raises(ErrUHDLStr):
        Bad()


@needs_verilator
def test_mem_lint_and_sim(tmp_path):
    paths = Ram().generate(tmp_path / 'rtl')
    assert lint(paths, 'ram') == []
    out = sim(tmp_path, paths, '''
        module tb;
          logic clk=0, we=0; logic [2:0] waddr=0, raddr=0; logic [7:0] wdata=0, rdata; int err=0;
          always #5 clk=~clk;
          ram dut(.*);
          initial begin
            for (int i=0;i<5;i++) begin @(negedge clk) we=1; waddr=3'(i); wdata=8'(8'h10+i); end
            @(negedge clk) we=0;
            for (int i=0;i<5;i++) begin raddr=3'(i); #1 if (rdata!==8'(8'h10+i)) err++; end
            $display("ERR=%0d", err); $finish;
          end
        endmodule''')
    assert 'ERR=0' in out


# ---------------------------------------------------------------- folding / Combine / unused / Case
def test_compare_folding():
    class C(Component):
        def circuit(self):
            self.p = Input(UInt(3))
            self.always1 = GreaterEqual(UInt(3, 7), self.p)
            self.always0 = Less(self.p, UInt(3, 0))
            self.normal = GreaterEqual(UInt(3, 5), self.p)
    c = C()
    assert isinstance(c.always1, UInt) and c.always1.value == 1
    assert isinstance(c.always0, UInt) and c.always0.value == 0
    assert not isinstance(c.normal, UInt)


def test_combine_single_argument():
    a = UInt(4, 3)
    assert Combine(a) is a


@needs_verilator
def test_mark_unused_is_lint_clean(tmp_path):
    class U(Component):
        MODULE_NAME = 'u'
        def circuit(self):
            self.clk = Input(UInt(1)); self.rst_n = Input(UInt(1))
            self.a = Input(UInt(4)); self.y = Output(UInt(4))
            self.s = Wire(UInt(5)); self.s += self.a + UInt(4, 1)
            self.y += self.s[3:0]
            self.mark_unused(self.clk, self.rst_n, self.s[4])
    assert lint(U().generate(tmp_path), 'u') == []


def test_case_without_default_warns(caplog):
    sel = UInt(2, 0)
    with caplog.at_level('WARNING', logger='UHDL'):
        Case(sel, {UInt(2, 0): UInt(1, 0), UInt(2, 1): UInt(1, 1)}, None)
    assert any('infer a latch' in r.message for r in caplog.records)


def test_no_log_file_by_default(tmp_path):
    env = dict(os.environ); env.pop('UHDL_LOG', None)
    env['PYTHONPATH'] = os.pathsep.join([os.path.dirname(os.path.dirname(os.path.abspath(__file__)))] +
                                        env.get('PYTHONPATH', '').split(os.pathsep))
    subprocess.run([sys.executable, '-c', 'import uhdl'], cwd=tmp_path, env=env, check=True)
    assert not (tmp_path / 'UHDL.log').exists()
