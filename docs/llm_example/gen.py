#!/usr/bin/env python3
"""LLM guide example: a histogram counter.

    hist: on each cycle with vld=1, cnt[bin] += 1 (saturating at 2**CW-1).
          rd_addr/rd_cnt read any bin combinationally; clr_all resets nothing in
          the Mem (Mems have no reset) but masks reads until each bin is written.

Shows: MODULE_NAME, a parameterised sub-component, Mem, WrapAdd, Case with a
default, when-chains, mark_unused and generate(out_dir).

Run:  python gen.py --out build --BINS 12 --CW 6
"""
import argparse
from uhdl import (Component, Input, Output, Wire, Reg, Mem, UInt, when, Case,
                  WrapAdd, Equal, And, Not, SelfAnd, Combine)


def clog2(n):
    return max(1, (n - 1).bit_length())


class SatInc(Component):
    """y = (a == all-ones) ? a : a + 1.  Has an __init__ argument, so its
    module name is derived from it (SatInc_W_6); that keeps different widths
    apart automatically."""

    def __init__(self, W):
        self.W = W                      # must be set before super().__init__() runs circuit()
        super().__init__()

    def circuit(self):
        self.a = Input(UInt(self.W))
        self.y = Output(UInt(self.W))
        self.at_max = Wire(UInt(1))
        self.at_max += SelfAnd(self.a)
        self.y += when(self.at_max).then(self.a).otherwise(WrapAdd(self.a, UInt(self.W, 1)))


def build(BINS, CW):
    AW = clog2(BINS)

    class hist(Component):
        MODULE_NAME = 'hist'            # exact top-level module name

        def circuit(self):
            # ---- ports
            self.clk     = Input(UInt(1))
            self.rst_n   = Input(UInt(1))
            self.vld     = Input(UInt(1))
            self.bin     = Input(UInt(AW))
            self.rd_addr = Input(UInt(AW))
            self.rd_cnt  = Output(UInt(CW))
            self.clr_all = Input(UInt(1))

            # ---- storage: no reset, so track which bins hold valid data
            self.cnt = Mem(UInt(CW), BINS, self.clk)
            self.valid = Reg(UInt(BINS, 0), self.clk, self.rst_n)

            in_range = Wire(UInt(1))
            self.in_range = in_range
            in_range += Case(self.bin, {UInt(AW, i): UInt(1, 1) for i in range(BINS)}, UInt(1, 0))

            # ---- read-modify-write through the sub-component
            self.cur = Wire(UInt(CW))
            bin_valid = Case(self.bin, {UInt(AW, i): self.valid[i] for i in range(BINS)}, UInt(1, 0))
            self.cur += when(bin_valid).then(self.cnt.read(self.bin)).otherwise(UInt(CW, 0))
            self.inc = SatInc(CW)
            self.inc.a += self.cur
            self.we = Wire(UInt(1))
            self.we += And(self.vld, in_range)
            self.cnt.write(self.we, self.bin, self.inc.y)

            # ---- valid bits: set on write, cleared by clr_all (clr wins)
            set_bits = Combine(*[And(self.we, Equal(self.bin, UInt(AW, i))) for i in reversed(range(BINS))])
            self.valid += when(self.clr_all).then(UInt(BINS, 0)) \
                          .when(self.we).then(self.valid | set_bits)

            # ---- read port
            rd_valid = Case(self.rd_addr, {UInt(AW, i): self.valid[i] for i in range(BINS)}, UInt(1, 0))
            self.rd_cnt += when(rd_valid).then(self.cnt.read(self.rd_addr)).otherwise(UInt(CW, 0))

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
