"""Drive uhdl_env.sh through many base Pythons, offline, then use each result for real work.

    python skill/tests/test_env.py --bundle dist/skill/uhdl --work /some/scratch \
        --py38 /path/python3.8 --py314 /path/python3.14 [--sys39 /usr/bin/python3.9] [--py313 ...]

For each base Python: build the venv with networking blocked, check versions, generate the
guide's example, run uhdl_check.py, and import SV through pyslang. Also: no ensurepip, no venv
module, a bundle without a matching pyslang wheel, choosing Python from PATH, and a rerun.
"""
import argparse, os, shutil, subprocess, sys, time
ap = argparse.ArgumentParser()
ap.add_argument('--bundle', required=True); ap.add_argument('--work', required=True)
ap.add_argument('--py38', required=True); ap.add_argument('--py314', required=True)
ap.add_argument('--py313'); ap.add_argument('--sys39')
A = ap.parse_args()
T = os.path.abspath(A.work); os.makedirs(T, exist_ok=True)
SK = os.path.abspath(A.bundle)
HERE = os.path.dirname(os.path.abspath(__file__))
for f in ('pkg.sv', 'cells.sv'):
    shutil.copy(os.path.join(HERE, 'data', f), T)
OFFLINE = dict(PIP_INDEX_URL='http://127.0.0.1:9/simple', http_proxy='http://127.0.0.1:9',
               https_proxy='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9', HTTP_PROXY='http://127.0.0.1:9',
               PIP_NO_CACHE_DIR='1', TMPDIR=T)

def py(v):
    return {'3.8': A.py38, '3.14': A.py314}[v]

def wrapper(name, real, fail_if):
    p = f'{T}/wrap_{name}'
    open(p, 'w').write(f'#!/bin/bash\ncase "$*" in {fail_if}) echo "simulated: no venv" >&2; exit 1;; esac\nexec {real} "$@"\n')
    os.chmod(p, 0o755); return p

CASES = [
    ('py3.8',            dict(UHDL_PYTHON=py('3.8')), 'yes', '8.1.0'),
    ('py3.13',           dict(UHDL_PYTHON=A.py313 or ''), 'yes', '12.1.0'),
    ('sys3.9-nopip',     dict(UHDL_PYTHON=A.sys39 or ''), 'yes', '8.1.0'),
    ('py3.14',           dict(UHDL_PYTHON=py('3.14')), 'yes', '12.1.0'),
    ('auto-from-PATH',   dict(PATH=os.path.dirname(A.py314) + ':/usr/bin:/bin'), 'yes', '12.1.0'),
    ('no-ensurepip',     dict(UHDL_PYTHON=f'{T}/wrap_noensure'), 'yes', '12.1.0'),
    ('no-venv-module',   dict(UHDL_PYTHON=wrapper('novenv', py('3.8'), '"-m venv"*')), 'yes', '8.1.0'),
]
# no-ensurepip: plain "-m venv DIR" fails, "-m venv --without-pip DIR" works
CASES = [c for c in CASES if c[1].get('UHDL_PYTHON', 'x')]      # drop the optional Pythons not given
open(f'{T}/wrap_noensure', 'w').write(f'#!/bin/bash\nif [ "$1" = -m ] && [ "$2" = venv ] && [ "$3" != --without-pip ]; then echo "simulated: ensurepip missing" >&2; exit 1; fi\nexec {py("3.14")} "$@"\n')
os.chmod(f"{T}/wrap_noensure", 0o755)

WORK = '''
import os, sys, subprocess
sys.argv = ['gen.py']
from uhdl import *
import importlib.util
spec = importlib.util.spec_from_file_location('ex', os.path.join(SK, 'references', 'example_gen.py'))
'''
def sh(cmd, env=None, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, env=env, **kw)

ok_all = True
# a bundle without the Python 3.8 pyslang wheel: UHDL alone, with a clear message
NOSV = f'{T}/dist_nosv/uhdl'
shutil.rmtree(f'{T}/dist_nosv', ignore_errors=True); shutil.copytree(SK, NOSV)
for w in os.listdir(f'{NOSV}/wheels'):
    if 'cp38' in w: os.remove(f'{NOSV}/wheels/{w}')
CASES.append(('no-pyslang-wheel', dict(UHDL_PYTHON=py('3.8'), _SKILL=NOSV), 'no', ''))
for name, extra, want_sv, want_pyslang in CASES + [('rerun-py3.8', dict(UHDL_PYTHON=py('3.8')), 'yes', '8.1.0')]:
    SK = extra.pop('_SKILL', os.path.abspath(A.bundle))
    venv = f'{T}/venvs/{name.replace("rerun-", "")}'
    if not name.startswith('rerun'):
        shutil.rmtree(venv, ignore_errors=True)
    env = dict(os.environ, **OFFLINE, UHDL_VENV=venv); env.pop('UHDL_ALLOW_NETWORK', None); env.pop('BASH_ENV', None)  # the sandbox's BASH_ENV resets PATH
    env.update(extra)
    t0 = time.time()
    r = sh(['/bin/bash', f'{SK}/scripts/uhdl_env.sh'], env)
    dt = time.time() - t0
    vpy = r.stdout.strip()
    notes = [l for l in r.stderr.splitlines() if l.startswith('[uhdl_env]')]
    res = {'rc': r.returncode, 'secs': round(dt, 1), 'python': vpy}
    if r.returncode == 0:
        ver = sh([vpy, '-c', 'import sys,importlib.metadata as m; print("%d.%d" % sys.version_info[:2], m.version("uhdl"), m.version("pyslang"))'], dict(env, PATH='/usr/bin:/bin'))
        res['versions'] = ver.stdout.strip() or ver.stderr.strip()[-200:]
        out = f'{T}/out_{name}'; shutil.rmtree(out, ignore_errors=True)
        g = sh([vpy, f'{SK}/references/example_gen.py', '--out', out], env, cwd=T)
        res['example_gen'] = g.returncode
        # the example's top module name: last module written
        top = [l for l in open(f'{out}/filelist.f').read().split() if l.endswith('.v')][-1].split('/')[-1][:-2] if g.returncode == 0 else '?'
        c = sh([vpy, f'{SK}/scripts/uhdl_check.py', out, '--top', top], dict(os.environ))
        res['check'] = c.stdout.strip().splitlines()[-1] if c.stdout else c.stderr[-200:]
        v = sh([vpy, '-c', f'''
from uhdl import *
pk = import_sv_package(['{T}/pkg.sv'], 'my_pkg')
c = VComponent(file='{T}/pkg.sv {T}/cells.sv', top='sreg', slang_opts='--ignore-unknown-modules --single-unit', struct_mode='packed')
print('sv-import ok', pk.req_t.width, c.i.attribute.width)'''], env, cwd=T)
        res['sv_import'] = v.stdout.strip() or v.stderr.strip().splitlines()[-1]
    good = (r.returncode == 0 and res.get('example_gen') == 0 and res.get('check', '').startswith('CHECK PASS')
            and ('sv-import ok' in res.get('sv_import', '')) == (want_sv == 'yes')
            and (res.get('versions', '').endswith(want_pyslang) if want_pyslang else 'pyslang' in res.get('versions', '')))
    ok_all &= good
    print(('PASS ' if good else 'FAIL ') + name, res)
    if not good or name.startswith(('no-', 'sys')):
        print('   ', '\n    '.join(notes[-4:] + r.stderr.splitlines()[-3:] if not good else notes[-2:]))
print('ALL PASS' if ok_all else 'SOME FAILED')
