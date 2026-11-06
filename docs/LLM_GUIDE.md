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
- Run with a Python that has UHDL: `pip install "uhdl[sv]"` (Python 3.8+; `[sv]` adds pyslang for section 7b), or `PYTHONPATH=<uhdl checkout> python gen.py ...`.
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

### Control logic: when-blocks and state machines
**Rule: when one condition (or one state) decides the next value of two or more signals, write it as a when-block.** Keep `cnt += when(...)...` chains for a signal that is decided on its own. Blocks keep one decision in one place instead of repeating its condition in every signal's chain.

```python
# a request/response handshake: one event updates several registers
with s.when(req_vld & ~busy):         # accept
    busy <<= 1
    tag  <<= req_tag
    data <<= req_data
with s.when(rsp_vld & rsp_rdy):       # complete
    busy <<= 0
```
Inside blocks, assign with `<<=`. State machines use the same blocks:
```python
st = s.fsm('st', ['IDLE', 'WAIT', 'RESP'])       # state reg in the current domain, resets to IDLE
with st.state('IDLE'):
    with s.when(req):
        st.goto('WAIT')
        addr <<= req_addr
        busy <<= 1
with st.state('RESP'):
    with s.when(ack):
        st.goto('IDLE')
        busy <<= 0
with s.when(err):
    busy <<= 0                                   # a later assignment wins over an earlier one
```
- `with s.when(c):`, `with s.elsewhen(c):`, `with s.otherwise():` nest freely. `fsm.is_('WAIT')` is the 1-bit "in state" test.
- A register that no block assigns keeps its value. A wire or output assigned in blocks needs a default first, written outside the blocks (`o <<= 0`). Without one, UHDL raises an error, because the result would be a latch.
- A signal is driven either with `+=` or with `<<=`, not both.

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
- **Clock and reset follow you.** A child's `clk` / `rst_n` inputs that you leave unconnected are connected to the `s.domain(...)` that was active when you attached the child. To use another clock, connect both `clk` and `rst_n` yourself. Connecting only one of them is an error.

## 7a. Structs, streams and partial assignment
```python
Flit = Struct(last=1, dst=TW, data=PW)           # first field = top bits; Flit.width
v = s.wire('v', Flit.pack(last=1, dst=d, data=x))
Flit(v).dst                                      # a field of any Flit-wide signal or expression

src = s.stream_in('ep0_in', Flit, domain=clk)    # ports ep0_in_vld, ep0_in_rdy (output), ep0_in_last, ep0_in_dst, ep0_in_data
dst = s.stream_out('ep0_out', Flit, domain=clk)
dst += src                                       # vld and payload forward, rdy back
src.fire                                         # vld & rdy
src.field('dst')                                 # one payload field

lane = Stream.of(s.core, 'l_in', Flit, lane=e)   # lane e of a child's flat vectors l_in_vld[E], l_in_dst[E*TW], ...
lane += src

s.bus[7:4] += hi                                 # drive part of a signal; all parts together must cover
s.bus[3:0] += lo                                 # every bit exactly once
```
- `Stream.of(comp, prefix, payload)` uses ports `<prefix>_vld`, `<prefix>_rdy`, and either one `<prefix>_<field>` per Struct field or `<prefix>_data`.
- `s.input(name, w, domain=)` and `s.output(name, w, domain=)` declare ports with computed names, e.g. `s.input(f'clk_d{k}', 1)`.

## 7b. Importing SystemVerilog
Existing SV modules become sub-components with `VComponent`; their ports and parameters are read with pyslang.
```python
pk = import_sv_package(['rtl/my_pkg.sv'], 'my_pkg')   # packed structs -> Struct, int localparams -> ints
Req = pk.req_t                                         # Req.width, Req.fields, Req(sig).addr, Req.pack(...)
N = pk.N_ENT

s.u_fifo = VComponent(file='rtl/pkg.sv rtl/fifo.sv', top='sync_fifo',      # several files: one string
                      slang_opts='--ignore-unknown-modules --single-unit',   # --single-unit: files share macros
                      struct_mode='packed',                                  # struct ports as plain vectors
                      WIDTH=Req.width, DEPTH=8,                              # module parameters
                      T=SvType('my_pkg::req_t'))                             # a `parameter type`
s.u_fifo.in_data += req                                # ports are ordinary UHDL ports
```
- **Pass `struct_mode='packed'`** when the module has struct-typed ports. They then become plain vectors of the struct's width, which you read with `Req(sig).field`. Without it, they become struct port groups that cannot be connected to plain signals. A `parameter type` given as `SvType` is always packed.
- A port of unpacked-array type (`logic [W-1:0] d [N]`) becomes one flat vector, element 0 in the low bits. `generate()` writes a small `<top>__uflat_<hash>.sv` wrapper for it and lists it in `filelist.f`.
- `generate()` does not copy or list the imported SV files. Give them to the simulator yourself, together with `filelist.f`.
- Clock and reset ports named `clk` / `rst_n` follow `s.domain(...)` like any child (section 7).
- If a port type cannot be resolved (missing package, wrong `top`), UHDL raises an error instead of guessing a width.

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
s.domain(s.clk_b, s.rstb_n)
s.sync = CdcSync()                                     # clk/rst_n follow the current domain (b)
s.sync.d += flag_a                                     # flag_a: a reg (or port) of clock a, no logic in between
s.bus = CdcBus(16, src=(s.clk_a, s.rsta_n), dst=(s.clk_b, s.rstb_n))
s.bus.src_data += cnt_a
cnt_in_b = s.bus.dst_data
s.f = AsyncFifo(Flit, 4, w=(s.clk_a, s.rsta_n), r=(s.clk_b, s.rstb_n))
s.f.w += src_a                                         # .w and .r are Streams
dst_b += s.f.r
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
- **Partial drivers** that leave bits undriven or drive a bit twice, a `clk`/`rst_n` pair connected only halfway, and a combinational signal assigned only inside when-blocks.

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
- **Finding the Python line.** A UHDL error starts with `file.py:line: <source>` of the code that caused it. Checks that run after `circuit()` (latch, slice coverage, CDC, two drivers) name the lines that were recorded, e.g. `first driver: gen.py:40: s.y += s.a`. In the files written by `generate()`, the first line of each assign, always block, instance and instance port ends with `// gen.py:42` (several lines for a when-chain: `// gen.py:48,56`). So for a simulator or lint message on generated Verilog, read the comment on that line. `generate(..., src_comments=False)` leaves the comments out. `verilog_def` never has them.

## 11. Known limitations
- The output is Verilog-2001, with no SystemVerilog interfaces. Parameters are not kept, because everything is elaborated.
- Constants are emitted in binary.
- `VComponent` (importing hand-written SV), and `TemplateComponent` from ip_builder (`ip_builder/uhdl_template_ip.py`), use their own output handling. `generate()` hands those components to it, and their files are not listed in `filelist.f`.
