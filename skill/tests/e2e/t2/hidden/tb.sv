// Reference: the same sync_fifo plus the filter written in SV; compares the DUT every cycle.
module tb;
  logic clk = 0, rst_n = 0, in_vld = 0, out_rdy = 0; logic [3:0] match_tag = 0; filt_pkg::entry_t in_pld = '0;
  wire d_in_rdy, d_out_vld; wire [11:0] d_out_data;
  tag_filter dut(.clk, .rst_n, .match_tag, .in_vld, .in_rdy(d_in_rdy), .in_pld, .out_vld(d_out_vld), .out_rdy, .out_data(d_out_data));
  logic f_out_vld, f_in_rdy, r_pop; filt_pkg::entry_t f_out_pld;
  sync_fifo #(.DEPTH(4)) ref_fifo(.clk, .rst_n, .in_vld, .in_rdy(f_in_rdy), .in_pld, .out_vld(f_out_vld), .out_rdy(r_pop), .out_pld(f_out_pld));
  wire hit = f_out_pld.tag == match_tag;
  wire r_out_vld = f_out_vld && hit;
  assign r_pop = hit ? out_rdy : 1'b1;
  int err = 0, n_in = 0, n_out = 0, n_drop = 0;
  always #5 clk = ~clk;
  initial begin
    #12 rst_n = 1;
    for (int c = 0; c < 5000; c++) begin
      @(negedge clk);
      if (!in_vld || f_in_rdy) begin in_vld = $urandom % 3 != 0; in_pld.tag = $urandom % 3; in_pld.data = $urandom; end
      out_rdy = $urandom % 4 != 0;
      if ($urandom % 200 == 0) match_tag = $urandom % 3;
      #1;
      if (d_in_rdy !== f_in_rdy || d_out_vld !== r_out_vld || (r_out_vld && d_out_data !== f_out_pld.data)) begin
        err++; if (err < 5) $display("MISMATCH c=%0d in_rdy %b/%b out_vld %b/%b data %h/%h", c, d_in_rdy, f_in_rdy, d_out_vld, r_out_vld, d_out_data, f_out_pld.data);
      end
      n_in += in_vld && f_in_rdy; n_out += r_out_vld && out_rdy; n_drop += f_out_vld && !hit;
    end
    $display("RESULT %s errors=%0d in=%0d out=%0d dropped=%0d", err == 0 ? "PASS" : "FAIL", err, n_in, n_out, n_drop);
    $finish;
  end
endmodule
