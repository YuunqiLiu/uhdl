# Change request for mesh_noc

Starting from the design you were given (see ../README.md for the top-level interface), make **all four** changes below. Everything not mentioned must keep its current behaviour cycle for cycle. Grading compares your design with a reference implementation of these changes, port by port and cycle by cycle, under random traffic.

Node (x, y) is node id n = y*8 + x, with x growing to the east and y to the north, as in the existing design.

1. **Remove the routing exception.** The router of node 21, at (5, 2), currently sends column-7 traffic west. Remove that exception, so the router follows the normal routing rule.
2. **Route Y first, then X.** Change the routing rule of every router: move north or south until the row matches, then east or west until the column matches, then deliver locally.
3. **Deeper FIFOs in the centre.** The routers of nodes with 2 <= x <= 5 and 2 <= y <= 5 (the central 4x4 block) get an input FIFO depth of 8 on all five inputs. All other routers keep depth 4.
4. **Report the source.** Add an output port `l_out_src`, 6 bits per node, flat like the others: node n uses `l_out_src[n*6 +: 6]`. Whenever `l_out_vld[n]` is 1, it must hold the id of the node whose local input injected that flit. Its value while `l_out_vld[n]` is 0 does not matter.

The top module stays `mesh_noc`, with all existing ports unchanged.
