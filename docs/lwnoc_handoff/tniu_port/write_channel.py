"""lwmnoc_tniu_write_channel in UHDL: the TNIU write channel, ring side to AXI side.

Ring write requests are queued in an SRAM-backed FIFO, write data passes a forward register
slice, and both feed the write buffer (write_buffer.py). AW leaves through a full register slice;
AXI B responses are turned back into ring Comp responses (through a FIFO) and free the ROB
entry whose id travels in BID.
"""
from uhdl import *
from lwmnoc_types import pk
from rob_entry import clog2
from write_buffer import write_buffer
from write_rob import ip


def write_channel():
    RingReq, RingDat, RingRsp = pk.ring_req_chnl, pk.ring_dat_chnl, pk.ring_rsp_chnl
    AxiAw, AxiW, AxiB = pk.tniu_axi_aw_chnl, pk.tniu_axi_w_chnl, pk.tniu_axi_b_chnl
    DEPTH = pk.TNIU_B_FIFO_DEPTH
    FW, EW = clog2(DEPTH), pk.TNIU_DNSTREAM_WRITE_ROB_ENTRY_WIDTH
    BIDW, TGTW = pk.INIU_AXI_BID_WIDTH, pk.RING_TGT_ID_WIDTH
    ENTRY_LSB = BIDW + pk.RING_SRC_ID_WIDTH                    # BID = {entry id, src id, txn id}
    AW_, SB, DW = pk.TNIU_WR_DATA_ADDR_WIDTH, pk.TNIU_WR_DATA_SB_WIDTH, RingDat.width

    class lwmnoc_tniu_write_channel(Component):
        MODULE_NAME = 'lwmnoc_tniu_write_channel'

        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.domain(s.clk, s.rst_n)
            s.node_id = Input(TGTW)
            aw = s.stream_out('axi_aw', AxiAw, data='pld')
            w = s.stream_out('axi_w', AxiW, data='pld')
            b = s.stream_in('axi_b', AxiB, data='pld')
            rx_req = s.stream_in('rx_req', RingReq, data='pld')
            rx_dat = s.stream_in('rx_dat', RingDat, data='pld')
            dbid_rsp = s.stream_out('tx_dbid_rsp', RingRsp, data='pld')
            tx_rsp = s.stream_out('tx_rsp', RingRsp, data='pld')
            sram = []
            for g in range(2):                                     # request-FIFO SRAM banks
                p = lambda n, io, wd: s.create(f'req_fifo_sram_{g}_{n}', io(wd))
                sram.append(dict(addr=p('addr', Output, FW), din=p('din', Output, RingReq.width),
                                 dout=p('dout', Input, RingReq.width), en=p('en', Output, 1),
                                 wren=p('wren', Output, 1), bit_en=p('bit_en', Output, RingReq.width)))
            # data SRAM ports pass straight through to the write buffer
            dram = [('data_ram_write_req_vld', Output, 2), ('data_ram_write_req_rdy', Input, 2),
                    ('data_ram_write_req_addr', Output, 2 * AW_), ('data_ram_write_req_data', Output, 2 * DW),
                    ('data_ram_write_req_bit_en', Output, 2 * DW), ('data_ram_read_req_vld', Output, 2),
                    ('data_ram_read_req_rdy', Input, 2), ('data_ram_read_req_addr', Output, 2 * AW_),
                    ('data_ram_read_req_sideband', Output, 2 * SB), ('data_ram_read_resp_vld', Input, 2),
                    ('data_ram_read_resp_data', Input, 2 * DW), ('data_ram_read_resp_sideband', Input, 2 * SB),
                    ('data_ram_read_resp_rdy', Output, 2)]
            for n, io, wd in dram:
                s.create(n, io(wd))

            # ---- blocks
            s.u_req_fifo = ip('fcip_sync_fifo_spram', FIFO_DEPTH_PER_GROUP=DEPTH, SRAM_GROUP_NUM=2,
                              DATA_WIDTH=RingReq.width, FORWARD_EN=0, ROB_DEPTH=16, SRAM_ACCESS_LATENCY=1,
                              SRAM_REQ_PIPE_STAGE=0, SRAM_RSP_PIPE_STAGE=0, MCP_CYCLE=1)
            s.u_r_fifo = ip('lwnoc_vrp_reg_fifo', ADDR_WIDTH=FW, PLD_TYPE=SvType('lwmnoc_pack::ring_rsp_chnl'))
            s.u_rs_rx_dat = ip('fcip_reg_slice', RS_TYPE=1, PLD_TYPE=SvType('lwmnoc_pack::ring_dat_chnl'))
            s.u_rs_axi_aw_chnl = ip('fcip_reg_slice', RS_TYPE=0, PLD_TYPE=SvType('lwmnoc_pack::tniu_axi_aw_chnl'))
            s.u_write_buffer = write_buffer()
            qf, rf, rsd, rsa, wb = s.u_req_fifo, s.u_r_fifo, s.u_rs_rx_dat, s.u_rs_axi_aw_chnl, s.u_write_buffer

            # ---- request FIFO (SRAM backed)
            qf.almost_full_threshold_val += 2
            qf.almost_empty_threshold_val += 2
            qf.stall += 0
            qf.clear += 0
            qf.write_req_vld += rx_req.vld; qf.write_req_pld += rx_req.data; rx_req.rdy += qf.write_req_rdy
            for g, m in enumerate(sram):
                m['addr'] += qf.spram_addr[(g + 1) * FW - 1:g * FW]
                for n in ('din', 'bit_en'):
                    m[n] += getattr(qf, 'spram_' + n)[(g + 1) * RingReq.width - 1:g * RingReq.width]
                m['en'] += qf.spram_en[g]
                m['wren'] += qf.spram_wren[g]
                qf.spram_dout[(g + 1) * RingReq.width - 1:g * RingReq.width] += m['dout']
            s.mark_unused(qf.idle, qf.almost_full, qf.almost_empty, qf.empty, qf.full)

            # ---- write buffer
            wb.node_id += s.node_id
            wb_req, wb_dat = Stream.of(wb, 'rx_req', data='pld'), Stream.of(wb, 'rx_dat', data='pld')
            wb_req += Stream(qf.read_resp_vld, qf.read_resp_rdy, data=qf.read_resp_pld)
            rsd.s_vld += rx_dat.vld; rsd.s_pld += rx_dat.data; rx_dat.rdy += rsd.s_rdy
            wb_dat += Stream(rsd.m_vld, rsd.m_rdy, data=rsd.m_pld)
            dbid_rsp += Stream.of(wb, 'tx_rsp', data='pld')
            rsa.s_vld += wb.axi_aw_vld; rsa.s_pld += wb.axi_aw_pld; wb.axi_aw_rdy += rsa.s_rdy
            aw += Stream(rsa.m_vld, rsa.m_rdy, data=rsa.m_pld)
            w += Stream.of(wb, 'axi_w', data='pld')
            for n, io, _ in dram:
                dst, src = (getattr(s, n), getattr(wb, n)) if io is Output else (getattr(wb, n), getattr(s, n))
                dst += src

            # ---- AXI B -> ring Comp response; BID carries the ROB entry to free
            bid = b.payload.bid
            rf.in_vld += b.vld
            b.rdy += rf.in_rdy
            wb.b_done_vld += b.fire
            wb.b_done_entry_id += bid[ENTRY_LSB + EW - 1:ENTRY_LSB]
            rf.in_pld += RingRsp.pack(opcode=7,  # Opcode_Comp
                                      src_id=s.node_id, tgt_id=bid[BIDW + TGTW - 1:BIDW], txn_id=bid[BIDW - 1:0],
                                      mdbid=0, dbid=0, resp=b.payload.bresp, user=b.payload.buser, ecc=0)
            tx_rsp += Stream(rf.out_vld, rf.out_rdy, data=rf.out_pld)

    return lwmnoc_tniu_write_channel()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    print('\n'.join(write_channel().generate(a.out)))
