---
name: uhdl-design
description: Design hardware in Python with UHDL and generate Verilog from it. Use when asked to write, modify or check an RTL module or design in UHDL (or "in Python" for hardware), to generate Verilog from UHDL code, to wrap existing SystemVerilog modules in a UHDL design, or when working in code that uses UHDL (`from uhdl import *`, `Component`, `circuit(s)`).
---

# UHDL

UHDL is a Python library for describing hardware. A design is a Python script that builds a circuit; `generate()` writes Verilog-2001. The `uhdl` command runs such scripts with its own bundled Python and UHDL (including SystemVerilog import), so nothing has to be installed.

## 1. Find the command

```bash
uhdl version            # e.g. "uhdl 0.9.0 (frozen, Python 3.13.11 x86_64, uhdl_slang 1 (slang 10.0))"
```
If `uhdl` is not on PATH, use `<this skill dir>/../../../bin/uhdl` (the toolkit's `bin/`). Keep the whole `bin/` directory; `bin/uhdl` needs its sibling `bin/_uhdl/`.

**Which Python runs the generator:**
- **Default: `uhdl run gen.py ...`.** The bundled Python is there to run UHDL: it has the standard library (without `ssl`, so no network) and UHDL, and no third-party packages.
- **When the generator also needs packages from the user's own Python** (numpy, a project library, ...), run it in that Python and give it UHDL through PYTHONPATH:
  ```bash
  PYTHONPATH=$(uhdl pythonpath --python python3)${PYTHONPATH:+:$PYTHONPATH} python3 gen.py --out out
  ```
  This works with any Python 3.8+, including a venv or conda env. It installs nothing and does not change that environment. SystemVerilog import works there too: it uses a library shipped with UHDL, not a Python package.
- **Projects that pin their own UHDL** (a `uhdl` checkout or submodule imported as `uhdl.uhdl.core`, like lwnoc) keep using it with their own setup. Follow the style of their code; that UHDL may be older than this guide.

## 2. Workflow

1. **Read `references/guide.md` completely before writing UHDL** (once per task). It covers syntax, widths, registers, when-blocks, sub-components, structs and streams, importing SV (section 7b), clocks and CDC. `references/example_gen.py` is a complete, lint-clean example.
2. Write the generator as a script that takes its output directory and parameters on the command line (template below).
3. Generate: `uhdl run gen.py --out out`. A UHDL error starts with `file.py:line: <source line>` of the code that caused it. Fix that line.
4. Check: `uhdl check out --top <top>`. If the design imports SystemVerilog, add `--sv <file>` for each imported source or `.f` filelist, packages first. Do not edit `out/filelist.f`; it lists only what UHDL generated.
   - The check runs Verilator lint (`-Wall`) and a Yosys synthesis check. Each message is mapped back to your Python line through the `// file.py:line` comments that `generate()` writes.
   - Expect `CHECK PASS`. A missing tool shows as `SKIPPED`, and with neither tool installed the result is `CHECK NOT RUN`. Tell the user which steps were skipped; do not call the design lint-clean.
5. If behaviour matters, write a testbench and simulate the generated Verilog: `verilator --binary --timing --top-module tb <imported SV files> tb.sv -f out/filelist.f`. Simulator messages point at generated lines; their trailing comment names the Python line.
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

`uhdl python` opens the bundled Python: `uhdl python -c '...'`, `uhdl python script.py`, or interactive.

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
