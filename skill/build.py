#!/usr/bin/env python3
"""Build the UHDL agent skill: skill/uhdl + guide + example + wheels, ready to copy.

    python skill/build.py [--out dist/skill] [--platform linux-x86_64 ...]

Result: <out>/uhdl/ (install by copying it to ~/.claude/skills/uhdl or <project>/.claude/skills/uhdl)
and <out>/uhdl-skill-<version>.tar.gz. The wheels/ directory holds:
  uhdl (built from this checkout), pip (a recent one, for old system pips), and pyslang with its
  dependencies for every supported Python: 8.1.0 for 3.8-3.10, 12.1.0 for 3.11-3.15.
Needs network access to PyPI (build time only); the result installs offline.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'skill', 'uhdl')

PLATFORMS = {                      # name -> pip --platform tags (pip accepts several)
    'linux-x86_64':  ['manylinux_2_28_x86_64', 'manylinux_2_27_x86_64'],
    'linux-aarch64': ['manylinux_2_28_aarch64', 'manylinux_2_27_aarch64'],
    'macos-arm64':   ['macosx_11_0_arm64'],
    'macos-x86_64':  ['macosx_11_0_universal2'],
    'windows-amd64': ['win_amd64'],
}
# pyslang 8.1.0 for Python 3.8-3.10. pyslang 12.1.0 is one abi3 wheel, but its dependency
# nanobind-backend is built per Python version, so 3.11-3.15 are each downloaded.
PYSLANG = [('8.1.0', v) for v in ('3.8', '3.9', '3.10')] + [('12.1.0', v) for v in ('3.11', '3.12', '3.13', '3.14', '3.15')]
PIP = 'pip==24.3.1'                # the last pip that supports Python 3.8


def run(cmd):
    print('+', ' '.join(cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'dist', 'skill'))
    ap.add_argument('--platform', action='append', choices=sorted(PLATFORMS), help='default: linux-x86_64')
    a = ap.parse_args()
    plats = a.platform or ['linux-x86_64']

    dst = os.path.join(a.out, 'uhdl')
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    refs = os.path.join(dst, 'references')
    os.makedirs(refs, exist_ok=True)
    shutil.copy(os.path.join(ROOT, 'docs', 'LLM_GUIDE.md'), os.path.join(refs, 'guide.md'))
    shutil.copy(os.path.join(ROOT, 'docs', 'llm_example', 'gen.py'), os.path.join(refs, 'example_gen.py'))

    wheels = os.path.join(dst, 'wheels')
    os.makedirs(wheels)
    run([sys.executable, '-m', 'pip', 'wheel', '-q', '--no-deps', '-w', wheels, ROOT])
    for egg in ('build', 'uhdl.egg-info'):
        shutil.rmtree(os.path.join(ROOT, egg), ignore_errors=True)
    run([sys.executable, '-m', 'pip', 'download', '-q', '--no-deps', '--only-binary', ':all:', '-d', wheels, PIP])
    for plat in plats:
        for ver, py in PYSLANG:
            cp = 'cp' + py.replace('.', '')
            cmd = [sys.executable, '-m', 'pip', 'download', '-q', '--only-binary', ':all:', '-d', wheels,
                   '--python-version', py, '--implementation', 'cp', '--abi', cp, '--abi', 'abi3', '--abi', 'none']
            for t in PLATFORMS[plat]:
                cmd += ['--platform', t]
            run(cmd + ['pyslang==' + ver])

    uhdl_whl = [w for w in os.listdir(wheels) if w.startswith('uhdl-')][0]
    rev = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', ROOT, 'status', '--porcelain', '--', 'uhdl', 'skill', 'docs'],
                           capture_output=True, text=True).stdout.strip()
    version = '%s+%s%s' % (uhdl_whl.split('-')[1], rev or 'nogit', '.dirty' if dirty else '')
    with open(os.path.join(dst, 'VERSION'), 'w') as f:
        f.write(version + '\n')
    with open(os.path.join(dst, 'wheels', 'PLATFORMS'), 'w') as f:
        f.write('\n'.join(plats) + '\n')
    for p in ('scripts/uhdl_env.sh', 'scripts/uhdl_check.py'):
        os.chmod(os.path.join(dst, p), 0o755)

    tar = os.path.join(a.out, 'uhdl-skill-%s.tar.gz' % version)
    with tarfile.open(tar, 'w:gz') as t:
        t.add(dst, arcname='uhdl')
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(dst) for f in fs)
    print('skill %s (%s): %s  %.1f MB\n  %s' % (version, ', '.join(plats), dst, size / 1e6, tar))


if __name__ == '__main__':
    main()
