# mesh_noc

`mesh_noc` is a network-on-chip built from packet routers. It has 64 nodes, numbered 0..63.

Top-level ports (clock `clk`, asynchronous active-low reset `rst_n`). Node n uses bits `[n*w +: w]` of each flat vector:

| Port | Dir | Width per node | Meaning |
|---|---|---|---|
| `l_in_vld`, `l_in_last` | in | 1 | local injection: flit valid, last flit of packet |
| `l_in_rdy` | out | 1 | local injection ready |
| `l_in_dst` | in | 6 | destination node id of the flit |
| `l_in_data` | in | 32 | payload |
| `l_out_vld`, `l_out_last` | out | 1 | local ejection: flit valid, last flit |
| `l_out_rdy` | in | 1 | local ejection ready |
| `l_out_dst` | out | 6 | destination id carried by the flit |
| `l_out_data` | out | 32 | payload |

A flit is transferred when valid and ready are both 1 at a rising clock edge. A packet is a sequence of flits with the same destination; `last` marks its final flit.
