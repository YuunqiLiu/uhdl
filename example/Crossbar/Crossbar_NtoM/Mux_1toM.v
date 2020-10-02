module Mux_1toM (
	input            vld_src ,
	input      [3:0] pld_src ,
	output           rdy_src ,
	input            sel_src ,
	output           vld_dst0,
	output           vld_dst1,
	output reg [3:0] pld_dst0,
	output reg [3:0] pld_dst1,
	input            rdy_dst0,
	input            rdy_dst1);
	wire [1:0] vld_mask;
	wire [1:0] rdy_dst ;
	assign rdy_src = (|(vld_mask & rdy_dst));
	
	assign vld_dst0 = (vld_mask[0:0] && vld_src);
	
	assign vld_dst1 = (vld_mask[1:1] && vld_src);
	
	always @(*) begin
	    if(vld_mask[0:0]) pld_dst0 = pld_src;
	    else pld_dst0 = 4'b0;
	end
	
	always @(*) begin
	    if(vld_mask[1:1]) pld_dst1 = pld_src;
	    else pld_dst1 = 4'b0;
	end
	
	assign vld_mask = ({1'b0, vld_src} << sel_src);
	
	assign rdy_dst = {rdy_dst0, rdy_dst1};
	

endmodule