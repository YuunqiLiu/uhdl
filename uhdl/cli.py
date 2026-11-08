"""The `uhdl` command: run generators, check their output, give any Python access to UHDL.

    uhdl run GEN.py [ARGS...]         run a generator script with this UHDL
    uhdl check OUT --top TOP [...]    Verilator lint + Yosys check of generate() output
    uhdl python [-c CODE | -m MOD | FILE [ARGS...]]   this UHDL's Python (no args: interactive)
    uhdl pythonpath [--python PY]     PYTHONPATH that lets another Python import this UHDL
    uhdl version

In the frozen build (bin/uhdl with bin/_uhdl/), `run`, `check` and `python` use the bundled
Python and UHDL: no Python is needed on the machine. A generator that also needs libraries from
the user's own Python runs there instead:

    PYTHONPATH=$(uhdl pythonpath --python python3)${PYTHONPATH:+:$PYTHONPATH} python3 gen.py

SystemVerilog is read by libuhdl_slang (C interface, loaded with ctypes), which ships inside
the uhdl package and works with any Python 3.8+. The same commands work from an installed
package as `python -m uhdl ...`.
"""
import argparse
import json
import os
import runpy
import subprocess
import sys

from ._version import __version__

FROZEN = bool(getattr(sys, 'frozen', False))
BASE = getattr(sys, '_MEIPASS', None)


def _pysrc():
    '''Directory holding the `uhdl` package as plain source.'''
    if FROZEN:
        return os.path.join(BASE, 'pysrc')
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _err(msg):
    sys.stderr.write('uhdl: %s\n' % msg)


def _run_path(path, args):
    sys.argv = [path] + list(args)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    try:
        runpy.run_path(path, run_name='__main__')
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return 0


def cmd_run(a):
    if not os.path.isfile(a.script):
        _err('no such file: %s' % a.script)
        return 2
    return _run_path(a.script, a.args)


def cmd_python(rest):
    if not rest and not sys.stdin.isatty():
        sys.argv = ['-']
        exec(compile(sys.stdin.read(), '<stdin>', 'exec'), {'__name__': '__main__'})
        return 0
    if not rest:
        import code
        code.interact(banner='UHDL %s, Python %s' % (__version__, sys.version.split()[0]), local={'__name__': '__main__'})
        return 0
    if rest[0] == '-c' and len(rest) > 1:
        sys.argv = ['-c'] + rest[2:]
        exec(compile(rest[1], '<string>', 'exec'), {'__name__': '__main__'})
        return 0
    if rest[0] == '-m' and len(rest) > 1:
        sys.argv = [rest[1]] + rest[2:]
        try:
            runpy.run_module(rest[1], run_name='__main__', alter_sys=True)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        return 0
    return _run_path(rest[0], rest[1:])


def cmd_check(rest):
    from .tools.check import main
    return main(rest)


def _python_version(python):
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    r = subprocess.run([python, '-c', 'import sys; print("%d %d" % sys.version_info[:2])'],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or 'could not run %s' % python)
    return tuple(int(x) for x in r.stdout.split())


def cmd_pythonpath(a):
    """Print a PYTHONPATH that lets PY import this UHDL (including SystemVerilog import)."""
    if a.python:
        try:
            ver = _python_version(a.python)
        except (OSError, RuntimeError) as e:
            _err('cannot run %s: %s' % (a.python, e))
            return 2
        if ver < (3, 8):
            _err('%s is Python %d.%d; UHDL needs 3.8 or newer' % ((a.python,) + ver))
            return 2
    print(_pysrc())
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(__doc__.strip())
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == 'version':
        import platform
        try:
            from .core import _slang
            sv = _slang.version()
        except Exception as e:
            sv = 'SV import unavailable: %s' % str(e).splitlines()[0][:80]
        print('uhdl %s (%s, Python %s %s, %s)' % (__version__, 'frozen' if FROZEN else 'package',
                                                   platform.python_version(), platform.machine(), sv))
        return 0
    if cmd == 'python':
        return cmd_python(rest)
    if cmd == 'check':
        return cmd_check(rest)
    if cmd == 'run':
        ap = argparse.ArgumentParser(prog='uhdl run', description='Run a UHDL generator script.')
        ap.add_argument('script')
        ap.add_argument('args', nargs=argparse.REMAINDER)
        return cmd_run(ap.parse_args(rest))
    if cmd == 'pythonpath':
        ap = argparse.ArgumentParser(prog='uhdl pythonpath', description=cmd_pythonpath.__doc__)
        ap.add_argument('--python', help='check that this Python (the one that will run the generator) is 3.8+')
        ap.add_argument('--no-sv', action='store_true', help=argparse.SUPPRESS)   # accepted for compatibility
        return cmd_pythonpath(ap.parse_args(rest))
    _err('unknown command %r (try: uhdl help)' % cmd)
    return 2


if __name__ == '__main__':
    sys.exit(main())
