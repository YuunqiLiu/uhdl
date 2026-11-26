"""lwmnoc_downstream_write_rob in UHDL: the TNIU downstream write ROB.

64 ROB entries (rob_entry.py) behind a ping-pong preallocator. DBID responses leave through
an age-ordered arbiter; AW requests through a locking age-ordered arbiter and a register
slice; accepted AWs are queued per sender bank (even / odd DBID) and in a global AW-order
FIFO for the W path. fcip / lwnoc IP is imported unchanged with VComponent.
"""
import os
from uhdl import *
from rob_entry import rob_entry, clog2
from lwmnoc_types import pk, PACK, MNOC

FCIP = '/workspace/lwnoc_dev/lwnoc/lwnoc_network_demo/subs/fcip/ip'
RING = '/workspace/lwnoc_dev/lwnoc/lwnoc_ring_network/de/rtl'
IP = {
    'fcip_age_matrix': [f'{FCIP}/arbiter/fcip_age_matrix.sv'],
    'fcip_arb_vrp_matrix': [f'{FCIP}/arbiter/fcip_arb_vrp_matrix.sv', f'{FCIP}/basic/fcip_real_mux_onehot.sv'],
    'lwring_lock_vrp_arb': PACK + [f'{MNOC}/niu_base/lwring_lock_vrp_arb.sv', f'{FCIP}/basic/fcip_real_mux_onehot.sv'],
    'fcip_reg_slice': [f'{FCIP}/regslice/fcip_reg_slice.sv'],
    'lwnoc_vrp_reg_fifo': [f'{MNOC}/common/lwnoc_vrp_reg_fifo.sv'],
    'lwmnoc_rob_pingpong_prealloc': [f'{RING}/lwmnoc_rob_pingpong_prealloc.sv'],
    'fcip_sync_fifo_spram': [f'{FCIP}/sync_fifo/fcip_sync_fifo_spram/fcip_sync_fifo_spram.sv',
                             f'{FCIP}/basic/fcip_real_mux_onehot.sv',
                             f'{FCIP}/stdcell_wrap/fcip_data_pipe.sv',
                             f'{FCIP}/stdcell_wrap/fcip_sync_arst.sv',
                             f'{FCIP}/sync_fifo/fcip_sync_fifo_spram/fcip_sfifo_spram_rob.sv',
                             f'{FCIP}/memory/fcip_mem_ctrl_wrap/fcip_mem_ctrl_wrap.sv',
                             f'{FCIP}/stdcell_wrap/fcip_marker.sv',
                             f'{FCIP}/ecc_codec/fcip_ecc_dec_dcls.sv',
                             f'{FCIP}/ecc_codec/fcip_ecc_dec.sv',
                             f'{FCIP}/basic/fcip_bin2onehot.sv',
                             f'{FCIP}/ecc_codec/fcip_ecc_enc.sv',
                             f'{FCIP}/sync_fifo/fcip_sync_fifo_spram/fcip_sfifo_spram_ctrl.sv',
                             f'{FCIP}/regslice/fcip_reg_slice.sv',
                             f'{FCIP}/sync_fifo/fcip_sync_fifo_spram/fcip_sfifo_spram_reg.sv',
                             f'{FCIP}/sync_fifo/fcip_sync_fifo_spram/fcip_sfifo_spram_ptr_ctrl.sv',
                             f'{FCIP}/arbiter/fcip_grant_gen_rr.sv'],
}
IP_FILES = list(dict.fromkeys(f for fs in IP.values() for f in fs))   # what a simulator needs besides our output


def ip(top, **params):
    """Import an SV module as a black box (types from lwmnoc_pack are visible)."""
    flist = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'uhdl_ip_%s.f' % top)
    with open(flist, 'w') as f:
        f.write('\n'.join(dict.fromkeys(PACK + IP[top])) + '\n')
    return VComponent(file=flist, top=top, slang_opts='--ignore-unknown-modules --single-unit', **params)


def axi_addr_range(addr, size, alen, burst, W=pk.AXI_ADDR_RANGE_CALC_WIDTH):
    """func_get_axi_addr_range of lwmnoc_pack: byte range [lower, upper] touched by a burst."""
    ext = lambda x: Cat(x, UInt(W - x.attribute.width, 0))
    a = ext(addr)
    xfer = UInt(W, 1) << size
    total = WrapAdd(ext(alen), 1) << size
    aligned = a & ~WrapSub(xfer, 1)
    wbase = a & ~WrapSub(total, 1)
    upper = Mux(burst, [WrapSub(WrapAdd(aligned, xfer), 1),           # FIXED
                        WrapSub(WrapAdd(aligned, total), 1),          # INCR
                        WrapSub(WrapAdd(wbase, total), 1),            # WRAP
                        WrapSub(WrapAdd(aligned, total), 1)])         # reserved: as INCR
    lower = If(burst.eq(2), wbase, a)
    return lower[W - 2:0], upper[W - 2:0]


