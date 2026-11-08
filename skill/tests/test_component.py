"""Test a built UHDL component (packaging/build_component.py) the way an agent uses it.

    python skill/tests/test_component.py --component dist/component/uhdl-<ver>-linux-x86_64 \\
        --work /some/scratch --python /path/python3.8 --python /usr/bin/python3.9 ... \\
        [--user-venv /path/venv/bin/python]    # a venv with prettytable installed

Frozen command, in an environment with no usable Python on PATH:
  version, run (the guide's example), check, SV import, the standard library, stdin, errors.
Each --python: `uhdl pythonpath --python X` then X runs a generator that imports SV.
--user-venv: a generator importing both a library of that venv and UHDL.
Also: a component without the wheel for a Python (SV import reported as unavailable), and
parallel `pythonpath` calls sharing one extracted pyslang.
"""
import argparse, json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ap = argparse.ArgumentParser()
ap.add_argument('--component', required=True); ap.add_argument('--work', required=True)
ap.add_argument('--python', action='append', default=[]); ap.add_argument('--user-venv')
A = ap.parse_args()
C = os.path.abspath(A.component); T = os.path.abspath(A.work)
shutil.rmtree(T, ignore_errors=True); os.makedirs(T)
HERE = os.path.dirname(os.path.abspath(__file__))
for f in ('pkg.sv', 'cells.sv'):
    shutil.copy(os.path.join(HERE, 'data', f), T)
UHDL = os.path.join(C, 'bin', 'uhdl')
BARE = {'HOME': os.environ['HOME'], 'PATH': '/usr/bin:/bin', 'TMPDIR': T, 'UHDL_CACHE': os.path.join(T, 'cache')}
TOOLS = dict(BARE, PATH='/usr/bin:/bin:' + os.path.dirname(shutil.which('verilator') or '/x') + ':' + os.path.dirname(shutil.which('yosys') or '/x'))
ok_all = True


def sh(cmd, env=BARE, inp=None):
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=T, input=inp)


def expect(name, cond, detail=''):
    global ok_all
    ok_all &= bool(cond)
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '\n    ' + str(detail).replace('\n', '\n    ')[-1500:]))


SVGEN = '''import sys, importlib.metadata as m
from uhdl import *
pk = import_sv_package(['pkg.sv'], 'my_pkg')
c = VComponent(file='pkg.sv cells.sv', top='sreg', slang_opts='--ignore-unknown-modules --single-unit', struct_mode='packed')
print('SV OK py%d.%d pyslang %s width %d %s' % (sys.version_info[0], sys.version_info[1], m.version('pyslang'), pk.req_t.width,
      'bundled-uhdl' if '/_uhdl/pysrc/' in __import__('uhdl').__file__ else 'OTHER-uhdl'))
'''
open(os.path.join(T, 'sv_gen.py'), 'w').write(SVGEN)

# ---- frozen command
r = sh([UHDL, 'version']); expect('frozen: version', r.returncode == 0 and 'frozen' in r.stdout and 'pyslang 12' in r.stdout, r.stdout + r.stderr)
ex = os.path.join(C, 'skills', 'uhdl', 'uhdl-design', 'references', 'example_gen.py')
r = sh([UHDL, 'run', ex, '--out', 'o_ex']); expect('frozen: run the guide example', r.returncode == 0 and os.path.isfile(os.path.join(T, 'o_ex', 'filelist.f')), r.stderr)
top = [l for l in open(os.path.join(T, 'o_ex', 'filelist.f')).read().split() if l.endswith('.v')][-1].split('/')[-1][:-2] if r.returncode == 0 else 'x'
r = sh([UHDL, 'check', 'o_ex', '--top', top], TOOLS); expect('frozen: check -> CHECK PASS', r.returncode == 0 and 'CHECK PASS' in r.stdout, r.stdout + r.stderr)
r = sh([UHDL, 'run', 'sv_gen.py']); expect('frozen: SV import with bundled pyslang', 'SV OK' in r.stdout and 'width 12' in r.stdout, r.stdout + r.stderr)
mods = 'json math argparse itertools dataclasses fractions functools collections re csv statistics random textwrap pathlib typing enum decimal hashlib shutil subprocess glob copy pprint string struct zlib tempfile unittest logging datetime operator heapq bisect concurrent.futures multiprocessing xml.etree.ElementTree'
r = sh([UHDL, 'python', '-c', 'import ' + ', '.join(mods.split()) + '; print("stdlib ok")'])
expect('frozen: standard library modules', 'stdlib ok' in r.stdout, r.stderr)
r = sh([UHDL, 'python'], inp='import uhdl\nprint("stdin ok")\n'); expect('frozen: script on stdin', 'stdin ok' in r.stdout, r.stdout + r.stderr)
r = sh([UHDL, 'python', '-c', 'import sys; sys.exit(3)']); expect('frozen: exit status passes through', r.returncode == 3, r.returncode)
open(os.path.join(T, 'bad.py'), 'w').write('from uhdl import *\nclass t(Component):\n    def circuit(s):\n        s.a = Input(2); s.y = Output(1)\n        s.y += s.a\nt()\n')
r = sh([UHDL, 'run', 'bad.py']); expect('frozen: UHDL error names the Python line', r.returncode != 0 and 'bad.py:5: s.y += s.a' in r.stderr, r.stderr)

