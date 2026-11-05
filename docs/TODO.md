# UHDL TODO

Expressiveness work that builds on the core features (structs, streams, bulk connection,
implicit clocks, multi-signal `when` blocks). Both items below are libraries on top of the core;
they need no language change beyond what is noted.

## 4. Standard library of components and combinators

Plain Python functions that return circuits, tested and documented in `docs/LLM_GUIDE.md` as
the one recommended way. Agents in the experiments (`lwnoc_dev/exp`) rewrote these by hand
again and again.

- `rr_arbiter(reqs, lock=None)`: round-robin grant over a list of 1-bit requests, with an
  optional packet lock (hold the grant until `last`). D1 agents wrote one priority chain per
  pointer value to get this.
- `s.counter(name, wrap=D, inc=..., dec=...)`: a counter or pointer with modulo-D wrap for any D,
  not only powers of 2.
- `RegBank(bus, regs)`: a register file from a table of `Reg(name, access, reset)` entries
  (RW / RO / W1C ...) with an AXI-Lite or APB front end. D2 (`axil_regs`) was the most
  expensive design in every round.
- Stream combinators on `Stream` objects: `.fifo(depth)`, `.pipe(n)` (register slice),
  `.skid()`, `.map(f)`, `.filter(pred)`, `.mux(sel, streams)` / `.demux(sel, n)`, `.arbitrate()`.
- Reduction helpers: `reduce_tree(op, xs)`, `onehot(x)`, `encode(onehot)`, `popcount(x)`.

Needs from the core: `Stream` and `Struct` (item 1); implicit clocks (item 2) so library parts pick
up the current domain.

## 5. Automatic clock-domain crossing: `s.cross(x, to=clk)`

Pick the CDC cell from the type of `x` and insert it:

- a 1-bit level → `CdcSync`;
- a multi-bit value (`UInt(w)`, `Struct`) → `CdcBus`;
- a `Stream` → `AsyncFifo` (depth given or a default).

The source domain comes from the design graph, so the call only names the destination.
Every agent in the CDC experiment (`exp/cdc`) wrote this same pattern by hand. The inserted
cells are ordinary CDC cells, so `check_cdc()` still verifies the result.

Needs from the core:

- type information (item 1);
- a public `domain_of(signal)` query. `check_cdc` already computes it internally.
