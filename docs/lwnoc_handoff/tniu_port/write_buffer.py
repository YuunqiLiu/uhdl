"""lwmnoc_downstream_write_buffer in UHDL: the TNIU downstream write path.

Write data from the ring goes into a two-bank data SRAM (bank = DBID[0]); the write ROB
(write_rob.py) tracks each write; two senders read a finished write's beats back from their
bank, and an ordered W-mux drains the senders in AW-issue order onto AXI W.
"""
from uhdl import *
from lwmnoc_types import pk
from rob_entry import clog2
from write_rob import write_rob, ip


def write_buffer_sender(ROB_DEPTH, DBID_W, ADDR_W, XFER=pk.RING_MAX_TRANSFER_NUM):
    """lwmnoc_downstream_write_buffer_sender: reads one ROB entry's beats from the data SRAM."""
    RingReq, RingDat = pk.ring_req_chnl, pk.ring_dat_chnl
    BL, SB = pk.RING_BURST_LEN, DBID_W + 1
    assert XFER == 1 << BL and ADDR_W >= DBID_W - 1 + BL

    class lwmnoc_downstream_write_buffer_sender(Component):
        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.domain(s.clk, s.rst_n)
            rob = s.stream_in('rob_entry', RingReq, data='pld')
            s.rob_entry_dbid = Input(DBID_W)
            rdreq = s.stream_out('data_ram_rdreq', ADDR_W, data='addr')
            s.data_ram_rdreq_sideband = Output(SB)
            rdrsp = s.stream_in('data_ram_rdrsp', RingDat, data='dat')
            s.data_ram_rdrsp_sideband = Input(SB)
            out = s.stream_out('sender_dat', RingDat, data='pld')
            s.sender_dat_done = Output(ROB_DEPTH)

            idle = s.reg('sender_idle', 1, init=1)
            cnt = s.reg('rdreq_cnt', BL)
            dbid = s.reg('sender_pld_buffer', DBID_W, rst=None)      # no reset, as in the RTL
            burst = s.reg('sender_burst_buffer', BL)

            last = s.wire('rdreq_last', cnt.eq(burst))
            done = s.wire('rdreq_done', last & rdreq.fire)
            rob.rdy += idle | done
            rdreq.vld += ~idle
            # SRAM row = DBID >> 1, RING_MAX_TRANSFER_NUM beats per row, beat = rdreq_cnt
            rdreq.data += Cat(cnt, dbid[DBID_W - 1:1], UInt(ADDR_W - (DBID_W - 1) - BL, 0)) \
                if ADDR_W > DBID_W - 1 + BL else Cat(cnt, dbid[DBID_W - 1:1])
            s.data_ram_rdreq_sideband += Combine(last, dbid)            # {last beat, full DBID}

            # later blocks win: a new entry accepted on the last read request keeps the sender busy
            with s.when(rdreq.fire):
                cnt <<= WrapAdd(cnt, 1)
            with s.when(done):
                idle <<= 1
            with s.when(rob.fire):
                idle <<= 0
                dbid <<= s.rob_entry_dbid
                burst <<= rob.payload.burst_len
            with s.when(done | idle):
                cnt <<= 0

            # read responses go straight out; the last beat tells the ROB the entry is sent
            out += rdrsp
            sb_last = s.data_ram_rdrsp_sideband[SB - 1]
            sb_row = s.data_ram_rdrsp_sideband[clog2(ROB_DEPTH):1]
            fin = s.wire('data_ram_read_done_ack', rdrsp.fire & sb_last)
            s.sender_dat_done += If(fin, Cat([sb_row.eq(k) for k in range(ROB_DEPTH)]), 0)
            s.mark_unused(s.data_ram_rdrsp_sideband[0])

    return lwmnoc_downstream_write_buffer_sender()


