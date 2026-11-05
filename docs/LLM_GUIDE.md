# UHDL guide for LLM agents

This guide is for language models and people writing hardware in UHDL. Everything in it has been run on branch `lwnoc_rewrite`. The complete example is `docs/llm_example/gen.py`: a histogram counter that uses a sub-component, Mem, Mux, If and Cat. The test suite generates it and runs `verilator -Wall` lint on the result.

Write new code in the compact style shown here. The older long form (`Wire(UInt(8))` plus `self.create(...)`, `UInt(w, v)` for every constant, `Equal(a, b)`) still works and is what existing lwnoc code uses, but do not mix the two in one file.

## 1. Mental model
- A design is a Python object graph, and UHDL turns it into Verilog-2001.
- **Elaboration time is Python.** Loops, lists, `if` and math run in Python and decide the circuit's structure.
- **Run time is hardware.** Only UHDL objects (Input, wire, reg, mem, expressions) become logic.
- A module's parameters are fixed when it is generated; the Verilog has no `parameter`. Generate once per configuration.
- **Each signal has exactly one driver**, written `sig += expr`. A second `+=` on the same signal is an error.

## 2. Skeleton
```python
from uhdl import *

def build(N, W):                       # parameters come from the closure
    class my_top(Component):
        MODULE_NAME = 'my_top'         # exact Verilog module name
        def circuit(s):                # Component.__init__ calls circuit(); `s` is just a short `self`
            s.clk, s.rst_n = Input(1), Input(1)
            s.din, s.dout = Input(N * W), Output(W)
            s.domain(s.clk, s.rst_n)   # default clock and async active-low reset for s.reg / s.mem
            ...
    return my_top()

paths = build(4, 8).generate('out_dir')   # out_dir/<module>.v per module + out_dir/filelist.f
```
- Run as `PYTHONPATH=<uhdl checkout> python gen.py ...`.
- Use `generate(out_dir)`. It writes the files flat into out_dir, keeps other files there, writes `filelist.f` with absolute paths, and raises an error if two different modules get the same name.
- `comp.set_module_name('name')` sets the module name at runtime instead of `MODULE_NAME`.

## 3. Declarations
| Write | Meaning |
|---|---|
| `s.a = Input(8)`, `s.y = Output(8)` | Ports, in assignment order. `Input(8)` is short for `Input(UInt(8))`. |
| `x = s.wire('x', expr)` | Declare a wire named `x`, drive it with `expr`. **The width comes from `expr`.** |
| `x = s.wire('x', Mux(sel, [1, 2, 3]), width=2)` | `width=` is needed only when every value is a plain int. `Mux(sel, [1, 2, 3], width=2)` works too. |
| `r = s.reg('cnt', 4)` / `s.reg('cnt', 4, init=5)` | Flop on the default domain, reset to `init` (default 0). Drive it with `r += ...`. |
| `m = s.mem('ram', 8, 16)` | `reg [7:0] ram [0:15]`, no reset. `m.write(en, addr, data)` adds a write port; `m[addr]` is a combinational read. |
| `s.domain(clk, rst, async_rst=False)` | Change the default domain (or its reset style) for the declarations that follow. `s.reg(..., clk=other)` uses another clock. |

- Names are what you see in the Verilog. Build per-index names with f-strings: `s.wire(f'req_{o}_{i}', ...)`.
- Keep the returned objects in Python lists (`cnt = [s.reg(f'cnt_{i}', 4) for i in range(N)]`); you do not need to read them back through `s`.

## 4. Values and widths
- **Signals must match widths exactly.** There is no implicit extension or truncation between signals. Zero-extend with `Cat(x, UInt(k, 0))`; truncate with `x[h:l]`.
- **Plain Python ints take the width of the signal they meet**: `cnt.eq(3)`, `ptr.lt(D)`, `WrapAdd(p, 1)`, `.then(0)`, `r += 0`, `m.write(we, 2, 7)`. The int must fit in that width, or UHDL raises an error. It is never truncated. Negative ints are rejected.
- An int needs a signal next to it: `Equal(1, 2)` is an error. For a sized constant on its own, write `UInt(w, v)`.

## 5. Expressions
| Write | Verilog |
|---|---|
| `a & b`, `a \| b`, `a ^ b`, `~a` | Bitwise. On 1-bit signals these are the logical and/or/not. |
| `a.eq(b)`, `.ne`, `.lt`, `.le`, `.gt`, `.ge` | Comparisons, 1-bit result. The `==`/`<` operators are **not** overloaded; always use these methods. |
| `WrapAdd(a, b)`, `WrapSub(a, b)` | `a + b` / `a - b` keeping the operand width (counters, pointers). |
| `a + b`, `a - b` | One bit wider than the operands. |
| `And(a, b, ...)`, `Or(*lst)`, `Not(a)` | Logical reductions of several 1-bit values. |
| `SelfOr(x)`, `SelfAnd(x)`, `SelfXor(x)` | `\|x`, `&x`, `^x`. |
| `x[h:l]`, `x[i]` | Slices, high index first. |
| `x.split(n)` | List of n equal fields, LSB field first: `s.in_data.split(N)[i]` is `in_data[i*W +: W]`. |
| `Cat(lst)` or `Cat(a, b, c)` | Concatenate **LSB first**: item 0 lands in the low bits. `Cat(lst)` is the inverse of `split`. |
| `Combine(a, b, c)` | `{a, b, c}`, MSB first (Verilog order). Use it for packing fields, e.g. `Combine(tgt, data, last)`. |
| `If(c, a, b)` | `c ? a : b`. |
| `Mux(sel, lst)` | `lst[sel]`. Values may be signals or ints. Select values past the end of the list give 0. |
| `Priority([(c0, v0), (c1, v1)], d)` | First true condition wins, else `d`. Good for chains built in loops. |
| `when(c0).then(v0).when(c1).then(v1).otherwise(d)` | Same as Priority, written inline. |
| `Case(sel, {0: v0, 1: v1}, default)` | Parallel case with explicit keys; keys may be ints. |

