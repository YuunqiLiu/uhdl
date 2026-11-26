# UHDL cheat sheet (lwnoc_rewrite @ 77d05c9)

There is a complete, verified example at `specs/cheatsheet_example/gen.py`. It covers the generator skeleton, a counter and the output layout. Copy its structure.

## Running it
`PYTHONPATH=/workspace/lwnoc_dev/uhdl_work /workspace/lwnoc_dev/.venv/bin/python gen.py ...`

## Imports
```python
from uhdl import (Component, Input, Output, Wire, Reg, UInt, Cut, when, EmptyWhen, Case,
                  Combine, Equal, NotEqual, Less, LessEqual, Greater, GreaterEqual,
                  And, Or, Not, BitAnd, BitOr, BitXor, Inverse, SelfOr, SelfAnd, SelfXor)
```

## Component and module name
- **Module name:** if a class takes `__init__` arguments, UHDL appends them to the module name (`foo_N_4`), and there is no way to turn this off.
  - To get an exact module name, define the class inside a factory function, read parameters from the closure, and give the class no `__init__` arguments.
- **Where the body goes:** put the body in `def circuit(self):`. `Component.__init__` calls it.
- **Instance names:** for dynamically named signals use `self.create('name_%d' % i, Wire(UInt(w)))`, or `self.set(name, obj)`.

## Signals
- `Input(UInt(w))`, `Output(UInt(w))`, `Wire(UInt(w))`.
- `Reg(UInt(w, reset_val), self.clk, self.rst_n)`: asynchronous active-low reset to `reset_val`.
- Constants: `UInt(w, value)`. They are emitted as binary.

## Assignment
- `x += expr` drives x. Each signal can have only one driver; a second `+=` is an error.
- **The width must match exactly**, otherwise you get an error. There is no implicit extension or truncation.
- Registers: `reg += when(c1).then(v1).when(c2).then(v2)`. The first true condition wins; if none is true, the register keeps its value (no `otherwise` needed). Combinational logic uses `.otherwise(v)`.
- `EmptyWhen()` starts a when-chain you build in a loop: `ch = EmptyWhen(); ch.when(c).then(v); ... ch.otherwise(d)`.
- `Case(sel, {UInt(k,0): v0, UInt(k,1): v1, ...}, default)` builds a parallel mux. The keys must be UInt values with the same width as sel.

## Operators
- `a + b`, `a - b`: **the result is 1 bit wider**. Use Cut to truncate (see the pitfalls below).
- `a & b`, `a | b`, `a ^ b`, `~a` are bitwise. `And/Or/Not` are logical, with 1-bit results.
- Comparisons go through functions: `Equal(a,b)`, `NotEqual`, `Less`, `GreaterEqual`, ... Both sides must have the same width.
- Reductions: `SelfOr(x)` is `|x`, also `SelfAnd`, `SelfXor`.
- Slices: `x[h:l]` (**high bit first**), `x[i]`. `Cut(x, h, l)` does the same.
- Concatenation: `Combine(a, b, c)` gives `{a, b, c}`, so a ends up in the **high bits**.

## Generating output
`generate_verilog()` writes into `<output_dir>/<module>/` and wipes that directory first. The example's approach:
1. Set `top.output_dir` to a temporary directory.
2. Call `generate_verilog(iteration=True)`.
3. Move the `.v` files out of `top.output_path` into `<out>`.
4. Write `filelist.f` yourself.

## Known pitfalls
1. **Bug ([issue #17](https://github.com/YuunqiLiu/uhdl/issues/17)):** if the same Reg's when-chain has several branches that use `Cut(expr)` on expressions of the same width, they all wrongly share one temporary wire. The generated logic is wrong and no error is reported.
   - Avoid it: compute each arithmetic result in its own named Wire, Cut it into another Wire, and use only those Wires in the when-chain. The example does this.
2. Comparisons with constants are emitted exactly as written. For example, if `ptr` can only be 0..7, `UInt(3,7) >= ptr` triggers Verilator CMPCONST. Simplify comparisons whose result is constant yourself.
3. UHDL cannot emit lint pragmas. For signals that are unused, such as the carry bit after truncation, put them into a wire with `unused` in its name. Verilator does not report UNUSED for those by default.
4. There is no memory/array primitive. A register array has to be built with `self.create('mem_%d'%i, Reg(...))`, and reads use `Case` muxing.
5. UHDL writes `UHDL.log` into the current working directory, so delete it or ignore it.
