package nested_pkg;
    typedef struct packed {
        logic [3:0] x;
        logic [3:0] y;
    } point_t;

    typedef struct packed {
        point_t start_pt;
        point_t end_pt;
        logic [7:0] color;
    } line_t;
endpackage

module nested_struct_user (
    input  nested_pkg::line_t  line_in,
    output nested_pkg::line_t  line_out
);
assign line_out = line_in;
endmodule