Any of these may be nested inside others; UHDL creates helper wires where Verilog needs them.

## 6. Registers
```python
cnt = s.reg('cnt', CW)
cnt += when(push & ~pop).then(WrapAdd(cnt, 1)) \
       .when(pop & ~push).then(WrapSub(cnt, 1))      # no match -> holds its value
ptr += when(adv).then(If(ptr.eq(D - 1), 0, WrapAdd(ptr, 1)))   # wrap at D, any D
```
- The first true condition wins. A register needs no `otherwise`; when nothing matches it keeps its value.

## 7. Sub-components
```python
class SatInc(Component):
    def __init__(self, W):
        self.W = W                 # set attributes BEFORE super().__init__(), which calls circuit()
        super().__init__()
    def circuit(s):
        s.a, s.y = Input(s.W), Output(s.W)
        s.y += If(SelfAnd(s.a), s.a, WrapAdd(s.a, 1))

# inside the parent's circuit():
s.inc = SatInc(6)                  # instance name = attribute name ("inc")
s.inc.a += cur                     # drive the child's input
nxt = s.wire('nxt', s.inc.y)       # read the child's output
s.create(f'u_{i}', SatInc(6))      # computed instance names, e.g. in a loop
```
- A child class with `__init__` arguments gets them as a module-name suffix (`SatInc_W_6`), so different configurations stay apart. Identical instances are written once.

## 8. Several clocks
- Every `s.reg` / `s.mem` belongs to the clock it was declared with (`s.domain(clk, rst)` or `clk=`). Call `s.domain(...)` again to switch.
- Give top-level ports their clock: `s.din = Input(8, domain=s.clk_a)`, `s.q = Output(1, domain=s.clk_b)`. Unannotated ports are not checked.
- A signal may cross from one clock domain to another only through a CDC cell:

| Cell | Use for | Ports |
|---|---|---|
| `CdcSync()` | one bit (a level, a flag) | `clk`, `rst_n` (destination), `d`, `q` |
| `CdcBus(W)` | a multi-bit value that changes now and then (a counter, a status word). `dst_data` is always a value `src_data` had. | `src_clk`, `src_rst_n`, `src_data`, `dst_clk`, `dst_rst_n`, `dst_data` |
| `AsyncFifo(W, D)` | a stream; D a power of 2 | `wclk`, `wrst_n`, `w_vld`, `w_rdy`, `w_data`, `rclk`, `rrst_n`, `r_vld`, `r_rdy`, `r_data` |

```python
s.sync = CdcSync(); s.sync.clk += s.clk_b; s.sync.rst_n += s.rstb_n
s.sync.d += flag_a                 # flag_a: a reg (or port) of clock a, no logic in between
s.bus = CdcBus(16)
s.bus.src_clk += s.clk_a; s.bus.src_rst_n += s.rsta_n; s.bus.src_data += cnt_a
s.bus.dst_clk += s.clk_b; s.bus.dst_rst_n += s.rstb_n
cnt_in_b = s.bus.dst_data
```
- `generate()` runs `check_cdc()` and raises an error for:
  - a crossing outside these cells;
  - logic in front of a `CdcSync`;
  - two `CdcSync` from the same source domain whose outputs meet in one destination register (reconvergence). Combine such bits in the source domain first and sync once, or send them as one value with `CdcBus`.
- `comp.check_cdc()` returns the same list without generating.

## 9. What UHDL guarantees and what you still own
UHDL raises an error, instead of emitting bad Verilog, for:
- **Width mismatches** between signals, and ints that do not fit.
- **Multiple drivers** on one signal.
- **Latches:** a combinational when-chain without `otherwise`, or a combinational `Case` that has no default and does not cover every select value. (`Mux` and `If` always cover every case.)
- **Mem misuse:** an address too narrow for the depth, or write data of the wrong width.
- **Name collisions:** `s.wire`/`s.reg`/`s.mem` with a name already used in the component or a Verilog/SV keyword, and two different modules with one name in `generate()`.
- **Clock-domain crossings** outside the CDC cells (section 8).

What you still have to handle:
- **Unused signals** (Verilator UNUSED): ports required by a spec but not used, bits you drop on purpose. Call `s.mark_unused(sig, ...)`.
- **Undriven outputs.** Every Output you declare must be driven.
- **Functional correctness.** Write a testbench. UHDL emits plain Verilog, so you can simulate it with `verilator --binary --timing tb.sv -f out/filelist.f`.

## 10. Checking your output
```bash
python gen.py --out out ...
verilator --lint-only -Wall --top-module <top> -f out/filelist.f      # expect no %Warning lines
yosys -q -p "read_verilog $(tr '\n' ' ' < out/filelist.f); synth -top <top>; check -assert"
```
- To look at one component's Verilog without writing files: `print('\n'.join(comp.verilog_def))`.
- UHDL writes no log file unless you set `UHDL_LOG=<path>`.

## 11. Known limitations
- The output is Verilog-2001, with no SystemVerilog interfaces. Parameters are not kept, because everything is elaborated.
- Constants are emitted in binary.
- `VComponent` (importing hand-written SV) and `TemplateIP` use their own output handling. `generate()` hands those components to it, and their files are not listed in `filelist.f`.
