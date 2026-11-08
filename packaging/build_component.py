#!/usr/bin/env python3
"""Build the UHDL toolkit component: a frozen `uhdl` command plus its Skill.

    python packaging/build_component.py --python /path/python3.X [--out dist/component]
        [--repository YuunqiLiu/uhdl] [--release-tag v<version>]

Writes, in <out>, what a motryx-toolkit component release consists of:
    uhdl-<version>-linux-x86_64.tar.gz          the archive
    uhdl-<version>-linux-x86_64.tar.gz.sha256   "<sha256>  <archive name>"
    component-manifest.json                      the same manifest as inside the archive

The archive root (the contract checked by motryx-toolkit's scripts/update_component_lock.py):
    uhdl                     frozen entry point (PyInstaller onedir)
    _uhdl/                   its runtime: Python with the standard library, uhdl with
                             _native/libuhdl_slang.so, and pysrc/ (uhdl as plain source for other
                             Pythons: uhdl pythonpath)
    skill/uhdl-design/       the Skill (the toolkit installs skill/ as skills/uhdl/)
    component-manifest.json  identity, binary hash and size, runtime and Skill tree hashes

The archive is reproducible (sorted, root-owned, commit time). The oldest glibc the component runs
on is the newest one any ELF file needs (build.glibc_needed in the manifest): libuhdl_slang.so
follows its compiler's sysroot (python native/build.py --cxx ...), the frozen Python follows the
interpreter given with --python. Needs PyPI for PyInstaller; the result runs offline.
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
SKILL = os.path.join(ROOT, 'skill', 'uhdl-design')
SKILL_NAME = 'uhdl-design'
COMPONENT = 'uhdl'
PYINSTALLER = 'pyinstaller==6.16.0'
# standard-library modules generators never need, or that pull in GUI toolkits
STDLIB_SKIP = {'tkinter', 'turtle', 'turtledemo', 'idlelib', 'test', 'lib2to3', 'ensurepip', 'venv',
               'pydoc_data', 'this', 'antigravity', 'msilib', 'winreg', 'winsound', '_winapi', 'nt',
               'msvcrt', '_msi', '_overlapped', 'curses', '_curses', '_curses_panel', 'readline', 'dbm',
               '_dbm', '_gdbm', 'sqlite3', '_sqlite3', 'xxsubtype', 'xxlimited', 'xxlimited_35', '_tkinter',
               }


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


def tree_sha(root):
    """motryx-toolkit's skill_tree_hash: sha256 over (relative path, hex sha256) of every file."""
    h = hashlib.sha256()
    n = 0
    for p in sorted((os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs),
                    key=lambda x: os.path.relpath(x, root).replace(os.sep, '/')):
        if os.path.islink(p):
            raise SystemExit('links are not allowed in the component: %s' % p)
        h.update(os.path.relpath(p, root).replace(os.sep, '/').encode() + b'\0')
        h.update(file_sha(p).encode('ascii') + b'\0')
        n += 1
    return h.hexdigest(), n


def max_glibc(root):
    """Newest GLIBC_x.y symbol version needed by any ELF file under root, as "x.y"."""
    import re
    tool = shutil.which('objdump')
    best = None
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            with open(p, 'rb') as fh:
                if fh.read(4) != b'\x7fELF':
                    continue
            out = subprocess.run([tool, '-T', p], capture_output=True, text=True).stdout if tool else ''
            for m in re.findall(r'GLIBC_(\d+)\.(\d+)', out):
                v = (int(m[0]), int(m[1]))
                best = v if best is None or v > best else best
    return '%d.%d' % best if best else None


