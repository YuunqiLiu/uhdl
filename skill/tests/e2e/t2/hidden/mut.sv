module tag_filter (input logic clk, input logic rst_n, input logic [3:0] match_tag,
  input logic in_vld, output logic in_rdy, input logic [15:0] in_pld,
  output logic out_vld, input logic out_rdy, output logic [11:0] out_data);
  logic fv; filt_pkg::entry_t fp; logic pop;
  sync_fifo #(.DEPTH(4)) u(.clk, .rst_n, .in_vld, .in_rdy, .in_pld, .out_vld(fv), .out_rdy(pop), .out_pld(fp));
  wire hit = fp.tag == match_tag;
  assign out_vld = fv && hit; assign out_data = fp.data; assign pop = out_rdy;
endmodule
