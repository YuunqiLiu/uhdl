// Small synchronous FIFO for filt_pkg::entry_t. Do not modify.
module sync_fifo #(parameter int unsigned DEPTH = 4) (
  input  logic              clk,
  input  logic              rst_n,
  input  logic              in_vld,
  output logic              in_rdy,
  input  filt_pkg::entry_t  in_pld,
  output logic              out_vld,
  input  logic              out_rdy,
  output filt_pkg::entry_t  out_pld
);
  localparam int unsigned AW = $clog2(DEPTH);
  filt_pkg::entry_t mem [DEPTH];
  logic [AW:0] wp, rp;
  assign in_rdy  = (wp - rp) != (AW+1)'(DEPTH);
  assign out_vld = wp != rp;
  assign out_pld = mem[rp[AW-1:0]];
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin wp <= '0; rp <= '0; end
    else begin
      if (in_vld && in_rdy) begin mem[wp[AW-1:0]] <= in_pld; wp <= wp + 1'b1; end
      if (out_vld && out_rdy) rp <= rp + 1'b1;
    end
endmodule
