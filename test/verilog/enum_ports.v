package enum_pkg;
    typedef enum logic [1:0] {
        IDLE = 2'b00,
        RUN  = 2'b01,
        DONE = 2'b10,
        ERR  = 2'b11
    } state_t;

    typedef enum logic [2:0] {
        ADD = 3'd0,
        SUB = 3'd1,
        MUL = 3'd2,
        DIV = 3'd3,
        NOP = 3'd4
    } opcode_t;
endpackage

module enum_user (
    input  enum_pkg::state_t   state_in,
    output enum_pkg::state_t   state_out,
    input  enum_pkg::opcode_t  op_in,
    output enum_pkg::opcode_t  op_out
);
assign state_out = state_in;
assign op_out = op_in;
endmodule
