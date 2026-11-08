# UHDL toolkit component and Skill

`skill/uhdl-design/` is the agent Skill (named `uhdl-design`, not `uhdl`: agents misread the short
path `r1/uhdl/SKILL.md` under a root that already ends in `skills/uhdl`). `packaging/build_component.py` builds a toolkit component around it:
a frozen `uhdl` command that brings its own Python and UHDL. SystemVerilog is read by UHDL's own
`libuhdl_slang.so` (slang behind a C interface, loaded with ctypes); no pyslang.

## Build

```bash
python native/build.py --cxx <g++ whose sysroot is glibc 2.17>     # uhdl/_native/libuhdl_slang.so
python packaging/build_component.py --python <python3.12 built for glibc 2.17> [--out dist/component] \
    [--release-tag v<version>]
```
Result in `dist/component/`, the files of a motryx-toolkit component release (same layout as
wave_reader's `scripts/ci/package_component.sh`, accepted by the toolkit's
`scripts/update_component_lock.py`):

| File | |
|---|---|
| `uhdl-<version>-linux-x86_64.tar.gz` | the archive (reproducible: sorted, root-owned, commit time) |
| `uhdl-<version>-linux-x86_64.tar.gz.sha256` | `<sha256>  <archive name>` |
| `component-manifest.json` | the same manifest as inside the archive |

Archive root:

| Path | |
|---|---|
| `uhdl` | frozen entry point (PyInstaller onedir); the toolkit installs it as `bin/uhdl` |
| `_uhdl/` | its runtime (`bin/_uhdl/`): Python with the standard library, uhdl with `uhdl/_native/libuhdl_slang.so`, and `pysrc/` (uhdl as plain source for other Pythons) |
| `skill/uhdl-design/` | `SKILL.md`, `references/guide.md` (from `docs/LLM_GUIDE.md`), `references/example_gen.py` (from `docs/llm_example/gen.py`); the toolkit installs `skill/` as `skills/uhdl/` |
| `component-manifest.json` | schema 1: component, version, repository, source commit, release tag (`main-<commit[:12]>` by default), binary hash and size, runtime and Skill tree hashes; plus an informational `build` record (Python, PyInstaller, `glibc_needed`, `source_dirty`) |

About 34 MB unpacked, 14 MB archive. Binaries are stripped. Building needs PyPI for PyInstaller;
the result runs offline. Build from a committed tree: the manifest names the commit.

**glibc:** `libuhdl_slang.so` needs only its compiler's sysroot glibc (conda-forge `gxx_linux-64`
13 with `sysroot_linux-64=2.17` gives 2.17; `native/build.py` checks it). The frozen Python needs
what its interpreter was built for (a conda-forge Python on the 2.17 sysroot gives 2.17).
`build.glibc_needed` is the newest glibc any ELF file in the component needs.

## The `uhdl` command

| Command | |
|---|---|
| `uhdl run gen.py ARGS` | run a generator with the bundled Python |
| `uhdl check OUT --top T [--sv F]` | Verilator `-Wall` lint + Yosys synth/`check -assert`, messages mapped to Python lines |
| `uhdl python [-c/-m/FILE]` | the bundled Python (interactive without arguments) |
| `uhdl pythonpath --python PY` | PYTHONPATH that lets another Python 3.8+ import this UHDL, SystemVerilog import included. For generators that also need the user's own libraries. |
| `uhdl version` | |

From an installed package the same commands are `python -m uhdl ...` (or `uhdl` from `pip install`).

## Tests

```bash
mkdir -p /tmp/c && tar -xzf dist/component/uhdl-<ver>-linux-x86_64.tar.gz -C /tmp/c
python skill/tests/check_toolkit_contract.py --toolkit <motryx-toolkit checkout> --dist dist/component --work <dir>
python skill/tests/test_component.py --component /tmp/c --work <dir> \
    --python /path/python3.8 --python /usr/bin/python3.9 --python /path/python3.14 [--user-venv <venv python>]
python skill/tests/test_check.py --uhdl /tmp/c/uhdl --work <dir>
# agent end to end: setup.sh / grade.sh, or run_headless.sh for a real `claude -p` run
bash skill/tests/e2e/run_headless.sh /tmp/c <dir> t1 t1-run
bash skill/tests/e2e/grade.sh <dir>/t1-run t1 /tmp/c
```
`check_toolkit_contract.py` runs the toolkit's own `update_component_lock.py` and
`package_toolkit.verify_component_archive` on the release, stages it like a toolkit release and
uses it from there. `e2e/t1` (round-robin arbiter) and `e2e/t2` (filter around an imported SV FIFO)
have hidden testbenches, each checked against a reference and a mutant.
