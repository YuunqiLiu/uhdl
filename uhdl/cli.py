"""The `uhdl` command: run generators, check their output, give any Python access to UHDL.

    uhdl run GEN.py [ARGS...]         run a generator script with this UHDL
    uhdl check OUT --top TOP [...]    Verilator lint + Yosys check of generate() output
    uhdl python [-c CODE | -m MOD | FILE [ARGS...]]   this UHDL's Python (no args: interactive)
    uhdl pythonpath [--python PY]     PYTHONPATH that lets another Python import this UHDL
    uhdl version

In the frozen build (bin/uhdl with bin/_uhdl/), `run`, `check` and `python` use the bundled
Python, UHDL and pyslang: no Python is needed on the machine. A generator that also needs
libraries from the user's own Python runs there instead:

    PYTHONPATH=$(uhdl pythonpath --python python3)${PYTHONPATH:+:$PYTHONPATH} python3 gen.py

`pythonpath` adds pyslang for that Python from the bundled wheels when it does not have one.
The same commands work from an installed package as `python -m uhdl ...`.
"""
import argparse
import json
import os
import runpy
import subprocess
import sys
import zipfile

from ._version import __version__

FROZEN = bool(getattr(sys, 'frozen', False))
BASE = getattr(sys, '_MEIPASS', None)


def _pysrc():
    '''Directory holding the `uhdl` package as plain source.'''
    if FROZEN:
        return os.path.join(BASE, 'pysrc')
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _wheels():
    if FROZEN:
        return os.path.join(BASE, 'wheels')
    return os.environ.get('UHDL_WHEELS')


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


def _probe(python):
    code = ('import sys, json, importlib.util, platform; print(json.dumps({"ver": list(sys.version_info[:2]), '
            '"machine": platform.machine(), "system": sys.platform, '
            '"pyslang": importlib.util.find_spec("pyslang") is not None}))')
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    r = subprocess.run([python, '-c', code], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or 'could not run %s' % python)
    return json.loads(r.stdout)


def _wheel_tags(name):
    # pyslang-12.1.0-cp311-abi3-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl
    parts = name[:-4].split('-')
    return parts[0], parts[-3], parts[-2], parts[-1]


def _pick(wheels, project, ver, machine):
    cp = 'cp%d%d' % tuple(ver)
    best = None
    for w in sorted(os.listdir(wheels)):
        if not w.endswith('.whl'):
            continue
        proj, py, abi, plat = _wheel_tags(w)
        if proj.lower().replace('_', '-') != project or machine not in plat:
            continue
        if py == cp and abi in (cp, 'none'):
            return w
        if abi == 'abi3' and int(py[2:]) <= int(cp[2:]) and ver[0] == 3:
            best = w
    return best


def cmd_pythonpath(a):
    paths = [_pysrc()]
    if a.no_sv:
        print(os.pathsep.join(paths))
        return 0
    try:
        info = _probe(a.python)
    except (OSError, RuntimeError) as e:
        _err('cannot run %s: %s' % (a.python, e))
        return 2
    if tuple(info['ver']) < (3, 8):
        _err('%s is Python %d.%d; UHDL needs 3.8 or newer' % ((a.python,) + tuple(info['ver'])))
        return 2
    if not info['pyslang']:
        wheels = _wheels()
        need = [('pyslang',)] + ([('nanobind-backend',)] if tuple(info['ver']) >= (3, 11) else [])
        picked = [_pick(wheels, n[0], info['ver'], info['machine']) for n in need] if wheels and os.path.isdir(wheels) else [None]
        if not info['system'].startswith('linux') or None in picked:
            _err('no bundled pyslang for Python %d.%d on %s %s: SV import (VComponent, import_sv_package) '
                 'will not work with this Python' % (tuple(info['ver']) + (info['system'], info['machine'])))
        else:
            cache = os.environ.get('UHDL_CACHE') or os.path.join(
                os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache'), 'uhdl')
            site = os.path.join(cache, '%s-cp%d%d-%s' % ((__version__,) + tuple(info['ver']) + (info['machine'],)))
            stamp = os.path.join(site, '.complete')
            if not os.path.exists(stamp):
                tmp = site + '.tmp%d' % os.getpid()
                os.makedirs(tmp, exist_ok=True)
                for w in picked:
                    with zipfile.ZipFile(os.path.join(wheels, w)) as z:
                        for m in z.infolist():
                            z.extract(m, tmp)
                            mode = (m.external_attr >> 16) & 0o777
                            if mode:
                                os.chmod(os.path.join(tmp, m.filename), mode)
                open(os.path.join(tmp, '.complete'), 'w').write('\n'.join(picked) + '\n')
                try:
                    os.rename(tmp, site)
                except OSError:                       # another process finished first
                    import shutil
                    shutil.rmtree(tmp, ignore_errors=True)
            paths.append(site)
    print(os.pathsep.join(paths))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(__doc__.strip())
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == 'version':
        import platform
        sv = 'none'
        try:
            from .core import _slang
            _slang.get('Driver')
            import importlib.metadata as md
            sv = md.version('pyslang')
        except Exception as e:
            sv = 'unavailable (%s)' % str(e).splitlines()[0][:60] if 'pyslang' in str(e) else sv
        print('uhdl %s (%s, Python %s %s, pyslang %s)' % (__version__, 'frozen' if FROZEN else 'package',
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
        ap = argparse.ArgumentParser(prog='uhdl pythonpath', description=cmd_pythonpath.__doc__ or
                                     'Print a PYTHONPATH that lets PY import this UHDL (and pyslang).')
        ap.add_argument('--python', default='python3', help='the Python that will run the generator (default: python3)')
        ap.add_argument('--no-sv', action='store_true', help='only UHDL, no pyslang')
        return cmd_pythonpath(ap.parse_args(rest))
    _err('unknown command %r (try: uhdl help)' % cmd)
    return 2


if __name__ == '__main__':
    sys.exit(main())
