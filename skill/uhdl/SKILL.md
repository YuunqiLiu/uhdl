---
name: uhdl
description: Design hardware in Python with UHDL and generate Verilog from it. Use when asked to write, modify or check an RTL module or design in UHDL (or "in Python" for hardware), to generate Verilog from UHDL code, to wrap existing SystemVerilog modules in a UHDL design, or when working in code that uses UHDL (`from uhdl import *`, `Component`, `circuit(s)`).
---

# UHDL

UHDL is a Python library for describing hardware. A design is Python code that builds a circuit; `generate()` writes Verilog-2001. This skill brings its own UHDL and pyslang wheels (Python 3.8-3.15; see `wheels/PLATFORMS` for the operating systems), so it works offline.

## 1. Set up Python (once per machine)

```bash
PY=$(bash <this skill dir>/scripts/uhdl_env.sh)    # prints a python that has UHDL; messages go to stderr
"$PY" -c "import uhdl"                            # works
```
- The script picks a Python ≥3.8 from PATH (`UHDL_PYTHON=/path/to/python` to choose one). It creates a virtual environment in `~/.cache/uhdl-skill/` (`UHDL_VENV=<dir>` to place it elsewhere) and installs from the bundled `wheels/` with no network. Running it again is fast and prints the same path.
- If the bundle has no pyslang wheel for this Python or platform, it installs UHDL without SV import and says so. In that case section 7b of the guide (VComponent, `import_sv_package`) is unavailable; `UHDL_ALLOW_NETWORK=1` lets pip fetch pyslang from PyPI.
- Use `"$PY"` for every command below. Do not `pip install` UHDL some other way, and do not edit the venv.
- **Existing projects that pin their own UHDL** (a `uhdl` checkout or submodule imported as `uhdl.uhdl.core`, like lwnoc) run with their own setup. Follow the style of their code: that UHDL may be older than this guide and may lack the compact syntax.

## 2. Workflow

1. **Read `references/guide.md` completely before writing UHDL** (once per task). It is the reference for syntax, widths, registers, when-blocks, sub-components, structs and streams, importing SV, clocks and CDC. `references/example_gen.py` is a complete, lint-clean example.
2. Write the generator as a script that takes its output directory and parameters on the command line (template below).
3. Generate: `"$PY" gen.py --out out`. UHDL errors start with `file.py:line: <source line>` of the code that caused them. Fix that line.
4. Check: `"$PY" <this skill dir>/scripts/uhdl_check.py out --top <top>` (add `--sv <file>` for each imported SV source or `.f` filelist). It runs Verilator lint (`-Wall`) and, for pure-Verilog designs, a Yosys synthesis check. Each message is mapped back to your Python line through the `// file.py:line` comments that `generate()` writes. Expect `CHECK PASS`. A missing tool shows as `SKIPPED`, and with neither tool installed the result is `CHECK NOT RUN`. Tell the user which steps were skipped; do not call the design lint-clean.
5. If behaviour matters, write a testbench and simulate the generated Verilog: `verilator --binary --timing --top-module tb tb.sv -f out/filelist.f`. Simulator messages point at generated lines; their trailing comment names the Python line.
6. Tell the user what you generated, where, and what you checked (lint, synthesis, simulation), including anything that was skipped.

```python
#!/usr/bin/env python3
import argparse
from uhdl import *

def build(W):
    class my_top(Component):
        MODULE_NAME = 'my_top'
        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.domain(s.clk, s.rst_n)
            s.din, s.dout = Input(W), Output(W)
            r = s.reg('r', W)
            r += s.din
            s.dout += r
    return my_top()

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--width', type=int, default=8)
    a = ap.parse_args()
    for p in build(a.width).generate(a.out):
        print(p)
```

## 3. Mistakes to avoid

These are the errors seen most often. The guide explains each one.
- **Widths must match exactly.** There is no implicit extension. Zero-extend with `Cat(x, UInt(k, 0))`, truncate with `x[h:l]`. `a + b` is one bit wider; use `WrapAdd`/`WrapSub` for counters.
- **Compare with methods.** Use `a.eq(b)`, `.ne`, `.lt`, `.le`, `.gt`, `.ge`. `==` and `<` are not hardware operators.
- **Concatenation order:** `Cat(a, b)` is LSB first (`a` in the low bits); `Combine(a, b)` is MSB first, like Verilog `{a, b}`.
- **One driver per signal.** Drive with `+=` once, or only with `<<=` inside `with s.when(...)` blocks. A wire or output driven in blocks needs a default (`o <<= 0`) first, outside the blocks.
- **Children:** set attributes before `super().__init__()` (which calls `circuit()`). Unconnected `clk`/`rst_n` follow `s.domain(...)`.
- **Unused inputs or bits** cause Verilator UNUSED warnings. Call `s.mark_unused(sig, ...)`. Every Output must be driven.
- **Imported SV with struct ports:** pass `struct_mode='packed'` to `VComponent`.
- **Clock crossings** need `CdcSync`, `CdcBus` or `AsyncFifo`. `generate()` rejects any other crossing.
- **Parameters are elaborated.** The Verilog has no `parameter`; generate once per configuration.
