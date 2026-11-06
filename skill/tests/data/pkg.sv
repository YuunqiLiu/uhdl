package my_pkg;
  localparam int unsigned N_ENT = 4;
  typedef struct packed { logic [3:0] id; logic [7:0] addr; } req_t;
endpackage