def file_sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--python', default=sys.executable,
                    help='Python to freeze (3.8+); its glibc requirement becomes the component\'s, e.g. a '
                         'conda-forge python with sysroot_linux-64=2.17 for glibc 2.17')
    ap.add_argument('--out', default=os.path.join(ROOT, 'dist', 'component'))
    ap.add_argument('--work', default=None, help='build scratch directory (default: <out>/.build)')
    ap.add_argument('--wheelhouse', default=None, help='kept between builds (default: <out>/.wheelhouse)')
    ap.add_argument('--repository', default='YuunqiLiu/uhdl', help='recorded in component-manifest.json')
    ap.add_argument('--release-tag', default=None, help='v<version> for a formal release (default: main-<commit[:12]>)')
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

    # 1. a build venv with PyInstaller and this uhdl
    venv = os.path.join(work, 'venv')
    run([a.python, '-m', 'venv', venv])
    vpy = os.path.join(venv, 'bin', 'python')
    pyver = tuple(json.loads(subprocess.check_output([vpy, '-c', 'import sys,json; print(json.dumps(sys.version_info[:2]))'])))
    lib = os.path.join(ROOT, 'uhdl', '_native', 'libuhdl_slang.so')
    if not os.path.isfile(lib):
        raise SystemExit('%s is missing: build it first with python native/build.py --cxx <compiler>' % lib)
    tools = [PYINSTALLER, 'setuptools>=61', 'wheel']
    pip(vpy, 'download', ['--only-binary', ':all:'] + tools, wh)
    pip(vpy, 'install', tools, wh)
    run([vpy, '-m', 'pip', 'install', '-q', '--no-deps', '--no-build-isolation', ROOT])
    for egg in ('build', 'uhdl.egg-info'):
        shutil.rmtree(os.path.join(ROOT, egg), ignore_errors=True)

    # 3. uhdl as plain source (for other Pythons), without caches and demos' outputs
    pysrc = os.path.join(work, 'pysrc')
    shutil.copytree(os.path.join(ROOT, 'uhdl'), os.path.join(pysrc, 'uhdl'),
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '_native'))   # the library comes from the runtime

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
    excludes = []
    run([vpy, '-m', 'PyInstaller', '--noconfirm', '--clean', '--log-level', 'WARN', '--onedir', '--strip'] + excludes + [
         '--name', 'uhdl', '--contents-directory', '_uhdl',
         '--distpath', os.path.join(work, 'dist'), '--workpath', os.path.join(work, 'pyi'),
         '--specpath', work,
         '--collect-all', 'uhdl', '--copy-metadata', 'uhdl',
         '--add-binary', '%s:uhdl/_native' % lib,
         '--add-data', '%s:pysrc' % pysrc] + hidden + [entry])

    # 5. the component archive, laid out as motryx-toolkit expects (scripts/update_component_lock.py,
    #    same layout as wave_reader's scripts/ci/package_component.sh): at the archive root
    #    uhdl, _uhdl/ (its onedir runtime), skill/ (copied to skills/uhdl/ by the toolkit) and
    #    component-manifest.json
    rev = git('rev-parse', 'HEAD')
    dirty = git('status', '--porcelain', '--', 'uhdl', 'skill', 'docs', 'packaging', 'native')
    release_tag = a.release_tag or 'main-' + rev[:12]
    epoch = int(git('show', '-s', '--format=%ct', rev))
    archive_name = '%s-%s-linux-x86_64.tar.gz' % (COMPONENT, version)
    stage = os.path.join(work, 'stage')
    os.makedirs(stage)
    shutil.copy2(os.path.join(work, 'dist', 'uhdl', 'uhdl'), os.path.join(stage, 'uhdl'))
    os.chmod(os.path.join(stage, 'uhdl'), 0o755)
    shutil.copytree(os.path.join(work, 'dist', 'uhdl', '_uhdl'), os.path.join(stage, '_uhdl'), symlinks=False)
    sk = os.path.join(stage, 'skill', SKILL_NAME)
    shutil.copytree(SKILL, sk, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    os.makedirs(os.path.join(sk, 'references'), exist_ok=True)
    shutil.copy(os.path.join(ROOT, 'docs', 'LLM_GUIDE.md'), os.path.join(sk, 'references', 'guide.md'))
    shutil.copy(os.path.join(ROOT, 'docs', 'llm_example', 'gen.py'), os.path.join(sk, 'references', 'example_gen.py'))

    exe = os.path.join(stage, 'uhdl')
    skill_sha, skill_n = tree_sha(os.path.join(stage, 'skill'))
    rt_sha, rt_n = tree_sha(os.path.join(stage, '_uhdl'))
    manifest = {
        'schema_version': 1,
        'component': COMPONENT,
        'component_version': version,
        'archive_name': archive_name,
        'repository': a.repository,
        'source_commit': rev,
        'release_tag': release_tag,
        'platform': 'linux-x86_64',
        'source_date_epoch': epoch,
        'binary': {'path': 'uhdl', 'sha256': file_sha(exe), 'size_bytes': os.path.getsize(exe), 'executable': True},
        'runtime': {'path': '_uhdl', 'sha256_tree': rt_sha, 'file_count': rt_n},
        'skill': {'path': 'skill', 'sha256_tree': skill_sha, 'file_count': skill_n},
        # informational, not part of the toolkit contract
        'build': {'python': '%d.%d' % pyver, 'pyinstaller': PYINSTALLER.split('==')[1],
                  'build_machine_glibc': '%s %s' % platform.libc_ver(), 'glibc_needed': max_glibc(stage),
                  'source_dirty': bool(dirty)},
    }
    text = json.dumps(manifest, indent=2, sort_keys=True) + '\n'
    open(os.path.join(stage, 'component-manifest.json'), 'w').write(text)

    os.makedirs(out, exist_ok=True)
    archive = os.path.join(out, archive_name)
    for p in (archive, archive + '.sha256', os.path.join(out, 'component-manifest.json')):
        if os.path.exists(p):
            os.remove(p)
    open(os.path.join(out, 'component-manifest.json'), 'w').write(text)
    write_archive(stage, archive, ['uhdl', '_uhdl', 'skill', 'component-manifest.json'], epoch)
    open(archive + '.sha256', 'w').write('%s  %s\n' % (file_sha(archive), archive_name))
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(stage) for f in fs)
    shutil.rmtree(work, ignore_errors=True)
    if dirty:
        print('warning: the source tree has uncommitted changes; this build is not a release', file=sys.stderr)
    print('component %s (%s): %s, %.1f MB archive, %.0f MB unpacked, glibc %s'
          % (version, release_tag, archive, os.path.getsize(archive) / 1e6, size / 1e6, manifest['build']['glibc_needed']))


def git(*args):
    return subprocess.run(['git', '-c', 'safe.directory=*', '-C', ROOT] + list(args),
                          capture_output=True, text=True, check=True).stdout.strip()


def write_archive(stage, archive, members, epoch):
    """Reproducible tar.gz: sorted names, root ownership, the commit time, no gzip timestamp."""
    import gzip, io
    def norm(ti):
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = ''
        ti.mtime = epoch
        return ti
    entries = []
    for m in members:
        root = os.path.join(stage, m)
        entries.append(m)
        if os.path.isdir(root):
            for d, dirs, files in os.walk(root):
                for x in dirs + files:
                    entries.append(os.path.relpath(os.path.join(d, x), stage))
    with open(archive, 'wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode='w', format=tarfile.PAX_FORMAT) as t:
                for e in sorted(entries):
                    p = os.path.join(stage, e)
                    if os.path.islink(p):
                        raise SystemExit('links are not allowed in the component: %s' % e)
                    t.add(p, arcname=e, recursive=False, filter=norm)

if __name__ == '__main__':
    main()
