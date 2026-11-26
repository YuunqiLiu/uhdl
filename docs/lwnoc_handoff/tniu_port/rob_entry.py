"""lwmnoc_downstream_rob_entry in UHDL: one entry of the TNIU downstream write ROB.

An entry takes a write request (rx_req_ack), answers it with a DBID response, collects
the write data beats into a bitmap, then sends AW and W downstream once every older
write it overlaps (WAW hazard) has finished. It is released when both the B response
and the sender's done have been seen.
"""
from uhdl import *
from lwmnoc_types import pk


def clog2(n):
    return max(1, (n - 1).bit_length())


def rob_entry(N=pk.MNOC_TNIU_DNSTREAM_WRITE_ROB_ENTRY_NUM, XFER=pk.RING_MAX_TRANSFER_NUM):
    RingReq, AddrRange = pk.ring_req_chnl, pk.axi_addr_range_t

    class lwmnoc_downstream_rob_entry(Component):
        MODULE_NAME = 'lwmnoc_downstream_rob_entry'

        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.domain(s.clk, s.rst_n)
            s.prealloc_vld = Output(1)
            s.rx_req_ack, s.rx_req_pld = Input(1), Input(RingReq.width)
            s.rx_dat_ack, s.rx_dat_burst_id = Input(1), Input(clog2(XFER))
            s.waw_addr_range = Input(AddrRange.width)
            s.waw_hzd_dep, s.all_entry_release = Input(N), Input(N)
            s.waw_hzd_flag = Output(1)
            dbid = s.stream_out('dbid_rsp', RingReq, data='req_pld')
            aw = s.stream_out('axi_aw', RingReq, data='pld')
            snd = s.stream_out('sender', RingReq, data='pld')
            s.sender_done, s.b_done = Input(1), Input(1)
            s.entry_release = Output(1)

            # entry state
            idle = s.reg('entry_idle', 1, init=1)
            req_done, dbid_sent, data_done = s.reg('receive_req_done', 1), s.reg('send_dbid_sent', 1), s.reg('receive_data_done', 1)
            aw_sent, w_sent = s.reg('send_aw_sent', 1), s.reg('send_w_sent', 1)
            b_rcvd, snd_rcvd = s.reg('b_done_rcvd', 1), s.reg('sender_done_rcvd', 1)
            exp_map, rcv_map = s.reg('dat_exp_bitmap', XFER), s.reg('dat_rcv_bitmap', XFER)
            hzd = s.reg('hzd_status', N)
            buf = s.reg('entry_pld_buffer', RingReq.width)
            rng = s.reg('local_addr_range', AddrRange.width)

            # interface
            hazard = SelfOr(hzd)
            s.prealloc_vld += idle
            dbid.vld += req_done & ~dbid_sent
            aw.vld += req_done & data_done & ~aw_sent & ~hazard
            snd.vld += data_done & req_done & ~w_sent & ~hazard
            for st in (dbid, aw, snd):
                st.data += buf
            release = s.wire('entry_free', (b_rcvd | s.b_done) & (snd_rcvd | s.sender_done))
            s.entry_release += release

            # data beats: one bit per burst index
            rcv_beat = s.wire('entry_receive_data', s.rx_dat_ack & dbid_sent)
            rcv_next = s.wire('dat_rcv_bitmap_nxt', If(rcv_beat, rcv_map | (UInt(XFER, 1) << s.rx_dat_burst_id), rcv_map))
            all_rcvd = s.wire('dat_all_rcvd', (rcv_next & exp_map).eq(exp_map))
            burst_len = RingReq(s.rx_req_pld).burst_len
            exp_init = Cat([burst_len.ge(b) for b in range(XFER)])

            # WAW hazard: an older write overlapping this one is still pending
            mine, other = AddrRange(rng), AddrRange(s.waw_addr_range)
            s.waw_hzd_flag += ~(other.lower.gt(mine.upper) | other.upper.lt(mine.lower)) & req_done

            # state updates: later blocks take priority over earlier ones
            hzd <<= hzd & ~s.all_entry_release                 # older entries retire one by one
            with s.when(dbid.fire):
                dbid_sent <<= 1
            with s.when(rcv_beat):
                rcv_map <<= rcv_next
                with s.when(all_rcvd):
                    data_done <<= 1
            with s.when(aw.fire):
                aw_sent <<= 1
            with s.when(snd.fire):
                w_sent <<= 1
            with s.when(s.b_done):
                b_rcvd <<= 1
            with s.when(s.sender_done):
                snd_rcvd <<= 1
            with s.when(s.rx_req_ack):                          # a new request takes the entry
                idle <<= 0
                req_done <<= 1
                data_done <<= 0
                exp_map <<= exp_init
                rcv_map <<= 0
                hzd <<= s.waw_hzd_dep & ~s.all_entry_release
                buf <<= s.rx_req_pld
                rng <<= s.waw_addr_range
            with s.when(release):                               # highest priority: free the entry
                idle <<= 1
                for r in (req_done, dbid_sent, data_done, aw_sent, w_sent, b_rcvd, snd_rcvd, exp_map, rcv_map, hzd):
                    r <<= 0


    return lwmnoc_downstream_rob_entry()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    print('\n'.join(rob_entry().generate(a.out)))
