# SV environment notes (Verilator 5.044 / Yosys 0.51)

- **Yosys 0.51's built-in SV reader** has limits inside functions:
  - It rejects `return`. Assign to the function name instead (`f = ...;`).
  - It rejects a declaration with an initializer, such as `int x = 0;`.
- **Testbench race:** with `verilator --binary --timing`, a TB that changes inputs in the same time step as `@(posedge clk)` races with the DUT. Change inputs at negedge, or put `#1` after posedge.
