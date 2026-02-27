package union_pkg;
    typedef struct packed {
        logic [3:0] x;
        logic [3:0] y;
    } point_t;

    typedef union packed {
        logic [7:0] byte_val;
        point_t     as_point;
    } my_union_t;
endpackage

module union_user (
    input  union_pkg::my_union_t  u_in,
    output union_pkg::my_union_t  u_out
);
assign u_out = u_in;
endmodule
