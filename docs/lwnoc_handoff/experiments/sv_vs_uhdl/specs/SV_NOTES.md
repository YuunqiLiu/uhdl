# SV environment notes (Verilator 5.044 / Yosys 0.51)

- **Yosys 0.51's built-in SV reader** has limits inside functions:
  - It rejects `return`. Assign to the function name instead (`f = ...;`).
  - It rejects a declaration with an initializer, such as `int x = 0;`.
  - It rejects `return (c) ? '0 : x;`.
- **Testbench race:** with `verilator --binary --timing`, a TB that changes inputs in the same time step as `@(posedge clk)` races with the DUT. Change inputs at negedge, or put `#1` after posedge.
- **Unused signals:** for ports the spec requires but the module never uses (for example clk in a combinational module), wrap them in `/* verilator lint_off UNUSEDSIGNAL */ ... /* verilator lint_on UNUSEDSIGNAL */`.
- **Checks:** use `verilator --lint-only -Wall` for lint, and `yosys -p "read_verilog -sv f.sv; hierarchy -top X -chparam N 4; synth"` for synthesis.
