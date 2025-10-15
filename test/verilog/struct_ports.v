package mypkg;
    typedef struct packed {
        logic [3:0] a;
        logic signed [7:0] b;
        logic c;
    } my_struct_t;
endpackage

module struct_user (
    input  mypkg::my_struct_t  s_in,
    output mypkg::my_struct_t  s_out
);
assign s_out = s_in;
endmodule
