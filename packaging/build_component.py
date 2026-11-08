#!/usr/bin/env python3
"""Build the UHDL toolkit component: a frozen `uhdl` command plus its Skill.

    python packaging/build_component.py [--python /path/python3.X] [--out dist/component]

Result: <out>/uhdl-<version>-linux-x86_64/ and the same as a .tar.gz, laid out like the other
motryx-toolkit components:

    bin/uhdl            frozen entry point (PyInstaller onedir)
    bin/_uhdl/          its runtime: Python, the full standard library, uhdl, pyslang,
                        pysrc/ (uhdl as plain source) and wheels/ (pyslang for other Pythons)
    skills/uhdl/uhdl/   the Skill (SKILL.md, references/)
    manifest.json       versions, source commit, SHA-256 of the binary and the Skill tree

Keep all of bin/: the entry point needs bin/_uhdl/. The frozen Python needs the glibc of the build
machine or newer; pyslang from PyPI needs glibc 2.27+ (see NexEvic/motryx-toolkit#15).
Needs network access to PyPI (PyInstaller, pyslang, wheels); the result runs offline.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, 'skill', 'uhdl')
PYINSTALLER = 'pyinstaller==6.16.0'
# pyslang for the frozen runtime (by its Python version) and wheels for other Pythons:
# 8.1.0 is the last release for 3.8; 12.x is abi3 but needs nanobind-backend per Python version.
PYSLANG_FOR = lambda v: '8.1.0' if v < (3, 11) else '12.1.0'
WHEEL_PYTHONS = ['3.8', '3.9', '3.10', '3.11', '3.12', '3.13', '3.14', '3.15']
PLATFORM_TAGS = ['manylinux_2_28_x86_64', 'manylinux_2_27_x86_64']
# standard-library modules generators never need, or that pull in GUI toolkits
STDLIB_SKIP = {'tkinter', 'turtle', 'turtledemo', 'idlelib', 'test', 'lib2to3', 'ensurepip', 'venv',
               'pydoc_data', 'this', 'antigravity', 'msilib', 'winreg', 'winsound', '_winapi', 'nt',
               'msvcrt', '_msi', '_overlapped', 'curses', '_curses', '_curses_panel', 'readline', 'dbm',
               '_dbm', '_gdbm', 'sqlite3', '_sqlite3', 'xxsubtype', 'xxlimited', 'xxlimited_35', '_tkinter'}


def run(cmd, **kw):
    print('+', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def pip(vpy, verb, args, wheelhouse):
    """pip download/install from the wheelhouse alone if it has everything, else from PyPI.
    Downloads land in the wheelhouse, so a rebuild needs no network."""
    base = [vpy, '-m', 'pip', verb, '-q', '--disable-pip-version-check', '--find-links', wheelhouse]
    if verb == 'download':
        base += ['-d', wheelhouse]
    print('+ pip %s %s' % (verb, ' '.join(args)), flush=True)
    if subprocess.run(base + ['--no-index'] + args, capture_output=True).returncode == 0:
        return
    for attempt in range(3):
        if subprocess.run(base + ['--retries', '5', '--timeout', '30'] + args).returncode == 0:
            return
    raise SystemExit('pip %s failed: %s' % (verb, ' '.join(args)))


def tree_sha(path):
    h = hashlib.sha256()
    n = 0
    for d, dirs, files in sorted(os.walk(path)):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            rel = os.path.relpath(p, path)
            h.update(rel.encode() + b'\0' + open(p, 'rb').read() + b'\0')
            n += 1
    return h.hexdigest(), n


def file_sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--python', default=sys.executable, help='Python to freeze (3.8+)')
    ap.add_argument('--out', default=os.path.join(ROOT, 'dist', 'component'))
    ap.add_argument('--work', default=None, help='build scratch directory (default: <out>/.build)')
    ap.add_argument('--wheelhouse', default=None, help='kept between builds (default: <out>/.wheelhouse)')
    a = ap.parse_args()

    ver = {}
    exec(open(os.path.join(ROOT, 'uhdl', '_version.py')).read(), ver)
    version = ver['__version__']
    name = 'uhdl-%s-linux-%s' % (version, platform.machine())
    out = os.path.abspath(a.out)
    work = os.path.abspath(a.work or os.path.join(out, '.build'))
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    wh = os.path.abspath(a.wheelhouse or os.path.join(out, '.wheelhouse'))
    os.makedirs(wh, exist_ok=True)

    # 1. a build venv with PyInstaller, pyslang and this uhdl
    venv = os.path.join(work, 'venv')
    run([a.python, '-m', 'venv', venv])
    vpy = os.path.join(venv, 'bin', 'python')
    pyver = tuple(json.loads(subprocess.check_output([vpy, '-c', 'import sys,json; print(json.dumps(sys.version_info[:2]))'])))
    tools = [PYINSTALLER, 'setuptools>=61', 'wheel', 'pyslang==' + PYSLANG_FOR(pyver)]
    pip(vpy, 'download', ['--only-binary', ':all:'] + tools, wh)
    pip(vpy, 'install', tools, wh)
    run([vpy, '-m', 'pip', 'install', '-q', '--no-deps', '--no-build-isolation', ROOT])
    for egg in ('build', 'uhdl.egg-info'):
        shutil.rmtree(os.path.join(ROOT, egg), ignore_errors=True)

    # 2. wheels for running uhdl in other Pythons (uhdl pythonpath)
    wheels = os.path.join(work, 'wheels')
    os.makedirs(wheels)
    for py in WHEEL_PYTHONS:
        v = tuple(int(x) for x in py.split('.'))
        cp = 'cp%d%d' % v
        args = ['--only-binary', ':all:', '--python-version', py, '--implementation', 'cp',
                '--abi', cp, '--abi', 'abi3', '--abi', 'none']
        for t in PLATFORM_TAGS:
            args += ['--platform', t]
        pip(vpy, 'download', args + ['pyslang==' + PYSLANG_FOR(v)], wh)
        # copy this Python's pyslang (and nanobind-backend) from the wheelhouse into wheels/
        r = subprocess.run([vpy, '-m', 'pip', 'download', '-q', '--no-index', '--find-links', wh, '-d', wheels]
                           + args + ['pyslang==' + PYSLANG_FOR(v)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(r.stderr)

    # 3. uhdl as plain source (for other Pythons), without caches and demos' outputs
    pysrc = os.path.join(work, 'pysrc')
    shutil.copytree(os.path.join(ROOT, 'uhdl'), os.path.join(pysrc, 'uhdl'),
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

    # 4. freeze
    entry = os.path.join(work, 'uhdl_entry.py')
    open(entry, 'w').write('import sys\nfrom uhdl.cli import main\nsys.exit(main())\n')
    stdlib = subprocess.check_output([vpy, '-c', 'import sys; print("\\n".join(sorted(sys.stdlib_module_names)))'
                                      if pyver >= (3, 10) else 'import sys; print("")'], text=True).split()
    hidden = []
    for m in stdlib:
        if m in STDLIB_SKIP or m.startswith('_test'):
            continue
        ok = subprocess.run([vpy, '-c', 'import ' + m], capture_output=True).returncode == 0
        if ok:
            hidden += ['--hidden-import', m]
    run([vpy, '-m', 'PyInstaller', '--noconfirm', '--clean', '--log-level', 'WARN', '--onedir',
         '--name', 'uhdl', '--contents-directory', '_uhdl',
         '--distpath', os.path.join(work, 'dist'), '--workpath', os.path.join(work, 'pyi'),
         '--specpath', work,
         '--collect-all', 'uhdl', '--collect-all', 'pyslang', '--collect-all', 'nanobind_backend',
         '--copy-metadata', 'pyslang', '--copy-metadata', 'uhdl',
         '--add-data', '%s:pysrc' % pysrc, '--add-data', '%s:wheels' % wheels] + hidden + [entry])

    # 5. lay out the component
    comp = os.path.join(out, name)
    shutil.rmtree(comp, ignore_errors=True)
    os.makedirs(os.path.join(comp, 'skills', 'uhdl'))
    shutil.copytree(os.path.join(work, 'dist', 'uhdl'), os.path.join(comp, 'bin'))
    sk = os.path.join(comp, 'skills', 'uhdl', 'uhdl')
    shutil.copytree(SKILL, sk, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    os.makedirs(os.path.join(sk, 'references'), exist_ok=True)
    shutil.copy(os.path.join(ROOT, 'docs', 'LLM_GUIDE.md'), os.path.join(sk, 'references', 'guide.md'))
    shutil.copy(os.path.join(ROOT, 'docs', 'llm_example', 'gen.py'), os.path.join(sk, 'references', 'example_gen.py'))

    rev = subprocess.run(['git', '-c', 'safe.directory=*', '-C', ROOT, 'rev-parse', 'HEAD'],
                         capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git', '-c', 'safe.directory=*', '-C', ROOT, 'status', '--porcelain', '--',
                            'uhdl', 'skill', 'docs', 'packaging'], capture_output=True, text=True).stdout.strip()
    skill_sha, skill_n = tree_sha(sk)
    rt_sha, rt_n = tree_sha(os.path.join(comp, 'bin', '_uhdl'))
    exe = os.path.join(comp, 'bin', 'uhdl')
    libc = platform.libc_ver()
    manifest = {
        'component': 'uhdl', 'component_version': version, 'platform': 'linux-' + platform.machine(),
        'repository': 'YuunqiLiu/uhdl', 'source_commit': rev, 'source_dirty': bool(dirty),
        'binary': {'path': 'uhdl', 'sha256': file_sha(exe), 'size_bytes': os.path.getsize(exe)},
        'runtime': {'path': '_uhdl', 'sha256_tree': rt_sha, 'file_count': rt_n},
        'skill': {'path': 'uhdl/uhdl', 'sha256_tree': skill_sha, 'file_count': skill_n},
        'build': {'python': '%d.%d' % pyver, 'pyslang': PYSLANG_FOR(pyver), 'pyinstaller': PYINSTALLER.split('==')[1],
                  'glibc': '%s %s' % libc},
    }
    json.dump(manifest, open(os.path.join(comp, 'manifest.json'), 'w'), indent=2)
    tar = comp + '.tar.gz'
    with tarfile.open(tar, 'w:gz') as t:
        t.add(comp, arcname=name)
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(comp) for f in fs)
    shutil.rmtree(work, ignore_errors=True)
    print('component %s: %s (%.0f MB unpacked)\n  %s' % (version, comp, size / 1e6, tar))


if __name__ == '__main__':
    main()
