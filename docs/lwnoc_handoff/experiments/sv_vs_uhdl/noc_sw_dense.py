#!/usr/bin/env python3
"""noc_sw in the dense UHDL syntax (lwnoc_rewrite).
Same circuit, same generated signal names as r4/sonnet/uhdl/D1/gen.py."""
import argparse
import json
from uhdl import *


def clog2(n):
    return (n - 1).bit_length() if n > 1 else 0


def build(N, M, W, D, TW, route):
    SW, RW, PW, CW = max(1, clog2(N)), max(1, clog2(M)), max(1, clog2(D)), D.bit_length()

    class noc_sw(Component):
        MODULE_NAME = 'noc_sw'

        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.in_vld, s.in_last, s.in_rdy = Input(N), Input(N), Output(N)
            s.in_tgt, s.in_data = Input(N * TW), Input(N * W)
            s.out_vld, s.out_last, s.out_rdy = Output(M), Output(M), Input(M)
            s.out_data, s.out_src = Output(M * W), Output(M * SW)
            s.domain(s.clk, s.rst_n)                     # default clock/reset for reg/mem

            tgt, data = s.in_tgt.split(N), s.in_data.split(N)

            # ---- input FIFOs: storage, pointers, head decode
            cnt  = [s.reg(f'cnt_{i}', CW) for i in range(N)]
            wptr = [s.reg(f'wptr_{i}', PW) for i in range(N)]
            rptr = [s.reg(f'rptr_{i}', PW) for i in range(N)]
            fifo = [s.mem(f'fifo_{i}', TW + W + 1, D) for i in range(N)]
            head = [s.wire(f'head_{i}', fifo[i][rptr[i]]) for i in range(N)]
            hv   = [s.wire(f'hv_{i}', cnt[i].gt(0)) for i in range(N)]
            rte  = [s.wire(f'route_{i}', Mux(h[TW + W:W + 1], route), RW) for i, h in enumerate(head)]
            hdata, hlast = [h[W:1] for h in head], [h[0] for h in head]

            # ---- output ports: arbiter
            hs, sel, ovld, olast, odata = [], [], [], [], []
            for o in range(M):
                locked, lidx, ptr = s.reg(f'locked_{o}', 1), s.reg(f'lidx_{o}', SW), s.reg(f'ptr_{o}', SW)
                req = [s.wire(f'req_{o}_{i}', hv[i] & rte[i].eq(o)) for i in range(N)]
                # round-robin pick, one priority chain per pointer value
                rr = s.wire(f'rr_{o}', Mux(ptr, [Priority([(req[(p + k) % N], (p + k) % N) for k in range(N)], p)
                                                  for p in range(N)]), SW)
                cur  = s.wire(f'sel_{o}', If(locked, lidx, rr))
                ov   = s.wire(f'ovld_{o}', If(locked, Mux(lidx, req), Or(*req)))
                od   = s.wire(f'odata_{o}', Mux(cur, hdata))
                ol   = s.wire(f'olast_{o}', Mux(cur, hlast))
                h    = s.wire(f'hs_{o}', ov & s.out_rdy[o])
                done = s.wire(f'done_{o}', h & ol)

                locked += when(done).then(0).when(ov).then(1)
                lidx   += when(ov & ~done).then(cur)
                ptr    += when(done).then(If(cur.eq(N - 1), 0, WrapAdd(cur, 1)))
                hs.append(h); sel.append(cur); ovld.append(ov); olast.append(ol); odata.append(od)

            s.out_vld += Cat(ovld); s.out_last += Cat(olast); s.out_data += Cat(odata); s.out_src += Cat(sel)

            # ---- FIFO enqueue / dequeue
            rdy = []
            for i in range(N):
                r    = s.wire(f'rdy_{i}', cnt[i].lt(D))
                push = s.wire(f'push_{i}', s.in_vld[i] & r)
                pop  = s.wire(f'pop_{i}', Or(*[hs[o] & sel[o].eq(i) for o in range(M)]))
                fifo[i].write(push, wptr[i], Combine(tgt[i], data[i], s.in_last[i]))
                wptr[i] += when(push).then(If(wptr[i].eq(D - 1), 0, WrapAdd(wptr[i], 1)))
                rptr[i] += when(pop).then(If(rptr[i].eq(D - 1), 0, WrapAdd(rptr[i], 1)))
                cnt[i]  += when(push & ~pop).then(WrapAdd(cnt[i], 1)).when(pop & ~push).then(WrapSub(cnt[i], 1))
                rdy.append(r)
            s.in_rdy += Cat(rdy)

    return noc_sw()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--config', required=True)
    a = ap.parse_args()
    with open(a.config) as f:
        c = json.load(f)
    comp = build(c['N'], c['M'], c['W'], c['D'], c['TW'], c['route'])
    print('\n'.join(comp.generate(a.out)))


if __name__ == '__main__':
    main()
