module adder (
    input [31:0] din1,
    input [31:0] din2,
    output [32:0] dout
);

    assign dout = din1 + din2;

endmodule