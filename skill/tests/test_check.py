"""uhdl_check.py: lint and synthesis messages map to Python lines; missing tools and imported SV.

    python skill/tests/test_check.py --bundle dist/skill/uhdl --work /some/scratch --python <python with UHDL>
"""
import argparse, os, subprocess, sys, shutil
ap = argparse.ArgumentParser()
ap.add_argument('--bundle', required=True); ap.add_argument('--work', required=True); ap.add_argument('--python', required=True)
ap.add_argument('-v', action='store_true')
A = ap.parse_args()
T = os.path.abspath(A.work); SK = os.path.abspath(A.bundle); PY = A.python
os.makedirs(f'{T}/ck', exist_ok=True)
open(f'{T}/ck/bad_gen.py', 'w').write('''import sys
from uhdl import *
class bad(Component):
    MODULE_NAME = 'bad'
    def circuit(s):
        s.a, s.b = Input(4), Input(4)      # LINE6: b is never used
        s.y = Output(4)
        s.y += s.a
bad().generate(sys.argv[1])
''')
open(f'{T}/ck/loop_gen.py', 'w').write('''import sys
from uhdl import *
class loopy(Component):
    MODULE_NAME = 'loopy'
    def circuit(s):
        s.a = Input(1); s.y = Output(1)
        x = s.wire('x', s.a)
        z = s.create('z', Wire(UInt(1)))
        z += x ^ s.y                        # LINE9: y depends on z, z on y
        s.y += z & s.a
loopy().generate(sys.argv[1])
''')
def run(*c, **kw): return subprocess.run(list(c), capture_output=True, text=True, **kw)
ok = True
def expect(name, cond, out):
    global ok; ok &= bool(cond); print(('PASS ' if cond else 'FAIL ') + name); print('   ' + out.replace('\n', '\n   ')) if not cond or A.v else None
r = run(PY, f'{T}/ck/bad_gen.py', f'{T}/ck/o_bad'); assert r.returncode == 0, r.stderr
c = run(PY, f'{SK}/scripts/uhdl_check.py', f'{T}/ck/o_bad', '--top', 'bad')
expect('unused input -> FAIL, mapped to bad_gen.py:6', c.returncode == 1 and 'UNUSED' in c.stdout and 'python: bad_gen.py:6' in c.stdout, c.stdout)
r = run(PY, f'{T}/ck/loop_gen.py', f'{T}/ck/o_loop'); assert r.returncode == 0, r.stderr
c = run(PY, f'{SK}/scripts/uhdl_check.py', f'{T}/ck/o_loop', '--top', 'loopy')
expect('combinational loop -> FAIL, mapped to python lines (lint and yosys)', c.returncode == 1 and 'python: loop_gen.py:' in c.stdout and '[python: loop_gen.py:9' in c.stdout, c.stdout)
env = dict(os.environ, PATH=os.path.dirname(PY) + ':/usr/bin:/bin'); env.pop('BASH_ENV', None)
c = run(PY, f'{SK}/scripts/uhdl_check.py', f'{T}/ck/o_bad', '--top', 'bad', env=env)
expect('no verilator/yosys -> SKIPPED, not a lint pass', 'lint   SKIPPED' in c.stdout and 'synth  SKIPPED' in c.stdout and 'CHECK NOT RUN' in c.stdout and c.returncode == 2, c.stdout)
c = run(PY, f'{SK}/scripts/uhdl_check.py', f'{T}/ck/nope', '--top', 'x')
expect('missing out dir -> FAIL with hint', c.returncode == 1 and 'Run generate' in c.stdout, c.stdout)

# imported SV that Yosys cannot read (a class): synthesis is SKIPPED, not FAIL; lint still runs
open(f'{T}/ck/odd.sv', 'w').write("""package odd_pkg;
  class helper; int x; endclass
endpackage
module odd_inv (input logic [3:0] a, output logic [3:0] y);
  assign y = ~a;
endmodule
""")
open(f'{T}/ck/odd_gen.py', 'w').write(f"""import sys
from uhdl import *
class wrap(Component):
    MODULE_NAME = 'wrap'
    def circuit(s):
        s.a = Input(4); s.y = Output(4)
        s.u = VComponent(file='{T}/ck/odd.sv', top='odd_inv')
        s.u.a += s.a
        s.y += s.u.y
wrap().generate(sys.argv[1])
""")
r = run(PY, f'{T}/ck/odd_gen.py', f'{T}/ck/o_odd'); assert r.returncode == 0, r.stderr
c = run(PY, f'{SK}/scripts/uhdl_check.py', f'{T}/ck/o_odd', '--top', 'wrap', '--sv', f'{T}/ck/odd.sv')
expect('imported SV yosys cannot parse -> synth SKIPPED, lint PASS', 'lint   PASS' in c.stdout and 'synth  SKIPPED' in c.stdout and 'cannot read the imported SV odd.sv' in c.stdout and c.returncode == 0, c.stdout)
print('ALL PASS' if ok else 'SOME FAILED')
