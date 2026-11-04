# UHDL guide for LLM agents

This guide is for language models and people writing hardware in UHDL. Everything in it has been run on branch `lwnoc_rewrite`. The complete example is `docs/llm_example/gen.py`: a histogram counter that uses a sub-component, Mem, WrapAdd and Case. The test suite generates it and runs `verilator -Wall` lint on the result.

## 1. Mental model
- A design is a Python object graph, and UHDL turns it into Verilog-2001.
- **Elaboration time is Python.** Loops, tables, `if` and math run in Python and decide the circuit's structure.
- **Run time is hardware.** Only UHDL objects (Input, Wire, Reg, Mem, expressions) become logic.
- A module's parameters are fixed when it is generated. The Verilog it emits has no `parameter`. Generate once for each configuration.
- **Each signal has exactly one driver**, written `sig += expr`. A second `+=` on the same signal is an error.

## 2. Skeleton
```python
from uhdl import *          # Component, Input, Output, Wire, Reg, Mem, UInt, when, Case, ...

def build(N, W):            # parameters come from the closure
    class my_top(Component):
        MODULE_NAME = 'my_top'                 # exact Verilog module name
        def circuit(self):                     # Component.__init__ calls circuit()
            self.clk   = Input(UInt(1))
            self.rst_n = Input(UInt(1))
            ...
    return my_top()

paths = build(4, 8).generate('out_dir')        # out_dir/<module>.v per module + out_dir/filelist.f
```
- Running Python: `PYTHONPATH=<uhdl checkout> python gen.py ...`
- Use `generate(out_dir)`, not `generate_verilog()`. It writes the files flat into out_dir, keeps any existing files there, writes `filelist.f` with absolute paths, and raises an error if two different modules end up with the same name.
- To set the module name at runtime instead, call `comp.set_module_name('name')`.

## 3. Sub-components
```python
class SatInc(Component):
    def __init__(self, W):
        self.W = W                 # set attributes BEFORE super().__init__(), which calls circuit()
        super().__init__()
    def circuit(self):
        self.a = Input(UInt(self.W)); self.y = Output(UInt(self.W)); ...

# inside the parent's circuit():
self.inc = SatInc(6)               # instance name = attribute name ("inc")
self.inc.a += self.cur             # drive the child's input from the parent
self.x     += self.inc.y           # read the child's output
self.create('u_%d' % i, SatInc(6)) # dynamically named instances, e.g. in a loop
```
- If a child class has `__init__` arguments, its module name gets them as a suffix (`SatInc_W_6`). That keeps different configurations apart automatically.
- If two instances of the same configuration produce identical Verilog, `generate()` writes it once.

## 4. Signals and values
| Construct | Meaning |
|---|---|
| `Input(UInt(w))` / `Output(UInt(w))` | Ports. Their order in the module follows the order of assignment in `circuit()`. |
| `Wire(UInt(w))` | Combinational net |
| `Reg(UInt(w, rst), clk, rst_n)` | Flop with asynchronous active-low reset to `rst`. Other options are in the Reg docstring. |
| `Mem(UInt(w), depth, clk)` | `reg [w-1:0] m [0:depth-1]`, no reset. `m.write(en, addr, data)` adds a write port; `m.read(addr)` is a combinational read. |
| `UInt(w, v)` | Constant |
| `self.create(name, obj)` | Attach a signal or instance under a computed name |

## 5. Expressions
- **Widths must match exactly.** Every `+=`, comparison and bitwise operator requires equal widths, and there is no implicit extension. To zero-extend, write `Combine(UInt(k, 0), x)`. To truncate, write `x[h:l]`.
- **Arithmetic:**
  - `a + b` and `a - b` give a result **one bit wider** than the operands.
  - For counters and pointers use `WrapAdd(a, b)` and `WrapSub(a, b)`. They keep the operand width and emit `{(a + b)}`, which produces no lint warnings.
  - `a * b` is also available.
- **Bitwise:** `a & b`, `a | b`, `a ^ b`, `~a`.
- **Logical (1-bit results):** `And(a, b, ...)`, `Or(...)`, `Not(a)`.
- **Comparisons:** `Equal`, `NotEqual`, `Less`, `LessEqual`, `Greater`, `GreaterEqual`. A comparison whose result is constant for the operand width, such as `GreaterEqual(UInt(3,7), p)`, is folded to a constant automatically.
- **Reductions:** `SelfOr(x)` (`|x`), `SelfAnd`, `SelfXor`.
- **Slices:** `x[h:l]` with the high index first, `x[i]`.
- **Concatenation:** `Combine(a, b, c)` gives `{a, b, c}`, so the first argument becomes the MSBs. A single argument is allowed.
- **Muxes:**
  - `when(c1).then(v1).when(c2).then(v2).otherwise(v3)` is a priority mux.
  - `Case(sel, {UInt(k,0): v0, ...}, default)` is a parallel mux. The keys must be UInt values of the same width as `sel`.
  - Either may be used inside other expressions; UHDL creates a helper wire for it.
  - For a when-chain built in a loop, use `ch = EmptyWhen()`, then `ch.when(c).then(v)` repeatedly, then `ch.otherwise(d)`.

## 6. Registers
```python
self.cnt += when(inc).then(WrapAdd(self.cnt, UInt(W, 1))) \
            .when(dec).then(WrapSub(self.cnt, UInt(W, 1)))     # no match -> holds its value
```
- The first condition that is true wins. A register needs no `otherwise`; when nothing matches it keeps its value.

## 7. What UHDL guarantees and what you still own
UHDL raises an error, instead of emitting bad Verilog, for:
- **Width mismatches** in assignments and operators.
- **Multiple drivers** on one signal.
- **Latches:** a combinational when-chain without `otherwise`, or a combinational `Case` with no default that does not cover every select value.
- **Mem misuse:** an address too narrow for the depth, or write data of the wrong width.
- **Name collisions** between different modules in `generate()`.

What you still have to handle:
- **Unused signals** (Verilator UNUSED). Examples are ports required by a spec but not used by your logic, or a carry you drop on purpose. Call `self.mark_unused(sig, ...)`.
- **Undriven outputs.** Every Output and Wire you declare must be driven.
- **Functional correctness.** Write a testbench. UHDL emits plain Verilog, so you can simulate it with `verilator --binary --timing tb.sv -f out/filelist.f`.

## 8. Checking your output
```bash
python gen.py --out out ...
verilator --lint-only -Wall --top-module <top> -f out/filelist.f      # expect no %Warning lines
yosys -q -p "read_verilog $(tr '\n' ' ' < out/filelist.f); synth -top <top>; check -assert"
```
- To look at the Verilog for one component without writing files: `print('\n'.join(comp.verilog_def))`.
- UHDL writes no log file unless you set `UHDL_LOG=<path>`.

## 9. Known limitations
- The output is Verilog-2001. There are no SystemVerilog interfaces in the output, and parameters are not kept, because everything is elaborated.
- Constants are emitted in binary.
- `VComponent` (importing hand-written SV) and `TemplateIP` use their own output handling. `generate()` hands those components to it, and their files are not listed in `filelist.f`.
