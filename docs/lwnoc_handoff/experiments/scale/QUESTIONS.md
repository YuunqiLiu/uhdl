# Questions about mesh_noc

Answer from the design you were given. Node ids are the indices of the `l_in_*` / `l_out_*` ports (see README.md). "Router of node n" means the router whose local port is node n's `l_in_*` / `l_out_*`.

1. **Path.** A single-flit packet is injected at node 0 with destination node 63. List, in order, the node ids of the routers it passes through (include the first and the last router).
2. **Path.** Same for a packet from node 46 to node 17.
3. **Latency.** The network is idle (just out of reset) and every `l_out_rdy` is 1. A single-flit packet from node 0 to node 63 is accepted at node 0 at rising clock edge 0. After which rising edge number does `l_out_vld` of node 63 first read 1? (If it is visible right after edge k, answer k.)
4. **Storage.** How many bits of storage are there in all router input FIFO memory arrays together? Count only the FIFO data arrays, not pointers, counters or other registers.
5. **Reachability.** In an otherwise idle network, which (source node, destination node) pairs can **never** be delivered? Give the number of such pairs and describe the set exactly (a rule or a full list).
6. **Traffic sources.** Consider flits whose destination is node 3, and the router of node 27. Which of the following can ever deliver such a flit into that router: local injection at node 27, or the router of a neighbouring node (give the neighbours' node ids)? List exactly the ones that can.
7. **Behaviour.** The network is otherwise idle and node 16 sends a single-flit packet to node 23. What happens to that flit? Be specific (which routers, what it does, whether it arrives).

Write your answers to `answers.json` in your output directory:
```json
{"q1": [0, ...], "q2": [46, ...], "q3": 0, "q4": 0,
 "q5": {"count": 0, "rule": "..."}, "q6": {"local": true, "neighbours": [..]},
 "q7": "...", "notes": "how you found the answers, and anything you are unsure of"}
```
