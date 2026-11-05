#!/usr/bin/env python3
"""LLM guide example: a histogram counter.

    hist: on each cycle with vld=1, cnt[bin] += 1 (saturating at 2**CW-1).
          rd_addr/rd_cnt read any bin combinationally; clr_all resets nothing in
          the Mem (Mems have no reset) but masks reads until each bin is written.

Shows: MODULE_NAME, a parameterised sub-component, the default clock domain,
self.wire/self.reg/self.mem, int literals, Mux, If, Cat and generate(out_dir).

Run:  python gen.py --out build --BINS 12 --CW 6
"""
import argparse
from uhdl import *


def clog2(n):
    return max(1, (n - 1).bit_length())


class SatInc(Component):
    """y = (a == all-ones) ? a : a + 1.  Has an __init__ argument, so its
    module name is derived from it (SatInc_W_6); that keeps different widths
    apart automatically."""

    def __init__(self, W):
        self.W = W                      # must be set before super().__init__() runs circuit()
        super().__init__()

    def circuit(s):
        s.a, s.y = Input(s.W), Output(s.W)
        at_max = s.wire('at_max', SelfAnd(s.a))
        s.y += If(at_max, s.a, WrapAdd(s.a, 1))


def build(BINS, CW):
    AW = clog2(BINS)

    class hist(Component):
        MODULE_NAME = 'hist'            # exact top-level module name

        def circuit(s):
            # ---- ports
            s.clk, s.rst_n = Input(1), Input(1)
            s.vld, s.bin = Input(1), Input(AW)
            s.rd_addr, s.rd_cnt = Input(AW), Output(CW)
            s.clr_all = Input(1)
            s.domain(s.clk, s.rst_n)    # default clock/reset for s.reg / s.mem

            # ---- storage: no reset, so track which bins hold valid data
            cnt = s.mem('cnt', CW, BINS)
            valid = s.reg('valid', BINS)
            vbits = valid.split(BINS)   # vbits[i] == valid[i]

            in_range = s.wire('in_range', Mux(s.bin, [1] * BINS), width=1)   # bin < BINS, any BINS

            # ---- read-modify-write through the sub-component
            cur = s.wire('cur', If(Mux(s.bin, vbits), cnt[s.bin], 0))
            s.inc = SatInc(CW)
            s.inc.a += cur
            we = s.wire('we', s.vld & in_range)
            cnt.write(we, s.bin, s.inc.y)

            # ---- valid bits: set on write, cleared by clr_all (clr wins)
            set_bits = Cat([we & s.bin.eq(i) for i in range(BINS)])
            valid += when(s.clr_all).then(0).when(we).then(valid | set_bits)

            # ---- read port
            s.rd_cnt += If(Mux(s.rd_addr, vbits), cnt[s.rd_addr], 0)

    return hist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--BINS', type=int, default=12)
    ap.add_argument('--CW', type=int, default=6)
    a = ap.parse_args()
    paths = build(a.BINS, a.CW).generate(a.out)     # <out>/SatInc_W_6.v, <out>/hist.v, <out>/filelist.f
    print('\n'.join(paths))


if __name__ == '__main__':
    main()
