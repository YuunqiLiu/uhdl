module tb_eq; import lwmnoc_pack::*;
  localparam int N = MNOC_TNIU_DNSTREAM_WRITE_ROB_ENTRY_NUM, X = RING_MAX_TRANSFER_NUM;
  logic clk = 0, rst_n = 0;
  logic rx_req_ack, rx_dat_ack, dbid_rsp_rdy, axi_aw_rdy, sender_rdy, sender_done, b_done;
  ring_req_chnl rx_req_pld; logic [$clog2(X)-1:0] burst_id; axi_addr_range_t rng;
  logic [N-1:0] dep, allrel;
  // RTL
  logic a_pre, a_hzd, a_dv, a_awv, a_sv, a_rel; ring_req_chnl a_dp, a_awp, a_sp;
  lwmnoc_downstream_rob_entry R(.clk, .rst_n, .prealloc_vld(a_pre), .rx_req_ack, .rx_req_pld, .rx_dat_ack, .rx_dat_burst_id(burst_id),
    .waw_addr_range(rng), .waw_hzd_dep(dep), .all_entry_release(allrel), .waw_hzd_flag(a_hzd),
    .dbid_rsp_vld(a_dv), .dbid_rsp_req_pld(a_dp), .dbid_rsp_rdy, .axi_aw_vld(a_awv), .axi_aw_pld(a_awp), .axi_aw_rdy,
    .sender_vld(a_sv), .sender_pld(a_sp), .sender_rdy, .sender_done, .b_done, .entry_release(a_rel));
  // UHDL
  logic b_pre, b_hzd, b_dv, b_awv, b_sv, b_rel; logic [$bits(ring_req_chnl)-1:0] b_dp, b_awp, b_sp;
  rob_entry_uhdl U(.clk, .rst_n, .prealloc_vld(b_pre), .rx_req_ack, .rx_req_pld, .rx_dat_ack, .rx_dat_burst_id(burst_id),
    .waw_addr_range(rng), .waw_hzd_dep(dep), .all_entry_release(allrel), .waw_hzd_flag(b_hzd),
    .dbid_rsp_vld(b_dv), .dbid_rsp_req_pld(b_dp), .dbid_rsp_rdy, .axi_aw_vld(b_awv), .axi_aw_pld(b_awp), .axi_aw_rdy,
    .sender_vld(b_sv), .sender_pld(b_sp), .sender_rdy, .sender_done, .b_done, .entry_release(b_rel));
  always #5 clk = ~clk;
  int err = 0, cyc = 0, n_aw = 0, n_rel = 0, n_hzd = 0, n_req = 0;
  function automatic logic [39:0] small_addr(); return 40'($urandom % 64); endfunction
  task automatic drive();
    logic [39:0] lo, hi;
    rx_req_ack   = ($urandom % 6 == 0);
    rx_req_pld   = {$urandom, $urandom, $urandom, $urandom, $urandom};
    rx_dat_ack   = ($urandom % 2);  burst_id = $urandom;
    lo = small_addr(); hi = lo + ($urandom % 16); rng.lower = lo; rng.upper = hi;
    dep          = {$urandom, $urandom} & {$urandom, $urandom};
    allrel       = ($urandom % 3 == 0) ? {$urandom, $urandom} : '0;
    dbid_rsp_rdy = $urandom; axi_aw_rdy = $urandom; sender_rdy = $urandom;
    sender_done  = ($urandom % 8 == 0); b_done = ($urandom % 8 == 0);
  endtask
  initial begin
    drive(); #12 rst_n = 1;
    repeat (200000) begin
      @(negedge clk); cyc++;
      if ({a_pre, a_hzd, a_dv, a_awv, a_sv, a_rel} !== {b_pre, b_hzd, b_dv, b_awv, b_sv, b_rel} ||
          a_dp !== b_dp || a_awp !== b_awp || a_sp !== b_sp) begin
        err++; if (err < 5) $display("MISMATCH cyc=%0d rtl=%b uhdl=%b", cyc, {a_pre,a_hzd,a_dv,a_awv,a_sv,a_rel}, {b_pre,b_hzd,b_dv,b_awv,b_sv,b_rel});
      end
      n_aw += a_awv & axi_aw_rdy; n_rel += a_rel; n_hzd += a_hzd; n_req += rx_req_ack;
      drive();
      if ($urandom % 20000 == 0) begin rst_n = 0; @(negedge clk); rst_n = 1; end
    end
    $display("RESULT %s errors=%0d cycles=%0d aw_sent=%0d releases=%0d hzd_cycles=%0d req_acks=%0d", err == 0 ? "PASS" : "FAIL", err, cyc, n_aw, n_rel, n_hzd, n_req);
    $finish;
  end
endmodule
