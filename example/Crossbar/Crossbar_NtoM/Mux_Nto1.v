module Mux_Nto1 (
	input            clk     ,
	input            rst_n   ,
	input            vld_src0,
	input            vld_src1,
	input            vld_src2,
	input            vld_src3,
	input      [3:0] pld_src0,
	input      [3:0] pld_src1,
	input      [3:0] pld_src2,
	input      [3:0] pld_src3,
	output           rdy_src0,
	output           rdy_src1,
	output           rdy_src2,
	output           rdy_src3,
	output           vld_dst ,
	output reg [3:0] pld_dst ,
	input            rdy_dst );
	reg  [3:0] priority    ;
	wire [3:0] pre_high    ;
	wire [3:0] pre_vld     ;
	wire [3:0] pre_high_vld;
	wire [3:0] pre_low_vld ;
	reg  [3:0] pre_priority;
	assign rdy_src0 = (priority[0:0] && rdy_dst);
	
	assign rdy_src1 = (priority[1:1] && rdy_dst);
	
	assign rdy_src2 = (priority[2:2] && rdy_dst);
	
	assign rdy_src3 = (priority[3:3] && rdy_dst);
	
	assign vld_dst = (|{vld_src0, vld_src1, vld_src2, vld_src3});
	
	always @(*) begin
	    case(priority)
	    4'b1 : pld_dst = pld_src0;
	    4'b10 : pld_dst = pld_src1;
	    4'b100 : pld_dst = pld_src2;
	    4'b1000 : pld_dst = pld_src3;
	    default : pld_dst = 4'b0;
	    endcase
	end
	
	always @(*) begin
	    if((|pre_high_vld)) priority = (((~pre_high_vld) + 4'b1)[3:0] & pre_high_vld);
	    else priority = (((~pre_high_vld) + 4'b1)[3:0] & pre_high_vld);
	end
	
	assign pre_high = (((~pre_priority) + 4'b1)[3:0] | pre_priority);
	
	assign pre_high_vld = (pre_high & {vld_src0, vld_src1, vld_src2, vld_src3});
	
	assign pre_low_vld = ((~pre_high) & {vld_src0, vld_src1, vld_src2, vld_src3});
	
	always @(posedge clk or negedge rst_n) begin
	    if(~rst_n) pre_priority <= 4'b0;
	    else pre_priority <= {priority[2:0], priority[3:3]};
	end
	

endmodule