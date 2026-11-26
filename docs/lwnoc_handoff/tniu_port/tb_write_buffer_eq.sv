// Closed-loop equivalence test: lwmnoc_downstream_write_buffer (RTL) vs write_buffer_uhdl.
// One traffic model (write requests, data beats after each DBID response, two-bank data SRAM
// with random latency, B completions after each W tail) is driven by the RTL outputs and fed
// to both designs; every output of both is compared on every cycle.
module tb_eq; import lwmnoc_pack::*;
  localparam int AW = TNIU_WR_DATA_ADDR_WIDTH, SB = TNIU_WR_DATA_SB_WIDTH, DW = $bits(ring_dat_chnl);
  logic clk = 0, rst_n = 0;
  always #5 clk = ~clk;
  // ---------------- shared inputs
  logic [3:0] node_id = 4'd3;
  logic rx_req_vld = 0, rx_dat_vld = 0, tx_rsp_rdy = 0, axi_aw_rdy = 0, axi_w_rdy = 0, b_done_vld = 0;
  ring_req_chnl rx_req_pld = '0; ring_dat_chnl rx_dat_pld = '0; logic [5:0] b_done_entry_id = '0;
  logic [1:0] wr_rdy = 0, rd_rdy = 0, rsp_vld = 0;
  logic [1:0][DW-1:0] rsp_data = '0; logic [1:0][SB-1:0] rsp_sb = '0;
  // ---------------- RTL
  logic a_rx_req_rdy, a_rx_dat_rdy, a_tx_rsp_vld, a_aw_vld, a_w_vld; ring_rsp_chnl a_tx_rsp_pld;
  tniu_axi_aw_chnl a_aw_pld; tniu_axi_w_chnl a_w_pld;
  logic [1:0] a_wr_vld, a_rd_vld, a_rsp_rdy; logic [1:0][AW-1:0] a_wr_addr, a_rd_addr;
  logic [1:0][DW-1:0] a_wr_data, a_wr_ben; logic [1:0][SB-1:0] a_rd_sb;
  lwmnoc_downstream_write_buffer R(.clk, .rst_n, .node_id, .rx_req_vld, .rx_req_rdy(a_rx_req_rdy), .rx_req_pld,
    .rx_dat_vld, .rx_dat_rdy(a_rx_dat_rdy), .rx_dat_pld, .tx_rsp_vld(a_tx_rsp_vld), .tx_rsp_rdy, .tx_rsp_pld(a_tx_rsp_pld),
    .axi_aw_vld(a_aw_vld), .axi_aw_pld(a_aw_pld), .axi_aw_rdy, .b_done_vld, .b_done_entry_id,
    .axi_w_vld(a_w_vld), .axi_w_pld(a_w_pld), .axi_w_rdy,
    .data_ram_write_req_vld(a_wr_vld), .data_ram_write_req_rdy(wr_rdy), .data_ram_write_req_addr(a_wr_addr),
    .data_ram_write_req_data(a_wr_data), .data_ram_write_req_bit_en(a_wr_ben),
    .data_ram_read_req_vld(a_rd_vld), .data_ram_read_req_rdy(rd_rdy), .data_ram_read_req_addr(a_rd_addr),
    .data_ram_read_req_sideband(a_rd_sb), .data_ram_read_resp_vld(rsp_vld), .data_ram_read_resp_data(rsp_data),
    .data_ram_read_resp_sideband(rsp_sb), .data_ram_read_resp_rdy(a_rsp_rdy));
  // ---------------- UHDL
  logic b_rx_req_rdy, b_rx_dat_rdy, b_tx_rsp_vld, b_aw_vld, b_w_vld; logic [$bits(ring_rsp_chnl)-1:0] b_tx_rsp_pld;
  logic [$bits(tniu_axi_aw_chnl)-1:0] b_aw_pld; logic [$bits(tniu_axi_w_chnl)-1:0] b_w_pld;
  logic [1:0] b_wr_vld, b_rd_vld, b_rsp_rdy; logic [2*AW-1:0] b_wr_addr, b_rd_addr;
  logic [2*DW-1:0] b_wr_data, b_wr_ben; logic [2*SB-1:0] b_rd_sb;
  write_buffer_uhdl U(.clk, .rst_n, .node_id, .rx_req_vld, .rx_req_rdy(b_rx_req_rdy), .rx_req_pld,
    .rx_dat_vld, .rx_dat_rdy(b_rx_dat_rdy), .rx_dat_pld, .tx_rsp_vld(b_tx_rsp_vld), .tx_rsp_rdy, .tx_rsp_pld(b_tx_rsp_pld),
    .axi_aw_vld(b_aw_vld), .axi_aw_pld(b_aw_pld), .axi_aw_rdy, .b_done_vld, .b_done_entry_id,
    .axi_w_vld(b_w_vld), .axi_w_pld(b_w_pld), .axi_w_rdy,
    .data_ram_write_req_vld(b_wr_vld), .data_ram_write_req_rdy(wr_rdy), .data_ram_write_req_addr(b_wr_addr),
    .data_ram_write_req_data(b_wr_data), .data_ram_write_req_bit_en(b_wr_ben),
    .data_ram_read_req_vld(b_rd_vld), .data_ram_read_req_rdy(rd_rdy), .data_ram_read_req_addr(b_rd_addr),
    .data_ram_read_req_sideband(b_rd_sb), .data_ram_read_resp_vld(rsp_vld), .data_ram_read_resp_data(rsp_data),
    .data_ram_read_resp_sideband(rsp_sb), .data_ram_read_resp_rdy(b_rsp_rdy));

  // ---------------- traffic model state
  logic [DW-1:0] mem [2][256];
  int burst_of [1024];                         // txn_id -> burst_len
  int dq_dbid [$], dq_txn [$], dq_beat [$], dq_len [$];   // data beats to send
  int aw_q [$];                                // entry ids in AW order, popped on W tail
  int b_q_id [$], b_q_t [$];                   // scheduled B completions
  // SRAM read pipes, one per bank (separate queues: Verilator mishandles arrays of queues)
  logic [DW-1:0] p0_data [$], p1_data [$]; logic [SB-1:0] p0_sb [$], p1_sb [$]; int p0_t [$], p1_t [$];
  int err = 0, cyc = 0, n_req = 0, n_dat = 0, n_rsp = 0, n_aw = 0, n_w = 0, n_wlast = 0, n_b = 0, txn = 0;

  function automatic bit outs_differ();
    return {a_rx_req_rdy, a_rx_dat_rdy, a_tx_rsp_vld, a_aw_vld, a_w_vld, a_wr_vld, a_rd_vld, a_rsp_rdy} !==
           {b_rx_req_rdy, b_rx_dat_rdy, b_tx_rsp_vld, b_aw_vld, b_w_vld, b_wr_vld, b_rd_vld, b_rsp_rdy} ||
           a_tx_rsp_pld !== b_tx_rsp_pld || a_aw_pld !== b_aw_pld || a_w_pld !== b_w_pld ||
           a_wr_addr !== b_wr_addr || a_wr_data !== b_wr_data || a_wr_ben !== b_wr_ben ||
           a_rd_addr !== b_rd_addr || a_rd_sb !== b_rd_sb;
  endfunction

  task automatic reset_model();
    dq_dbid.delete(); dq_txn.delete(); dq_beat.delete(); dq_len.delete(); aw_q.delete(); b_q_id.delete(); b_q_t.delete();
    p0_data.delete(); p0_sb.delete(); p0_t.delete(); p1_data.delete(); p1_sb.delete(); p1_t.delete();
    rx_req_vld = 0; rx_dat_vld = 0; b_done_vld = 0;
  endtask

  // Inputs change at the falling edge; just before each rising edge (#4) the outputs are compared and
  // the transfers that the coming edge will make are recorded; they take effect at the next falling edge.
  bit hs_req, hs_dat, hs_rsp, hs_aw, hs_w; ring_rsp_chnl s_rsp; tniu_axi_aw_chnl s_aw; tniu_axi_w_chnl s_w;
  logic [1:0] hs_wr, hs_rd, hs_rp; logic [1:0][AW-1:0] s_wra, s_rda; logic [1:0][DW-1:0] s_wrd; logic [1:0][SB-1:0] s_rdsb;

  always @(negedge clk) if (rst_n) begin
    automatic int phase = (cyc / 25000) % 2;          // 0: few address conflicts, 1: many
    // ---- apply the transfers of the last rising edge
    if (hs_req) rx_req_vld = 0;
    if (hs_dat) begin rx_dat_vld = 0; void'(dq_dbid.pop_front()); void'(dq_txn.pop_front()); void'(dq_beat.pop_front()); void'(dq_len.pop_front()); end
    if (hs_rsp)
      for (int k = 0; k <= burst_of[s_rsp.txn_id]; k++) begin
        dq_dbid.push_back(s_rsp.dbid); dq_txn.push_back(s_rsp.txn_id); dq_beat.push_back(k); dq_len.push_back(burst_of[s_rsp.txn_id]);
      end
    if (hs_aw) aw_q.push_back(s_aw.awid[19:14]);
    if (hs_w && s_w.wlast && aw_q.size()) begin b_q_id.push_back(aw_q.pop_front()); b_q_t.push_back(cyc + 2 + $urandom % 20); end
    if (b_done_vld) b_done_vld = 0;                    // a B completion is a one-cycle pulse
    for (int b = 0; b < 2; b++) if (hs_wr[b]) mem[b][s_wra[b]] = s_wrd[b];
    if (hs_rd[0]) begin p0_data.push_back(mem[0][s_rda[0]]); p0_sb.push_back(s_rdsb[0]); p0_t.push_back(cyc + 1 + $urandom % 3); end
    if (hs_rd[1]) begin p1_data.push_back(mem[1][s_rda[1]]); p1_sb.push_back(s_rdsb[1]); p1_t.push_back(cyc + 1 + $urandom % 3); end
    if (hs_rp[0]) begin void'(p0_data.pop_front()); void'(p0_sb.pop_front()); void'(p0_t.pop_front()); end
    if (hs_rp[1]) begin void'(p1_data.pop_front()); void'(p1_sb.pop_front()); void'(p1_t.pop_front()); end
    // ---- drive the next cycle
    if (!rx_req_vld && $urandom % 3 == 0) begin
      rx_req_pld = {$urandom, $urandom, $urandom, $urandom, $urandom};
      rx_req_pld.txn_id = 10'(txn); burst_of[txn] = rx_req_pld.burst_len; txn = (txn + 1) % 1024;
      rx_req_pld.addr = phase ? 40'($urandom % 256) : 40'({$urandom, $urandom} & 40'hFFFFFFFF);
      rx_req_pld.size = $urandom % 7;
      rx_req_vld = 1;
    end
    if (!rx_dat_vld && dq_dbid.size() && $urandom % 4 != 0) begin
      rx_dat_pld = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                    $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
      rx_dat_pld.dbid = 7'(dq_dbid[0]); rx_dat_pld.txn_id = 10'(dq_beat[0]); rx_dat_pld.tail = (dq_beat[0] == dq_len[0]);
      rx_dat_vld = 1;
    end
    if (b_q_t.size() && b_q_t[0] <= cyc) begin b_done_vld = 1; b_done_entry_id = 6'(b_q_id.pop_front()); void'(b_q_t.pop_front()); end
    tx_rsp_rdy = ($urandom % 4 != 0); axi_aw_rdy = ($urandom % 4 != 0); axi_w_rdy = ($urandom % 4 != 0);
    wr_rdy = $urandom; rd_rdy = $urandom;
    rsp_vld[0] = p0_t.size() && p0_t[0] <= cyc; rsp_data[0] = p0_data.size() ? p0_data[0] : '0; rsp_sb[0] = p0_sb.size() ? p0_sb[0] : '0;
    rsp_vld[1] = p1_t.size() && p1_t[0] <= cyc; rsp_data[1] = p1_data.size() ? p1_data[0] : '0; rsp_sb[1] = p1_sb.size() ? p1_sb[0] : '0;
    // ---- just before the rising edge: compare, and record what this edge transfers
    #4;
    cyc++;
    if (outs_differ()) begin
      err++; if (err < 5) $display("MISMATCH cyc=%0d ctl rtl=%b uhdl=%b aw=%0d w=%0d rsp=%0d rdaddr=%0d rdsb=%0d", cyc,
        {a_rx_req_rdy, a_rx_dat_rdy, a_tx_rsp_vld, a_aw_vld, a_w_vld, a_wr_vld, a_rd_vld, a_rsp_rdy},
        {b_rx_req_rdy, b_rx_dat_rdy, b_tx_rsp_vld, b_aw_vld, b_w_vld, b_wr_vld, b_rd_vld, b_rsp_rdy},
        a_aw_pld !== b_aw_pld, a_w_pld !== b_w_pld, a_tx_rsp_pld !== b_tx_rsp_pld, a_rd_addr !== b_rd_addr, a_rd_sb !== b_rd_sb);
    end
    hs_req = rx_req_vld && a_rx_req_rdy;   n_req += hs_req;
    hs_dat = rx_dat_vld && a_rx_dat_rdy;   n_dat += hs_dat;
    hs_rsp = a_tx_rsp_vld && tx_rsp_rdy;   n_rsp += hs_rsp; s_rsp = a_tx_rsp_pld;
    hs_aw  = a_aw_vld && axi_aw_rdy;       n_aw  += hs_aw;  s_aw  = a_aw_pld;
    hs_w   = a_w_vld && axi_w_rdy;         n_w   += hs_w;   s_w   = a_w_pld; n_wlast += hs_w && a_w_pld.wlast;
    n_b   += b_done_vld;
    hs_wr  = a_wr_vld & wr_rdy; s_wra = a_wr_addr; s_wrd = a_wr_data;
    hs_rd  = a_rd_vld & rd_rdy; s_rda = a_rd_addr; s_rdsb = a_rd_sb;
    hs_rp  = rsp_vld & a_rsp_rdy;
  end

  initial begin
    reset_model(); hs_req = 0; hs_dat = 0; hs_rsp = 0; hs_aw = 0; hs_w = 0; hs_wr = 0; hs_rd = 0; hs_rp = 0;
    #12 rst_n = 1;
    repeat (100000) @(posedge clk);
    $display("RESULT %s errors=%0d cycles=%0d req=%0d dbid_rsp=%0d data_beats=%0d aw=%0d w_beats=%0d w_tx=%0d b=%0d",
             err == 0 ? "PASS" : "FAIL", err, cyc, n_req, n_rsp, n_dat, n_aw, n_w, n_wlast, n_b);
    $finish;
  end
endmodule
