# UHDL toolkit component and Skill

`skill/uhdl/` is the agent Skill. `packaging/build_component.py` builds a toolkit component around it:
a frozen `uhdl` command that brings its own Python, UHDL and pyslang.

## Build

```bash
python packaging/build_component.py --python /path/to/python3.13 [--out dist/component]
```
Result: `dist/component/uhdl-<version>-linux-x86_64/` and the same as a `.tar.gz`:

| Path | |
|---|---|
| `bin/uhdl` | frozen entry point (PyInstaller onedir) |
| `bin/_uhdl/` | its runtime: Python with the full standard library, uhdl, pyslang; `pysrc/` (uhdl as plain source) and `wheels/` (pyslang for Python 3.8–3.15) |
| `skills/uhdl/uhdl/` | `SKILL.md`, `references/guide.md` (from `docs/LLM_GUIDE.md`), `references/example_gen.py` (from `docs/llm_example/gen.py`) |
| `manifest.json` | version, source commit, SHA-256 of the binary, runtime tree and Skill tree, build Python/pyslang/glibc |

About 100 MB unpacked. Building needs PyPI; the result runs offline. Keep all of `bin/`.

**glibc:** the frozen Python needs the build machine's glibc or newer. PyPI's pyslang needs glibc
2.27+. A build for the toolkit's glibc 2.17 baseline waits for a pyslang built on that baseline
(NexEvic/motryx-toolkit#15).

## The `uhdl` command

| Command | |
|---|---|
| `uhdl run gen.py ARGS` | run a generator with the bundled Python |
| `uhdl check OUT --top T [--sv F]` | Verilator `-Wall` lint + Yosys synth/`check -assert`, messages mapped to Python lines |
| `uhdl python [-c/-m/FILE]` | the bundled Python (interactive without arguments) |
| `uhdl pythonpath --python PY` | PYTHONPATH that lets another Python 3.8+ import this UHDL, adding a bundled pyslang for its version if it has none. For generators that also need the user's own libraries. |
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