def write_buffer(N=pk.MNOC_TNIU_DNSTREAM_WRITE_ROB_ENTRY_NUM):
    RingReq, RingDat, RingRsp = pk.ring_req_chnl, pk.ring_dat_chnl, pk.ring_rsp_chnl
    AxiAw, AxiW = pk.tniu_axi_aw_chnl, pk.tniu_axi_w_chnl
    EW, HALF = clog2(N), N // 2
    AW_, SB = pk.TNIU_WR_DATA_ADDR_WIDTH, pk.TNIU_WR_DATA_SB_WIDTH
    DW = RingDat.width

    class lwmnoc_downstream_write_buffer(Component):
        MODULE_NAME = 'lwmnoc_downstream_write_buffer'

        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.domain(s.clk, s.rst_n)
            s.node_id = Input(4)
            rx_req = s.stream_in('rx_req', RingReq, data='pld')
            rx_dat = s.stream_in('rx_dat', RingDat, data='pld')
            tx_rsp = s.stream_out('tx_rsp', RingRsp, data='pld')
            aw = s.stream_out('axi_aw', AxiAw, data='pld')
            s.b_done_vld, s.b_done_entry_id = Input(1), Input(EW)
            w = s.stream_out('axi_w', AxiW, data='pld')
            # data SRAM, two banks: bank b uses bit b of vld/rdy and slice b of each vector
            s.data_ram_write_req_vld, s.data_ram_write_req_rdy = Output(2), Input(2)
            s.data_ram_write_req_addr = Output(2 * AW_)
            s.data_ram_write_req_data, s.data_ram_write_req_bit_en = Output(2 * DW), Output(2 * DW)
            s.data_ram_read_req_vld, s.data_ram_read_req_rdy = Output(2), Input(2)
            s.data_ram_read_req_addr, s.data_ram_read_req_sideband = Output(2 * AW_), Output(2 * SB)
            s.data_ram_read_resp_vld, s.data_ram_read_resp_data = Input(2), Input(2 * DW)
            s.data_ram_read_resp_sideband, s.data_ram_read_resp_rdy = Input(2 * SB), Output(2)

            s.u_rob = write_rob(N)                                            # clk/rst_n follow the domain
            rob = s.u_rob
            dat = RingDat(rx_dat.data)

            # ---- ring write data -> data SRAM bank DBID[0]
            bank = dat.dbid[0]
            rx_dat.rdy += If(bank, s.data_ram_write_req_rdy[1], s.data_ram_write_req_rdy[0])
            row = Cat(dat.txn_id[1:0], dat.dbid[dat.dbid.attribute.width - 1:1])  # (dbid >> 1) * 4 + beat
            for b in range(2):
                s.data_ram_write_req_vld[b] += rx_dat.vld & (bank if b else ~bank)
                s.data_ram_write_req_addr[(b + 1) * AW_ - 1:b * AW_] += row
                s.data_ram_write_req_data[(b + 1) * DW - 1:b * DW] += rx_dat.data
                s.data_ram_write_req_bit_en[(b + 1) * DW - 1:b * DW] += UInt(DW, (1 << DW) - 1)

            # ---- ROB
            rob.node_id += s.node_id
            rob.rx_req_vld += rx_req.vld; rx_req.rdy += rob.rx_req_rdy; rob.rx_req_pld += rx_req.data
            rob.rx_dat_ack += rx_dat.fire
            rob.rx_dat_pld += rx_dat.data
            tx_rsp += Stream.of(rob, 'tx_rsp', data='pld')
            rob.b_done_vld += s.b_done_vld; rob.b_done_entry_id += s.b_done_entry_id

            # ---- two senders: SRAM read requests through a forward register slice each
            snd_vld, snd_pld = [], []
            for b in range(2):
                sd = s.create(f'u_write_sender_{b}', write_buffer_sender(HALF, EW, AW_))
                sd.rob_entry_vld += rob.sender_vld[b]
                sd.rob_entry_pld += rob.sender_pld[(b + 1) * RingReq.width - 1:b * RingReq.width]
                sd.rob_entry_dbid += rob.sender_dbid[(b + 1) * EW - 1:b * EW]
                rob.sender_rdy[b] += sd.rob_entry_rdy
                rob.sender_dat_done[(b + 1) * HALF - 1:b * HALF] += sd.sender_dat_done

                rs = s.create(f'u_rs_data_dreq_{b}', ip('fcip_reg_slice', RS_TYPE=1, PLD_TYPE=SvType('logic [%d:0]' % (AW_ + SB - 1))))
                rs.s_vld += sd.data_ram_rdreq_vld
                sd.data_ram_rdreq_rdy += rs.s_rdy
                rs.s_pld += Combine(sd.data_ram_rdreq_addr, sd.data_ram_rdreq_sideband)
                s.data_ram_read_req_vld[b] += rs.m_vld
                rs.m_rdy += s.data_ram_read_req_rdy[b]
                s.data_ram_read_req_addr[(b + 1) * AW_ - 1:b * AW_] += rs.m_pld[AW_ + SB - 1:SB]
                s.data_ram_read_req_sideband[(b + 1) * SB - 1:b * SB] += rs.m_pld[SB - 1:0]

                sd.data_ram_rdrsp_vld += s.data_ram_read_resp_vld[b]
                sd.data_ram_rdrsp_dat += s.data_ram_read_resp_data[(b + 1) * DW - 1:b * DW]
                sd.data_ram_rdrsp_sideband += s.data_ram_read_resp_sideband[(b + 1) * SB - 1:b * SB]
                s.data_ram_read_resp_rdy[b] += sd.data_ram_rdrsp_rdy
                snd_vld.append(sd.sender_dat_vld); snd_pld.append(sd.sender_dat_pld)

            # ---- ordered W-mux: drain the sender that owns the head of the AW-order FIFO,
            #      a whole transaction at a time (pop on the tail beat)
            s.u_sender_rs = ip('fcip_reg_slice', RS_TYPE=0, PLD_TYPE=SvType('lwmnoc_pack::ring_dat_chnl'))
            rs = s.u_sender_rs
            head = rob.aw_order_dbid[0]
            w_vld = s.wire('rs_sender_vld', rob.aw_order_vld & Mux(head, snd_vld))
            w_pld = s.wire('rs_sender_pld', Mux(head, snd_pld))
            rs.s_vld += w_vld
            rs.s_pld += w_pld
            for b, sd in enumerate([s.u_write_sender_0, s.u_write_sender_1]):
                sd.sender_dat_rdy += rob.aw_order_vld & head.eq(b) & rs.s_rdy
            rob.aw_order_rdy += w_vld & rs.s_rdy & RingDat(w_pld).tail

            # ---- ring -> AXI
            a = RingReq(rob.axi_aw_pld)
            aw.vld += rob.axi_aw_vld
            rob.axi_aw_rdy += aw.rdy
            x = a.req_ext
            aw.data += AxiAw.pack(awid=Combine(rob.axi_aw_entry_id, a.src_id, a.txn_id), awaddr=a.addr,
                                  awlen=a.burst_len, awsize=a.size, awburst=x.axburst, awlock=x.axlock,
                                  awcache=x.axcache, awprot=x.axprot, awqos=x.axqos, awregion=x.axregion,
                                  awdomain=x.axdomain, awsnoop=x.axsnoop, awuser=a.user)
            d = RingDat(rs.m_pld)
            w.vld += rs.m_vld
            rs.m_rdy += w.rdy
            w.data += AxiW.pack(wdata=d.data, wstrb=d.strb, wlast=d.tail)
            s.mark_unused(Cat(d.opcode, d.src_id, d.tgt_id, d.txn_id, d.dbid, d.resp, d.head, d.dat_ext.bits, d.user, d.ecc))

    return lwmnoc_downstream_write_buffer()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    print('\n'.join(write_buffer().generate(a.out)))
