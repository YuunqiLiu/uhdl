module rr_arb (input logic clk, input logic rst_n, input logic [3:0] req, input logic hold, output logic [3:0] gnt);
  logic [1:0] ptr; logic [3:0] last;
  always_comb begin
    gnt = 0;
    if (hold) gnt = last;
    else for (int k = 3; k >= 0; k--) if (req[(ptr + k) % 4]) gnt = 4'b1 << ((ptr + k) % 4);
  end
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin ptr <= 0; last <= 0; end
    else if (gnt != 0) begin last <= gnt; for (int k = 0; k < 4; k++) if (gnt[k]) ptr <= 2'((k + 1) % 4); end
endmodule
