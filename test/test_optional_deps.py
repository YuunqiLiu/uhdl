"""UHDL needs no third-party Python package: SystemVerilog import goes through libuhdl_slang."""
import os, subprocess, sys, textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, 'uhdl', '_native', 'libuhdl_slang.so')


def _run(code, cwd, **env):
    e = dict(os.environ, PYTHONPATH=ROOT, **env)
    r = subprocess.run([sys.executable, '-c', textwrap.dedent(code)], capture_output=True, text=True, env=e, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


BLOCK = '''
import sys
for m in ('pyslang', 'yaml', 'networkx', 'matplotlib'):
    sys.modules[m] = None            # make any import of them fail
from uhdl import *
'''


def test_core_and_sv_import_without_python_packages(tmp_path):
    if not os.path.isfile(LIB):
        import pytest
        pytest.skip('libuhdl_slang.so not built (python native/build.py)')
    (tmp_path / 'm.sv').write_text('module m #(parameter int W = 4) (input logic [W-1:0] a, output logic [W-1:0] y);\n'
                                   '  assign y = ~a;\nendmodule\n')
    rc, out = _run(BLOCK + '''
class T(Component):
    def circuit(s):
        s.a = Input(4); s.y = Output(4); s.y += ~s.a
print('\\n'.join(T().verilog_def)[:0] + 'core ok')
v = VComponent(file='m.sv', top='m', W=6)
print('sv ok', v.a.attribute.width, v.y.attribute.width)
try:
    from uhdl import TemplateIP
except ImportError as e:
    print('TemplateIP:', e)
''', str(tmp_path))
    assert rc == 0, out
    assert 'core ok' in out and 'sv ok 6 6' in out
    assert 'TemplateIP: TemplateIP moved to the ip_builder repository' in out


def test_missing_library_says_how_to_build(tmp_path):
    rc, out = _run(BLOCK + '''
try:
    VComponent(file='x.sv', top='x')
except ImportError as e:
    print('VC:', e)
''', str(tmp_path), UHDL_SLANG_LIB=str(tmp_path / 'nope.so'))
    assert rc == 0, out
    assert 'VC: Reading SystemVerilog' in out and 'native/build.py' in out
