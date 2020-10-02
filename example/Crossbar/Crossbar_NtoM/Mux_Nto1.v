module Mux_Nto1 (
	input            clk     ,
	input            rst_n   ,
	input            vld_src0,
	input            vld_src1,
	input            vld_src2,
	input      [3:0] pld_src0,
	input      [3:0] pld_src1,
	input      [3:0] pld_src2,
	output           rdy_src0,
	output           rdy_src1,
	output           rdy_src2,
	output           vld_dst ,
	output reg [3:0] pld_dst ,
	input            rdy_dst );
	wire [2:0] priority;
	assign rdy_src0 = (priority[0:0] && rdy_dst);
	
	assign rdy_src1 = (priority[1:1] && rdy_dst);
	
	assign rdy_src2 = (priority[2:2] && rdy_dst);
	
	assign vld_dst = (|{vld_src0, vld_src1, vld_src2});
	
	always @(*) begin
	    case(priority)
	    3'b1 : pld_dst = pld_src0;
	    3'b10 : pld_dst = pld_src1;
	    3'b100 : pld_dst = pld_src2;
	    default : pld_dst = 4'b0;
	    endcase
	end
	
	assign priority = (((~{vld_src0, vld_src1, vld_src2}) + 3'b1)[2:0] & {vld_src0, vld_src1, vld_src2});
	

endmodule