# ---- other Pythons through pythonpath
for py in A.python:
    r = sh([UHDL, 'pythonpath', '--python', py])
    if r.returncode != 0:
        expect('pythonpath %s' % py, False, r.stderr); continue
    v = sh([py, 'sv_gen.py'], dict(BARE, PYTHONPATH=r.stdout.strip()))
    expect('pythonpath: %s runs UHDL + SV import' % py, 'SV OK' in v.stdout and 'bundled-uhdl' in v.stdout, v.stdout + v.stderr + r.stderr)
    print('    ' + v.stdout.strip())
if A.user_venv:
    open(os.path.join(T, 'mix_gen.py'), 'w').write('from prettytable import PrettyTable\n' + SVGEN + 'print("user lib ok", PrettyTable.__name__)\n')
    r = sh([UHDL, 'pythonpath', '--python', A.user_venv])
    v = sh([A.user_venv, 'mix_gen.py'], dict(BARE, PYTHONPATH=r.stdout.strip()))
    expect('pythonpath: user venv library + UHDL together', 'user lib ok' in v.stdout and 'SV OK' in v.stdout, v.stdout + v.stderr)

# ---- a component without the wheels for one Python
if A.python:
    py = A.python[0]
    ver = sh([py, '-c', 'import sys; print("cp%d%d" % sys.version_info[:2])']).stdout.strip()
    C2 = os.path.join(T, 'comp_nowheel'); shutil.copytree(C, C2, symlinks=True)
    wd = os.path.join(C2, 'bin', '_uhdl', 'wheels')
    for w in os.listdir(wd):
        if '-%s-' % ver in w or (ver >= 'cp311' and 'abi3' in w):
            os.remove(os.path.join(wd, w))
    r = sh([os.path.join(C2, 'bin', 'uhdl'), 'pythonpath', '--python', py], dict(BARE, UHDL_CACHE=os.path.join(T, 'cache2')))
    v = sh([py, '-c', 'import uhdl; print("uhdl ok")'], dict(BARE, PYTHONPATH=r.stdout.strip()))
    has_own = sh([py, '-c', 'import pyslang']).returncode == 0
    expect('no wheel for %s: UHDL works, SV import reported unavailable' % ver,
           r.returncode == 0 and 'uhdl ok' in v.stdout and (has_own or 'SV import' in r.stderr), r.stderr + v.stderr)

# ---- parallel pythonpath calls share one extraction
if A.python:
    py = A.python[-1]
    env = dict(BARE, UHDL_CACHE=os.path.join(T, 'cache3'))
    with ThreadPoolExecutor(6) as pool:
        outs = list(pool.map(lambda _: sh([UHDL, 'pythonpath', '--python', py], env), range(6)))
    paths = {o.stdout.strip() for o in outs}
    v = sh([py, 'sv_gen.py'], dict(BARE, PYTHONPATH=paths.pop())) if len(paths) == 1 else None
    left = [d for d in os.listdir(os.path.join(T, 'cache3'))] if os.path.isdir(os.path.join(T, 'cache3')) else []
    expect('parallel pythonpath: one result, usable, no leftovers',
           all(o.returncode == 0 for o in outs) and v is not None and ('SV OK' in v.stdout or sh([py, '-c', 'import pyslang']).returncode == 0)
           and not any('.tmp' in d for d in left), [o.stderr for o in outs] + left)

print('ALL PASS' if ok_all else 'SOME FAILED')
sys.exit(0 if ok_all else 1)
