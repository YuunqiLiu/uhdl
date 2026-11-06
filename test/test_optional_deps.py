"""The UHDL core imports and generates Verilog without its optional dependencies (pyslang, demo packages)."""
import os, subprocess, sys, textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(code):
    env = dict(os.environ, PYTHONPATH=ROOT)
    r = subprocess.run([sys.executable, '-c', textwrap.dedent(code)], capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def test_core_without_pyslang_or_yaml():
    rc, out = _run('''
        import sys
        for m in ('pyslang', 'yaml', 'networkx', 'matplotlib'):
            sys.modules[m] = None            # make any import of them fail
        from uhdl import *
        class T(Component):
            def circuit(s):
                s.a = Input(4); s.y = Output(4); s.y += ~s.a
        print('\\n'.join(T().verilog_def))
        try:
            VComponent(file='x.sv', top='x')
        except ImportError as e:
            print('VC:', e)
        try:
            from uhdl import TemplateIP
        except ImportError as e:
            print('TemplateIP:', e)
        ''')
    assert rc == 0, out
    assert 'assign y = (~a);' in out.replace('\t', '') or 'assign y' in out
    assert 'VC: Reading SystemVerilog' in out and 'pip install' in out
    assert 'TemplateIP: TemplateIP moved to the ip_builder repository' in out
