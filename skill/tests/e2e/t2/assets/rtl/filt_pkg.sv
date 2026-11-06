package filt_pkg;
  localparam int unsigned TAG_W  = 4;
  localparam int unsigned DATA_W = 12;
  typedef struct packed {
    logic [TAG_W-1:0]  tag;
    logic [DATA_W-1:0] data;
  } entry_t;
endpackage
