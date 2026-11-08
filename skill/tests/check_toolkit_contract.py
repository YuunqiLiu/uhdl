"""Check a built uhdl component against motryx-toolkit's own code, then run it as installed.

    python skill/tests/check_toolkit_contract.py --toolkit /path/to/motryx-toolkit \\
        --dist dist/component --work /some/scratch

1. scripts/update_component_lock.py (the toolkit's lock updater) accepts the archive, its
   .sha256 sidecar and component-manifest.json, and writes a lock entry. uhdl is added to its
   allowlist for this run, and the qualification record that CI would write is synthesized.
2. scripts/package_toolkit.py's verify_component_archive accepts the archive against that entry.
3. The component is staged the way package_toolkit stages it (bin/uhdl, bin/_uhdl/,
   skills/uhdl/) and run from there: version, the guide's example, `uhdl check`, SV import, and
   the Skill's fallback path <skill dir>/../../../bin/uhdl.
Nothing in the toolkit checkout is modified.
"""
import argparse, glob, json, os, shutil, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--toolkit', required=True); ap.add_argument('--dist', required=True); ap.add_argument('--work', required=True)
A = ap.parse_args()
TK = Path(A.toolkit).resolve(); D = Path(A.dist).resolve(); W = Path(A.work).resolve()
shutil.rmtree(W, ignore_errors=True); W.mkdir(parents=True)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(TK / 'scripts'))
import update_component_lock as ucl          # noqa: E402  (the toolkit's code, unchanged)
import package_toolkit as pt                 # noqa: E402

ok_all = True


def expect(name, cond, detail=''):
    global ok_all
    ok_all &= bool(cond)
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '\n    ' + str(detail)[-1500:]))


archive = Path(glob.glob(str(D / 'uhdl-*-linux-x86_64.tar.gz'))[0])
manifest_path = D / 'component-manifest.json'
manifest = json.loads(manifest_path.read_text())
sha = ucl.sha256_file

# ---- 1. the toolkit's lock updater
ucl.ALLOWED_COMPONENTS['uhdl'] = manifest['repository']      # the toolkit adds this when it integrates uhdl
qualification = {
    'schema_version': 1, 'component': 'uhdl', 'component_version': manifest['component_version'],
    'repository': manifest['repository'], 'source_commit': manifest['source_commit'],
    'snapshot_tag': manifest['release_tag'], 'archive_name': archive.name,
    'archive_sha256': sha(archive), 'manifest_sha256': sha(manifest_path),
    'workflow': {'event': 'push', 'path': '.github/workflows/release.yml', 'run_id': 1, 'run_attempt': 1},
}
qpath = W / 'qualification.json'
qpath.write_text(json.dumps(qualification))
lock = W / 'components.lock.json'
shutil.copy(TK / 'components.lock.json', lock)
argv = ['update_component_lock.py', '--component', 'uhdl', '--repository', manifest['repository'],
        '--source-sha', manifest['source_commit'], '--release-tag', 'v' + manifest['component_version'],
        '--artifact-release-tag', manifest['release_tag'], '--archive', str(archive),
        '--checksum', str(archive) + '.sha256', '--manifest', str(manifest_path),
        '--archive-sha256', sha(archive), '--manifest-sha256', sha(manifest_path),
        '--qualification', str(qpath), '--qualification-sha256', sha(qpath), '--lock', str(lock)]
old_argv, sys.argv = sys.argv, argv
try:
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        rc = ucl.main()
    err = ''
except SystemExit as e:
    rc, err = (e.code if isinstance(e.code, int) else 1), str(e)
finally:
    sys.argv = old_argv
entry = json.loads(lock.read_text())['components'].get('uhdl')
expect('update_component_lock.py accepts the release (archive, sidecar, manifest)', rc == 0 and entry, err)
if not entry:
    print('SOME FAILED'); sys.exit(1)

# ---- 2. package_toolkit's archive verification
ext = W / 'extracted'; ext.mkdir()
try:
    pt.verify_component_archive('uhdl', entry, archive, ext)
    expect('package_toolkit.verify_component_archive accepts it', True)
except Exception as e:
    expect('package_toolkit.verify_component_archive accepts it', False, e)

# ---- 3. staged like the toolkit release, then used from there
stage = W / 'motryx-toolkit'
(stage / 'bin').mkdir(parents=True); (stage / 'skills').mkdir()
shutil.copy2(ext / manifest['binary']['path'], stage / 'bin' / 'uhdl')
shutil.copytree(ext / manifest['runtime']['path'], stage / 'bin' / manifest['runtime']['path'])
shutil.copytree(ext / 'skill', stage / 'skills' / 'uhdl')
skill = stage / 'skills' / 'uhdl' / 'uhdl-design'
expect('Skill installed at skills/uhdl/uhdl-design/SKILL.md', (skill / 'SKILL.md').is_file())
fallback = (skill / '..' / '..' / '..' / 'bin' / 'uhdl').resolve()
expect('Skill fallback path <skill dir>/../../../bin/uhdl is the binary', fallback == (stage / 'bin' / 'uhdl'))

env = {'HOME': os.environ['HOME'], 'PATH': '/usr/bin:/bin', 'TMPDIR': str(W)}
tools = dict(env, PATH='/usr/bin:/bin:' + ':'.join(os.path.dirname(shutil.which(t) or '/x') for t in ('verilator', 'yosys')))
run = lambda *c, e=env: subprocess.run([str(x) for x in c], capture_output=True, text=True, env=e, cwd=W)
r = run(fallback, 'version')
expect('installed uhdl runs (no Python on PATH)', r.returncode == 0 and 'frozen' in r.stdout, r.stdout + r.stderr)
r = run(fallback, 'run', skill / 'references' / 'example_gen.py', '--out', W / 'o')
expect('installed uhdl runs the Skill example', r.returncode == 0 and (W / 'o' / 'filelist.f').is_file(), r.stderr)
top = [l for l in (W / 'o' / 'filelist.f').read_text().split() if l.endswith('.v')][-1].split('/')[-1][:-2] if r.returncode == 0 else 'x'
r = run(fallback, 'check', W / 'o', '--top', top, e=tools)
expect('installed uhdl check -> CHECK PASS', 'CHECK PASS' in r.stdout, r.stdout + r.stderr)
for f in ('pkg.sv', 'cells.sv'):
    shutil.copy(HERE / 'data' / f, W)
r = run(fallback, 'python', '-c', "from uhdl import *\nc = VComponent(file='pkg.sv cells.sv', top='sreg', "
        "slang_opts='--ignore-unknown-modules --single-unit', struct_mode='packed')\nprint('sv', c.i.attribute.width)")
expect('installed uhdl imports SystemVerilog', 'sv 12' in r.stdout, r.stdout + r.stderr)
print('lock entry:', json.dumps({k: entry[k] for k in ('component_version', 'binary', 'runtime', 'skill')}))
print('ALL PASS' if ok_all else 'SOME FAILED')
sys.exit(0 if ok_all else 1)
