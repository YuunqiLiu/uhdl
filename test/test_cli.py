"""The `uhdl` command (python -m uhdl) from a source checkout."""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def uhdl(*args, cwd=None, inp=None):
    env = dict(os.environ, PYTHONPATH=ROOT)
    return subprocess.run([sys.executable, '-m', 'uhdl'] + list(args), capture_output=True, text=True,
                          env=env, cwd=cwd, input=inp)


def test_version_and_help():
    assert uhdl('version').stdout.startswith('uhdl ')
    assert 'uhdl run' in uhdl('help').stdout


def test_run_generates_and_check_reports(tmp_path):
    gen = tmp_path / 'g.py'
    gen.write_text('import sys\nfrom uhdl import *\nclass t(Component):\n    MODULE_NAME = "t"\n'
                   '    def circuit(s):\n        s.a = Input(4); s.y = Output(4); s.y += ~s.a\n'
                   't().generate(sys.argv[1])\n')
    r = uhdl('run', str(gen), str(tmp_path / 'o'))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / 'o' / 't.v').is_file()
    r = uhdl('check', str(tmp_path / 'o'), '--top', 't')
    assert 'CHECK' in r.stdout


def test_python_c_stdin_and_exit_code():
    assert 'ok' in uhdl('python', '-c', 'import uhdl; print("ok")').stdout
    assert 'stdin' in uhdl('python', inp='print("stdin")\n').stdout
    assert uhdl('python', '-c', 'import sys; sys.exit(4)').returncode == 4


def test_pythonpath_points_at_this_uhdl():
    r = uhdl('pythonpath', '--no-sv')
    assert r.stdout.strip() == ROOT
    r = uhdl('pythonpath', '--python', sys.executable)
    assert r.returncode == 0 and r.stdout.split(os.pathsep)[0].strip() == ROOT
