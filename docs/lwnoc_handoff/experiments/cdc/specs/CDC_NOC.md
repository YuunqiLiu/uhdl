# cdc_noc: the topology NoC with endpoints in their own clock domains

Build `cdc_noc`. It wraps the provided NoC core `topo_core` (the `topo_noc` of `/workspace/lwnoc_dev/exp/flex/specs/TOPO.md`, which runs on one clock). In `cdc_noc`, each endpoint may live in a different clock domain, and the design adds per-endpoint statistics and an error summary.

## Configuration
```json
{"topo": {...a TOPO.md topology: PW, D, R, links, endpoints...},
 "domains": 2, "ep_domain": [1, 1, 2, 0, ...], "afifo_depth": 4, "cnt_w": 16}
```
- `domains` = K, the number of endpoint clock domains. They are numbered 1..K. Domain 0 is the NoC clock.
- `ep_domain[e]` is the clock domain of endpoint e (0..K).
- `afifo_depth` is the depth of every clock-crossing FIFO (a power of 2).
- `cnt_w` = CW is the statistics counter width.
- Let E be the number of endpoints, `TW = max(1, ceil(log2(E)))`, and `PW = topo.PW`.
- Examples: `specs/cdc_A.json` and `specs/cdc_B.json`. Grading also uses other configurations of the same form. All topologies used are trees.

## Ports
Every reset is active low, asynchronous, and already synchronized to its own clock.

| Port | Dir | Width | Clock domain |
|---|---|---|---|
| `clk_noc`, `rst_noc_n` | in | 1 | NoC |
| `clk_d<k>`, `rst_d<k>_n`, for k = 1..K | in | 1 | domain k |
| `ep<e>_in_vld`, `ep<e>_in_last` | in | 1 | domain of endpoint e |
| `ep<e>_in_rdy` | out | 1 | domain of e |
| `ep<e>_in_dst` | in | TW | domain of e |
| `ep<e>_in_data` | in | PW | domain of e |
| `ep<e>_out_vld`, `ep<e>_out_last` | out | 1 | domain of e |
| `ep<e>_out_rdy` | in | 1 | domain of e |
| `ep<e>_out_dst` | out | TW | domain of e |
| `ep<e>_out_data` | out | PW | domain of e |
| `ep<e>_err` | in | 1 | domain of e |
| `st_addr` | in | TW | NoC |
| `st_data` | out | CW | NoC |
| `noc_err` | out | 1 | NoC |

Port e here means `<e>` written in decimal: `ep0_in_vld`, `ep11_out_data`, and so on.

## Behaviour
- **Data path.** Each endpoint's flit stream reaches the core's port for that endpoint, and the core's output stream reaches the endpoint. Valid/ready semantics are the same as in TOPO.md.
  - Endpoints in domain 0 connect to the core directly.
  - Endpoints in other domains go through a clock-crossing FIFO of depth `afifo_depth` in each direction. A flit is `{last, dst, data}`.
  - Every flit that is injected must be delivered once, in order per (source, destination), with `last`, `dst` and `data` intact.
- **Statistics.**
  - For each endpoint e there is a CW-bit counter in e's own domain. It starts at 0 after reset and increments, modulo 2^CW, on every `ep<e>_out` handshake (`out_vld && out_rdy`).
  - `st_data` shows the counter of endpoint `st_addr` (0 if `st_addr` >= E).
  - It may lag the counter, but it must only ever show values the counter actually had, in order.
  - Once the counter has stopped changing, `st_data` must show its final value within 64 NoC cycles, after `st_addr` has been stable for 4 NoC cycles.
- **Error summary.** `noc_err` is the OR of all `ep<e>_err` inputs as seen in the NoC domain. When that OR has been stable for 32 NoC cycles plus 8 cycles of the slowest endpoint clock, `noc_err` must equal it.
- Use the provided `topo_core` for the network, clocked by `clk_noc`/`rst_noc_n`, unchanged.

## Clock-domain crossing policy (checked structurally, in addition to simulation)
- Every signal that goes from one clock domain to another must pass through one of the provided CDC cells:
  - a **1-bit synchronizer**, for a single-bit signal. Its input must come directly from a register or an input port of the source domain, with no logic in between.
  - a **bus synchronizer**, for a multi-bit value such as a counter.
  - an **asynchronous FIFO**, for a stream.
- Several signals from the same source domain must not each go through their own 1-bit synchronizer and then be combined in the destination domain (reconvergence). Signals that belong together cross as one value, or are combined in the source domain before a single synchronizer.
- No other crossing is allowed, combinational or registered, in either direction.

## Provided library (`/workspace/lwnoc_dev/exp/cdc/lib/`)
| | SystemVerilog flow | UHDL flow |
|---|---|---|
| NoC core | `topo_core_gen.emit(topo_cfg, out_dir)` writes Verilog for module `topo_core` | `topo_core.topo_core(topo_cfg)` returns the Component |
| CDC cells | `cdc_cells.sv`: `cdc_sync`, `cdc_bus #(W)`, `async_fifo #(W, D)` | `CdcSync()`, `CdcBus(W)`, `AsyncFifo(W, D)` from `uhdl` |

The CDC cells of both flows have the same ports and behaviour. See the comments in `cdc_cells.sv` and the UHDL guide.
