# UHDL toolkit component and Skill

`skill/uhdl-design/` is the agent Skill (named `uhdl-design`, not `uhdl`: agents misread the short
path `r1/uhdl/SKILL.md` under a root that already ends in `skills/uhdl`). `packaging/build_component.py` builds a toolkit component around it:
a frozen `uhdl` command that brings its own Python and UHDL. SystemVerilog is read by UHDL's own
`libuhdl_slang.so` (slang behind a C interface, loaded with ctypes); no pyslang.

## Build

```bash
python packaging/build_component.py --python /path/to/python3.13 [--out dist/component]
```
Result: `dist/component/uhdl-<version>-linux-x86_64/` and the same as a `.tar.gz`:

| Path | |
|---|---|
| `bin/uhdl` | frozen entry point (PyInstaller onedir) |
| `bin/_uhdl/` | its runtime: Python with the full standard library and uhdl (with `uhdl/_native/libuhdl_slang.so`); `pysrc/`, uhdl as plain source with the same library, for other Pythons |
| `skills/uhdl/uhdl-design/` | `SKILL.md`, `references/guide.md` (from `docs/LLM_GUIDE.md`), `references/example_gen.py` (from `docs/llm_example/gen.py`) |
| `manifest.json` | version, source commit, SHA-256 of the binary, runtime tree and Skill tree, build Python and the newest glibc any ELF file needs (`build.glibc_needed`) |

About 100 MB unpacked. Building needs PyPI; the result runs offline. Keep all of `bin/`.

Build `uhdl/_native/libuhdl_slang.so` first: `python native/build.py --cxx <g++>` (needs the
`third_party/slang` and `third_party/fmt` submodules and CMake; no network).

**glibc:** `libuhdl_slang.so` needs only the glibc of its compiler's sysroot: conda-forge
`gxx_linux-64` 13 with `sysroot_linux-64=2.17` gives glibc 2.17 (`native/build.py` checks it). The
frozen Python needs the glibc its interpreter was built for; `manifest.json` records the newest
glibc the whole component needs.

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
python skill/tests/test_component.py --component dist/component/uhdl-<ver>-linux-x86_64 --work <dir> \
    --python /path/python3.8 --python /usr/bin/python3.9 --python /path/python3.14 [--user-venv <venv python>]
python skill/tests/test_check.py --uhdl dist/component/uhdl-<ver>-linux-x86_64/bin/uhdl --work <dir>
# agent end to end: setup.sh / grade.sh, or run_headless.sh for a real `claude -p` run
bash skill/tests/e2e/run_headless.sh dist/component/uhdl-<ver>-linux-x86_64 <dir> t1 t1-run
bash skill/tests/e2e/grade.sh <dir>/t1-run t1 dist/component/uhdl-<ver>-linux-x86_64
```
`e2e/t1` (round-robin arbiter) and `e2e/t2` (filter around an imported SV FIFO) have hidden testbenches,
each checked against a reference and a mutant.
