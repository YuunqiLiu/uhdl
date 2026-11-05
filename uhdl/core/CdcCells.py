"""Clock-domain crossing cells. check_cdc() accepts a crossing only inside one of these.

    CdcSync()          1 bit, two flops in the destination clock. Its input must come
                       straight from a register (or port) of the source domain.
    CdcBus(W)          a multi-bit value that changes now and then (a counter, a status
                       word). Toggle handshake: dst_data is always a value src_data had,
                       never a mix of two values. Updates every few cycles of each clock.
    AsyncFifo(W, D)    a stream with valid/ready on both sides. D must be a power of 2.
"""
from .Component import Component
from .Variable import Input, Output, UInt
from .Operator import When, If, WrapAdd, Cat


def _clog2(n):
    return max(1, (n - 1).bit_length())


class CdcSync(Component):
    CDC_CELL = 'sync'
    MODULE_NAME = 'uhdl_cdc_sync'

    def circuit(s):
        s.clk, s.rst_n = Input(1), Input(1)            # destination clock / reset
        s.d = Input(1)
        s.q = Output(1, domain=s.clk)
        s.domain(s.clk, s.rst_n)
        q1 = s.reg('q1', 1)
        q2 = s.reg('q2', 1)
        q1 += s.d
        q2 += q1
        s.q += q2


class CdcBus(Component):
    CDC_CELL = 'bus'

    def __init__(self, W):
        self.W = W
        super().__init__()

    def circuit(s):
        W = s.W
        s.src_clk, s.src_rst_n, s.src_data = Input(1), Input(1), Input(W)
        s.dst_clk, s.dst_rst_n = Input(1), Input(1)
        s.dst_data = Output(W, domain=s.dst_clk)
        # source side: capture a value and toggle req whenever the last one was acknowledged
        s.domain(s.src_clk, s.src_rst_n)
        hold, req = s.reg('hold', W), s.reg('req', 1)
        ack_s1, ack_s2 = s.reg('ack_s1', 1), s.reg('ack_s2', 1)
        idle = s.wire('idle', req.eq(ack_s2))
        hold += When(idle).then(s.src_data)
        req += When(idle).then(~req)
        # destination side: take hold when req toggles, then acknowledge
        s.domain(s.dst_clk, s.dst_rst_n)
        req_d1, req_d2, req_d3 = s.reg('req_d1', 1), s.reg('req_d2', 1), s.reg('req_d3', 1)
        ack, data = s.reg('ack', 1), s.reg('data', W)
        req_d1 += req
        req_d2 += req_d1
        req_d3 += req_d2
        upd = s.wire('upd', req_d2 ^ req_d3)
        data += When(upd).then(hold)
        ack += req_d2
        s.dst_data += data
        s.domain(s.src_clk, s.src_rst_n)
        ack_s1 += ack
        ack_s2 += ack_s1


class AsyncFifo(Component):
    CDC_CELL = 'fifo'

    def __init__(self, W, D=4):
        if D < 2 or D & (D - 1):
            raise ValueError('AsyncFifo depth must be a power of 2 >= 2, got %r' % D)
        self.W, self.D = W, D
        super().__init__()

    def circuit(s):
        W, D = s.W, s.D
        AW = _clog2(D)
        PW = AW + 1
        s.wclk, s.wrst_n = Input(1), Input(1)
        s.w_vld, s.w_data = Input(1), Input(W)
        s.w_rdy = Output(1, domain=s.wclk)
        s.rclk, s.rrst_n = Input(1), Input(1)
        s.r_rdy = Input(1)
        s.r_vld = Output(1, domain=s.rclk)
        s.r_data = Output(W, domain=s.rclk)

        gray = lambda b: b ^ (b >> 1)
        # write side
        s.domain(s.wclk, s.wrst_n)
        mem = s.mem('mem', W, D)
        wbin, wgray = s.reg('wbin', PW), s.reg('wgray', PW)
        rq1, rq2 = s.reg('rq1', PW), s.reg('rq2', PW)
        full = s.wire('full', wgray.eq(rq2 ^ (3 << (AW - 1))))
        push = s.wire('push', s.w_vld & ~full)
        wnext = s.wire('wnext', WrapAdd(wbin, 1))
        mem.write(push, wbin[AW - 1:0], s.w_data)
        wbin += When(push).then(wnext)
        wgray += When(push).then(gray(wnext))
        s.w_rdy += ~full
        # read side
        s.domain(s.rclk, s.rrst_n)
        rbin, rgray = s.reg('rbin', PW), s.reg('rgray', PW)
        wq1, wq2 = s.reg('wq1', PW), s.reg('wq2', PW)
        empty = s.wire('empty', rgray.eq(wq2))
        pop = s.wire('pop', s.r_rdy & ~empty)
        rnext = s.wire('rnext', WrapAdd(rbin, 1))
        rbin += When(pop).then(rnext)
        rgray += When(pop).then(gray(rnext))
        s.r_vld += ~empty
        s.r_data += mem[rbin[AW - 1:0]]
        # pointer synchronizers
        wq1 += wgray
        wq2 += wq1
        s.domain(s.wclk, s.wrst_n)
        rq1 += rgray
        rq2 += rq1
