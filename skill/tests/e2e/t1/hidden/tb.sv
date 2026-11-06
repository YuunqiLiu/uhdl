module tb;
  logic clk = 0, rst_n = 0, hold = 0; logic [3:0] req = 0; wire [3:0] gnt;
  rr_arb dut(.clk, .rst_n, .req, .hold, .gnt);
  logic [1:0] ptr; logic [3:0] last, exp_g; int err = 0, ngnt = 0, nhold = 0;
  always #5 clk = ~clk;
  function automatic logic [3:0] model(input logic [3:0] r, input logic h, input logic [1:0] p, input logic [3:0] l);
    if (h && (l & r) != 0) return l;
    for (int k = 0; k < 4; k++) if (r[(p + k) % 4]) return 4'b1 << ((p + k) % 4);
    return 0;
  endfunction
  initial begin
    ptr = 0; last = 0;
    #12 rst_n = 1;
    for (int c = 0; c < 4000; c++) begin
      @(negedge clk); req = $urandom; hold = ($urandom % 3 == 0);
      #1 exp_g = model(req, hold, ptr, last);
      if (gnt !== exp_g) begin err++; if (err < 5) $display("MISMATCH c=%0d req=%b hold=%b ptr=%0d last=%b gnt=%b exp=%b", c, req, hold, ptr, last, gnt, exp_g); end
      if (hold && (last & req) != 0) nhold++;
      @(posedge clk);
      if (exp_g != 0) begin ngnt++; last = exp_g; for (int k = 0; k < 4; k++) if (exp_g[k]) ptr = (k + 1) % 4; end
    end
    $display("RESULT %s errors=%0d grants=%0d held=%0d", err == 0 ? "PASS" : "FAIL", err, ngnt, nhold);
    $finish;
  end
endmodule
