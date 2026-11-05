"""Clock-domain crossing cells. check_cdc() accepts a crossing only inside one of these.

    CdcSync()          1 bit, two flops in the destination clock. Its input must come
                       straight from a register (or port) of the source domain.
    CdcBus(W)          a multi-bit value that changes now and then (a counter, a status
                       word). Toggle handshake: dst_data is always a value src_data had,
                       never a mix of two values. Updates every few cycles of each clock.
    AsyncFifo(W, D)    a stream with valid/ready on both sides. D must be a power of 2.

W may be a Struct. Clocks can be given at construction and are connected when the cell is
placed in its parent: CdcBus(W, src=(clk, rst_n), dst=(clk, rst_n)),
AsyncFifo(W, D, w=(clk, rst_n), r=(clk, rst_n)). CdcSync's clk/rst_n, if left open, follow the
parent's current s.domain(). AsyncFifo.w / .r are its two ends as Streams.
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


def _pair(comp, names, pair):
    if pair is not None:
        clk, rst = pair if isinstance(pair, (tuple, list)) else (pair, None)
        comp._connect_on_attach(names[0], clk)
        comp._connect_on_attach(names[1], rst)


class CdcBus(Component):
    CDC_CELL = 'bus'
    CLOCK_PORTS = ()

    def __init__(self, W, **clocks):
        self.payload = W if hasattr(W, 'fields') else None
        W = W.width if self.payload is not None else W
        self.W = W
        src, dst = clocks.pop('src', None), clocks.pop('dst', None)
        if clocks:
            raise TypeError('CdcBus: unknown arguments %s' % ', '.join(clocks))
        super().__init__()
        self.set_module_name('CdcBus_W_%d' % W)
        _pair(self, ('src_clk', 'src_rst_n'), src)
        _pair(self, ('dst_clk', 'dst_rst_n'), dst)

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
    CLOCK_PORTS = ()

    def __init__(self, W, D=4, **clocks):
        if D < 2 or D & (D - 1):
            raise ValueError('AsyncFifo depth must be a power of 2 >= 2, got %r' % D)
        self.payload = W if hasattr(W, 'fields') else None
        W = W.width if self.payload is not None else W
        self.W, self.D = W, D
        wpair, rpair = clocks.pop('w', None), clocks.pop('r', None)
        if clocks:
            raise TypeError('AsyncFifo: unknown arguments %s' % ', '.join(clocks))
        super().__init__()
        self.set_module_name('AsyncFifo_W_%d_D_%d' % (W, D))
        _pair(self, ('wclk', 'wrst_n'), wpair)
        _pair(self, ('rclk', 'rrst_n'), rpair)

    @property
    def w(self):
        """The write end as a Stream (drive it: fifo.w += src)."""
        from .Struct import Stream
        return Stream(self.w_vld, self.w_rdy, data=self.w_data, struct=self.payload)

    @w.setter
    def w(self, v):          # `fifo.w += src` ends in setattr(fifo, 'w', <the stream>)
        _accept_stream(v)

    @property
    def r(self):
        """The read end as a Stream (dst += fifo.r)."""
        from .Struct import Stream
        return Stream(self.r_vld, self.r_rdy, data=self.r_data, struct=self.payload)

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

    @r.setter
    def r(self, v):
        _accept_stream(v)


def _accept_stream(v):
    from .Struct import Stream
    if not isinstance(v, Stream):
        raise AttributeError('AsyncFifo.w / .r are its stream ends; connect them with +=.')
