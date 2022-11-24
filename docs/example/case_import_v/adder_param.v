

module adder_param #(
    parameter WIDTH = 32
)(
    input [WIDTH-1:0] din1,
    input [WIDTH-1:0] din2,
    output [WIDTH:0] dout
);

    assign dout = din1 + din2;

endmodule