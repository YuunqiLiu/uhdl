"""Importing SV: type parameters (SvType), unpacked-array ports (packed shim),
unresolved port types, and import_sv_package()."""
import os, sys, textwrap
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from uhdl import *
from uhdl.core.UHDLException import ErrUHDLStr
from test_lint_clean_features import needs_verilator, lint, sim

if not os.path.isfile(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uhdl', '_native', 'libuhdl_slang.so')):
    pytest.skip('libuhdl_slang.so not built (python native/build.py)', allow_module_level=True)

PKG = '''
package demo_pkg;
  localparam int unsigned N_ENT = 4;
  localparam int unsigned AW    = 8;
  typedef struct packed { logic [1:0] burst; logic lock; } ext_t;
  typedef struct packed { logic [3:0] id; logic [AW-1:0] addr; ext_t ext; } req_t;
endpackage
'''
CELLS = '''
module tslice #(parameter type T = logic) (
  input logic clk, input logic rst_n, input T i, output T o);
  T q;
  always_ff @(posedge clk or negedge rst_n) if (!rst_n) q <= '0; else q <= i;
  assign o = q;
endmodule
module amux #(parameter int unsigned W = 4, parameter int unsigned N = 3) (
  input logic [W-1:0] din [N-1:0], input logic [$clog2(N)-1:0] sel, output logic [W-1:0] dout,
  output logic [W-1:0] dup [N-1:0]);
  assign dout = din[sel];
  for (genvar k = 0; k < N; k++) begin : g assign dup[k] = ~din[k]; end
endmodule
'''


@pytest.fixture
def svfiles(tmp_path):
    p, c = tmp_path / 'pkg.sv', tmp_path / 'cells.sv'
    p.write_text(PKG); c.write_text(CELLS)
    return str(p), str(c)


def test_import_sv_package(svfiles):
    pk = import_sv_package([svfiles[0]], 'demo_pkg')
    assert pk.N_ENT == 4 and pk.AW == 8
    assert pk.req_t.width == 15 and pk.req_t.fields == ['id', 'addr', 'ext']
    assert pk.req_t.field_type('ext').fields == ['burst', 'lock']
    assert pk.req_t.bounds('id') == (14, 11)


def test_type_parameter(svfiles):
    v = VComponent(file=svfiles[1], top='tslice', T=SvType('logic [6:0]'))
    assert v.i.attribute.width == 7 and v.o.attribute.width == 7


def test_unresolved_type_is_an_error(svfiles, tmp_path):
    f = tmp_path / 'bad.sv'
    f.write_text('module bad (input missing_pkg::t i, output logic o); assign o = 1\'b0; endmodule\n')
    with pytest.raises(ErrUHDLStr, match='could not resolve the type'):
        VComponent(file=str(f), top='bad')


@needs_verilator
def test_unpacked_ports_get_a_packed_shim(svfiles, tmp_path):
    class T(Component):
        MODULE_NAME = 'shim_t'

        def circuit(s):
            s.d = Input(12); s.sel = Input(2); s.y = Output(4); s.z = Output(12)
            s.m = VComponent(file=svfiles[1], top='amux', W=4, N=3)
            s.m.din += s.d
            s.m.sel += s.sel
            s.y += s.m.dout
            s.z += s.m.dup
    t = T()
    assert t.m.din.attribute.width == 12 and t.m.dup.attribute.width == 12
    paths = t.generate(str(tmp_path / 'o'))
    assert any(p.endswith('.sv') and 'amux__uflat_' in p for p in paths)
    out = sim(tmp_path, [svfiles[1]] + paths, '''
        module tb;
          logic [11:0] d = 12'h5a3; logic [1:0] sel; wire [3:0] y; wire [11:0] z; int err = 0;
          shim_t u(.*);
          initial begin
            for (int k = 0; k < 3; k++) begin sel = k; #1 if (y != d[k*4 +: 4]) err++; end
            if (z != ~d) err++;
            $display("RESULT %s", err == 0 ? "PASS" : "FAIL"); $finish;
          end
        endmodule''')
    assert 'RESULT PASS' in out, out


@needs_verilator
def test_struct_type_parameter_from_package(svfiles, tmp_path):
    pk = import_sv_package([svfiles[0]], 'demo_pkg')

    class T(Component):
        MODULE_NAME = 'tp_t'

        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.a, s.o = Input(pk.req_t.width), Output(4)
            s.domain(s.clk, s.rst_n)                     # the VComponent's clk/rst_n follow this domain
            s.r = VComponent(file='%s %s' % svfiles, top='tslice', slang_opts='--ignore-unknown-modules --single-unit',
                             T=SvType('demo_pkg::req_t'))
            s.r.i += s.a
            s.o += pk.req_t(s.r.o).id
            s.mark_unused(pk.req_t(s.r.o).addr, pk.req_t(s.r.o).ext.bits)
    paths = T().generate(str(tmp_path / 'o'))
    ours = [w for w in lint([svfiles[0], svfiles[1]] + paths, 'tp_t') if any(p in w for p in paths)]
    assert ours == []                                # warnings from the hand-written test SV are not ours