def onehot2bin(oh):
    """fcip_onehot2bin: index of the highest set bit (0 if none)."""
    n = oh.attribute.width
    return Priority([(oh[i], i) for i in reversed(range(n))], 0)


def write_rob(N=pk.MNOC_TNIU_DNSTREAM_WRITE_ROB_ENTRY_NUM, XFER=pk.RING_MAX_TRANSFER_NUM):
    RingReq, RingRsp, RingDat, AddrRange = pk.ring_req_chnl, pk.ring_rsp_chnl, pk.ring_dat_chnl, pk.axi_addr_range_t
    EW, HALF = clog2(N), N // 2
    HW = clog2(HALF)

    class lwmnoc_downstream_write_rob(Component):
        MODULE_NAME = 'lwmnoc_downstream_write_rob'

        def circuit(s):
            s.clk, s.rst_n = Input(1), Input(1)
            s.domain(s.clk, s.rst_n)
            s.node_id = Input(4)
            rx_req = s.stream_in('rx_req', RingReq, data='pld')
            s.rx_dat_ack, s.rx_dat_pld = Input(1), Input(RingDat.width)
            tx_rsp = s.stream_out('tx_rsp', RingRsp, data='pld')
            aw = s.stream_out('axi_aw', RingReq, data='pld')
            s.axi_aw_entry_id = Output(EW)
            s.b_done_vld, s.b_done_entry_id = Input(1), Input(EW)
            s.sender_vld, s.sender_pld = Output(2), Output(2 * RingReq.width)
            s.sender_dbid, s.sender_rdy = Output(2 * EW), Input(2)
            s.sender_dat_done = Input(2 * HALF)
            aw_order = s.stream_out('aw_order', EW, data='dbid')

            # ---- IP blocks (imported SV)
            s.u_prealloc = ip('lwmnoc_rob_pingpong_prealloc', ROB_ENTRY_NUM=N)
            s.u_age = ip('fcip_age_matrix', WIDTH=N)
            s.u_arb_dbid = ip('fcip_arb_vrp_matrix', WIDTH=N, PLD_WIDTH=EW + RingReq.width)
            s.u_arb_req = ip('lwring_lock_vrp_arb', WIDTH=N, PLD_TYPE=SvType('lwmnoc_pack::ring_req_chnl'))
            s.u_rs = ip('fcip_reg_slice', RS_TYPE=0, PLD_TYPE=SvType('logic [%d:0]' % (RingReq.width + N - 1)))
            s.u_aw_order = ip('lwnoc_vrp_reg_fifo', ADDR_WIDTH=4, PLD_TYPE=SvType('logic [%d:0]' % (EW - 1)))
            fifo = [s.create(f'u_id_fifo_{i}', ip('lwnoc_vrp_reg_fifo', ADDR_WIDTH=4, PLD_TYPE=SvType('logic [%d:0]' % (HW - 1))))
                    for i in range(2)]
            pre, age, arb_d, arb_r, rs = s.u_prealloc, s.u_age, s.u_arb_dbid, s.u_arb_req, s.u_rs
            s.mark_unused(pre.out_pld, pre.out_pld_oh, arb_r.sel_lock)

            # ---- allocation
            rx_req.rdy += pre.out_vld
            pre.out_rdy += rx_req.vld
            age.alloc_en += pre.out_vld & rx_req.vld
            age.v_alloc += pre.v_in_rdy
            req = RingReq(rx_req.data)
            lower, upper = axi_addr_range(req.addr, req.size, req.burst_len, req.req_ext.axburst)
            rng = s.wire('rx_req_addr_range', AddrRange.pack(lower=lower, upper=upper))

            # ---- ROB entries
            dat = RingDat(s.rx_dat_pld)
            dat_ack = s.wire('v_rob_rx_dat_ack', If(s.rx_dat_ack, Cat([dat.dbid[EW - 1:0].eq(j) for j in range(N)]), 0), width=N)
            b_done = s.wire('v_rob_b_done', If(s.b_done_vld, Cat([s.b_done_entry_id.eq(j) for j in range(N)]), 0), width=N)
            ent = [s.create(f'u_rob_entry_{j}', rob_entry(N, XFER)) for j in range(N)]
            hzd = s.wire('v_rob_waw_hzd_flag', Cat([e.waw_hzd_flag for e in ent]))
            rel = s.wire('v_rob_entry_release', Cat([e.entry_release for e in ent]))
            for j, e in enumerate(ent):
                pre.v_in_vld[j] += e.prealloc_vld
                e.rx_req_ack += pre.v_in_rdy[j]
                e.rx_req_pld += rx_req.data
                e.rx_dat_ack += dat_ack[j]
                e.rx_dat_burst_id += dat.txn_id[clog2(XFER) - 1:0]
                e.waw_addr_range += rng
                e.waw_hzd_dep += hzd
                e.all_entry_release += rel
                e.b_done += b_done[j]
                # DBID responses: arbitrated oldest first, entry id travels with the payload
                arb_d.v_vld_s[j] += e.dbid_rsp_vld
                arb_d.v_pld_s[(j + 1) * (EW + RingReq.width) - 1:j * (EW + RingReq.width)] += Combine(UInt(EW, j), e.dbid_rsp_req_pld)
                e.dbid_rsp_rdy += arb_d.v_rdy_s[j]
                # AW requests: locking arbiter
                arb_r.v_vld_s[j] += e.axi_aw_vld
                arb_r.v_pld_s[(j + 1) * RingReq.width - 1:j * RingReq.width] += e.axi_aw_pld
                e.axi_aw_rdy += arb_r.v_rdy_s[j]
            arb_d.vv_matrix += age.vv_matrix
            arb_r.vv_matrix += age.vv_matrix

            # ---- DBID response
            tx_rsp.vld += arb_d.vld_m
            arb_d.rdy_m += tx_rsp.rdy
            won = RingReq(arb_d.pld_m[RingReq.width - 1:0])
            mdbid = arb_d.pld_m[EW + RingReq.width - 1:RingReq.width]
            tx_rsp.data += RingRsp.pack(opcode=5,  # Opcode_DBIDResp
                                        src_id=s.node_id, tgt_id=won.src_id, txn_id=won.txn_id,
                                        mdbid=won.mdbid, dbid=Cat(mdbid, UInt(1, 0)), resp=0, user=0, ecc=0)

            # ---- AW path: arbiter -> register slice -> AW, per-bank id FIFOs, AW-order FIFO
            rs.s_vld += arb_r.vld_m
            arb_r.rdy_m += rs.s_rdy
            rs.s_pld += Combine(arb_r.pld_m, arb_r.sel_onehot)
            bin_ = s.wire('align_aw_bin', onehot2bin(rs.m_pld[N - 1:0]), width=EW)
            sel_rdy = s.wire('sel_id_fifo_in_rdy', If(bin_[0], fifo[1].in_rdy, fifo[0].in_rdy))
            room = s.wire('aw_room', sel_rdy & s.u_aw_order.in_rdy)
            aw.vld += rs.m_vld & room
            rs.m_rdy += room & aw.rdy
            aw.data += rs.m_pld[RingReq.width + N - 1:N]
            s.axi_aw_entry_id += bin_
            s.u_aw_order.in_vld += aw.fire
            s.u_aw_order.in_pld += bin_
            aw_order += Stream(s.u_aw_order.out_vld, s.u_aw_order.out_rdy, data=s.u_aw_order.out_pld)

            # ---- two senders: bank i owns entries 2k+i
            for i, f in enumerate(fifo):
                bank = [ent[2 * k + i] for k in range(HALF)]
                f.in_vld += aw.fire & bin_[0].eq(i)
                f.in_pld += bin_[EW - 1:1]
                head = s.wire(f'head_sender_vld_{i}', f.out_vld & Mux(f.out_pld, [e.sender_vld for e in bank]))
                s.sender_vld[i] += head
                s.sender_pld[(i + 1) * RingReq.width - 1:i * RingReq.width] += Mux(f.out_pld, [e.sender_pld for e in bank])
                s.sender_dbid[(i + 1) * EW - 1:i * EW] += Cat(UInt(1, i), f.out_pld)
                pop = s.wire(f'id_fifo_out_rdy_{i}', head & s.sender_rdy[i])
                f.out_rdy += pop
                for k, e in enumerate(bank):
                    e.sender_rdy += f.out_pld.eq(k) & pop
                    e.sender_done += s.sender_dat_done[i * HALF + k]

    return lwmnoc_downstream_write_rob()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    print('\n'.join(write_rob().generate(a.out)))
