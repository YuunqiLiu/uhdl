module adder_param #(
    parameter WIDTH = 32,
    parameter DEPTH = 10
)(
    input [WIDTH-1:0] din1,
    input [WIDTH-1:0] din2,
    input [DEPTH-1:0] din3,
    output [WIDTH:0] dout
);

    assign dout = din1 + din2;

endmodule