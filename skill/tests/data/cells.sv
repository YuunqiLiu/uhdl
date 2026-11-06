module sreg (input logic clk, input logic rst_n, input my_pkg::req_t i, output my_pkg::req_t o);
  always_ff @(posedge clk or negedge rst_n) if (!rst_n) o <= '0; else o <= i;
endmodule
module amux #(parameter int unsigned W = 4, parameter int unsigned N = 3) (
  input logic [W-1:0] din [N-1:0], input logic [$clog2(N)-1:0] sel, output logic [W-1:0] dout);
  assign dout = din[sel];
endmodule
