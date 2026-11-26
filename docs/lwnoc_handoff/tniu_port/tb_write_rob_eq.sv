module tb_eq; import lwmnoc_pack::*;
  localparam int N = 64, EW = 6, HALF = 32, RW = $bits(ring_req_chnl);
  logic clk = 0, rst_n = 0;
  logic [3:0] node_id; logic rx_req_vld, rx_dat_ack, tx_rsp_rdy, axi_aw_rdy, b_done_vld, aw_order_rdy;
  ring_req_chnl rx_req_pld; ring_dat_chnl rx_dat_pld; logic [EW-1:0] b_done_entry_id; logic [1:0] sender_rdy;
  logic [HALF-1:0] dat_done [1:0];
  // RTL
  logic a_rdy, a_tv, a_awv, a_aov; ring_rsp_chnl a_tp; ring_req_chnl a_awp; logic [EW-1:0] a_awid, a_aod;
  logic [1:0] a_sv; ring_req_chnl a_sp [1:0]; logic [EW-1:0] a_sd [1:0];
  lwmnoc_downstream_write_rob R(.clk, .rst_n, .node_id, .rx_req_vld, .rx_req_rdy(a_rdy), .rx_req_pld, .rx_dat_ack, .rx_dat_pld,
    .tx_rsp_vld(a_tv), .tx_rsp_rdy, .tx_rsp_pld(a_tp), .axi_aw_vld(a_awv), .axi_aw_rdy, .axi_aw_pld(a_awp), .axi_aw_entry_id(a_awid),
    .b_done_vld, .b_done_entry_id, .sender_vld(a_sv), .sender_pld(a_sp), .sender_dbid(a_sd), .sender_rdy, .sender_dat_done(dat_done),
    .aw_order_vld(a_aov), .aw_order_rdy, .aw_order_dbid(a_aod));
  // UHDL
  logic b_rdy, b_tv, b_awv, b_aov; logic [$bits(ring_rsp_chnl)-1:0] b_tp; logic [RW-1:0] b_awp; logic [EW-1:0] b_awid, b_aod;
  logic [1:0] b_sv; logic [2*RW-1:0] b_sp; logic [2*EW-1:0] b_sd;
  write_rob_uhdl U(.clk, .rst_n, .node_id, .rx_req_vld, .rx_req_rdy(b_rdy), .rx_req_pld, .rx_dat_ack, .rx_dat_pld,
    .tx_rsp_vld(b_tv), .tx_rsp_rdy, .tx_rsp_pld(b_tp), .axi_aw_vld(b_awv), .axi_aw_rdy, .axi_aw_pld(b_awp), .axi_aw_entry_id(b_awid),
    .b_done_vld, .b_done_entry_id, .sender_vld(b_sv), .sender_pld(b_sp), .sender_dbid(b_sd), .sender_rdy, .sender_dat_done({dat_done[1], dat_done[0]}),
    .aw_order_vld(b_aov), .aw_order_rdy, .aw_order_dbid(b_aod));
  always #5 clk = ~clk;
  int err = 0, cyc = 0, n_req = 0, n_dbid = 0, n_aw = 0, n_snd = 0, n_ord = 0;
  task automatic drive();
    node_id = $urandom;
    rx_req_vld = ($urandom % 3 == 0);
    rx_req_pld = {$urandom, $urandom, $urandom, $urandom, $urandom};
    rx_req_pld.addr = ((cyc / 20000) % 2) ? 40'({$urandom, $urandom} & 40'hFFFFFF) : 40'($urandom % 512); rx_req_pld.size = $urandom % 7;
    rx_dat_ack = ($urandom % 2); rx_dat_pld = '0; rx_dat_pld.dbid = $urandom; rx_dat_pld.txn_id = $urandom;
    tx_rsp_rdy = ($urandom % 4 != 0); axi_aw_rdy = ($urandom % 4 != 0); aw_order_rdy = ($urandom % 3 != 0);
    b_done_vld = ((cyc / 20000) % 2) ? ($urandom % 60 == 0) : ($urandom % 3 == 0); b_done_entry_id = $urandom;
    sender_rdy = $urandom;
    dat_done[0] = ($urandom % (((cyc / 20000) % 2) ? 60 : 3) == 0) ? (32'b1 << ($urandom % 32)) : '0;
    dat_done[1] = ($urandom % (((cyc / 20000) % 2) ? 60 : 3) == 0) ? (32'b1 << ($urandom % 32)) : '0;
  endtask
  initial begin
    drive(); #12 rst_n = 1;
    repeat (200000) begin
      @(negedge clk); cyc++;
      if ({a_rdy, a_tv, a_awv, a_aov, a_sv} !== {b_rdy, b_tv, b_awv, b_aov, b_sv} || a_tp !== b_tp || a_awp !== b_awp ||
          a_awid !== b_awid || a_aod !== b_aod || a_sp[0] !== b_sp[RW-1:0] || a_sp[1] !== b_sp[2*RW-1:RW] ||
          a_sd[0] !== b_sd[EW-1:0] || a_sd[1] !== b_sd[2*EW-1:EW]) begin
        err++; if (err < 5) $display("MISMATCH cyc=%0d ctl rtl=%b uhdl=%b tp=%0d awp=%0d awid=%0d/%0d sd=%0d/%0d", cyc,
          {a_rdy,a_tv,a_awv,a_aov,a_sv}, {b_rdy,b_tv,b_awv,b_aov,b_sv}, a_tp !== b_tp, a_awp !== b_awp, a_awid, b_awid, a_sd[0], b_sd[EW-1:0]);
      end
      n_req += rx_req_vld & a_rdy; n_dbid += a_tv & tx_rsp_rdy; n_aw += a_awv & axi_aw_rdy; n_snd += $countones(a_sv & sender_rdy); n_ord += a_aov & aw_order_rdy;
      drive();
      if ($urandom % 25000 == 0) begin rst_n = 0; @(negedge clk); rst_n = 1; end
    end
    $display("RESULT %s errors=%0d cycles=%0d req=%0d dbid_rsp=%0d aw=%0d sender=%0d aw_order=%0d", err == 0 ? "PASS" : "FAIL", err, cyc, n_req, n_dbid, n_aw, n_snd, n_ord);
    $finish;
  end
endmodule
