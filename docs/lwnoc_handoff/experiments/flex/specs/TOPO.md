# topo_noc: a network-on-chip with an arbitrary topology

Build `topo_noc`, a NoC whose topology comes from a configuration: an arbitrary undirected graph of routers, with endpoints attached to routers. Routing tables are computed from the graph.

## Configuration
```json
{"PW": 32, "D": 4, "R": 7,
 "links": [[0, 1], [0, 2], ...],
 "endpoints": [3, 3, 4, ...]}
```
- `PW` is the payload width, `D` the FIFO depth of every router input, and `R` the number of routers (ids 0..R-1).
- `links` are bidirectional router-to-router links. There is at most one link per router pair, and no self links. The graph is connected.
- `endpoints[e]` is the router that endpoint `e` attaches to (endpoint ids 0..E-1, where E = len(endpoints)). A router may have zero, one or several endpoints.
- `TW = max(1, ceil(log2(E)))` is the width of an endpoint id.
- Every router has at least 2 ports.
- Examples: `specs/topo_A.json` (a tree) and `specs/topo_B.json` (a graph with cycles). Grading also uses other configurations of the same form.

## Top-level ports
Clock `clk`, asynchronous active-low reset `rst_n`. For endpoint e, each flat vector uses bits `[e*w +: w]`:

| Port | Dir | Width per endpoint |
|---|---|---|
| `l_in_vld`, `l_in_last` | in | 1 |
| `l_in_rdy` | out | 1 |
| `l_in_dst` | in | TW (destination endpoint id) |
| `l_in_data` | in | PW |
| `l_out_vld`, `l_out_last` | out | 1 |
| `l_out_rdy` | in | 1 |
| `l_out_dst` | out | TW |
| `l_out_data` | out | PW |

## Structure (cycle-exact; grading compares against a reference cycle by cycle)
- **Routers.** Each router r is one instance of the provided switch `noc_sw` (D1 in `/workspace/lwnoc_dev/exp/sv_vs_uhdl/specs/SPEC2.md`). Its parameters are:
  - `N = M = P_r`, the number of ports;
  - `W = TW + PW`, the flit data `{dst, payload}`;
  - `D` = the configuration's FIFO depth;
  - `TW` as above;
  - `ROUTE` = the routing table below.
  - Use the library version for your language: `lib/noc_sw.sv` (SystemVerilog, `ROUTE` packed 8 bits per entry) or `lib/router.py` (UHDL, `router(N, M, W, D, TW, route_list)`).
- **Port order of router r.** First its endpoints, in increasing endpoint id. Then its links, in increasing neighbour router id. `P_r` is the total.
- **Endpoint port.** The endpoint's `l_in_*` signals drive the router's input on that port:
  - `in_tgt = l_in_dst`;
  - `in_data = {l_in_dst, l_in_data}`.

  The router's output on that port drives `l_out_*`:
  - `l_out_dst` is the top TW bits of `out_data`;
  - `l_out_data` is the low PW bits.

  `l_in_rdy` is the router's `in_rdy` and `out_rdy` is `l_out_rdy`.
- **Link port.** Router a's port toward b connects to router b's port toward a, in both directions:
  - `out_vld`, `out_last` and `out_data` of one side drive `in_vld`, `in_last` and `in_data` of the other;
  - `in_tgt` is the top TW bits of the incoming `out_data`;
  - `out_rdy` is the other side's `in_rdy`.
- `out_src` of the routers is not used.

## Routing table of router r (entry t for t = 0 .. 2^TW - 1)
- If t >= E (no such endpoint), use port 0.
- If endpoint t is attached to r, use t's endpoint port.
- Otherwise, let `dist(a, b)` be the hop count between routers a and b in the link graph. Among the neighbours n of r with `dist(n, endpoints[t]) == dist(r, endpoints[t]) - 1`, pick the one with the **smallest router id**, and use the port toward it.

## Rules
- Must compile and simulate with Verilator 5.044. Module names other than `topo_noc` are free.
- The design must not depend on anything outside your output directory except the provided `lib/` file for your language.
