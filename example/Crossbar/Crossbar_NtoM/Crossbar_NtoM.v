module Crossbar_NtoM (
	input        clk     ,
	input        rst_n   ,
	input        vld_src0,
	input        vld_src1,
	input        vld_src2,
	input        vld_src3,
	input  [3:0] pld_src0,
	input  [3:0] pld_src1,
	input  [3:0] pld_src2,
	input  [3:0] pld_src3,
	output       rdy_src0,
	output       rdy_src1,
	output       rdy_src2,
	output       rdy_src3,
	input        sel_src0,
	input        sel_src1,
	input        sel_src2,
	input        sel_src3,
	output       vld_dst0,
	output       vld_dst1,
	output [3:0] pld_dst0,
	output [3:0] pld_dst1,
	input        rdy_dst0,
	input        rdy_dst1);
	wire       inst_Mux_1toM_0_vld_src ;
	wire [3:0] inst_Mux_1toM_0_pld_src ;
	wire       inst_Mux_1toM_0_rdy_src ;
	wire       inst_Mux_1toM_0_sel_src ;
	wire       inst_Mux_1toM_0_vld_dst0;
	wire       inst_Mux_1toM_0_vld_dst1;
	wire [3:0] inst_Mux_1toM_0_pld_dst0;
	wire [3:0] inst_Mux_1toM_0_pld_dst1;
	wire       inst_Mux_1toM_0_rdy_dst0;
	wire       inst_Mux_1toM_0_rdy_dst1;
	wire       inst_Mux_1toM_1_vld_src ;
	wire [3:0] inst_Mux_1toM_1_pld_src ;
	wire       inst_Mux_1toM_1_rdy_src ;
	wire       inst_Mux_1toM_1_sel_src ;
	wire       inst_Mux_1toM_1_vld_dst0;
	wire       inst_Mux_1toM_1_vld_dst1;
	wire [3:0] inst_Mux_1toM_1_pld_dst0;
	wire [3:0] inst_Mux_1toM_1_pld_dst1;
	wire       inst_Mux_1toM_1_rdy_dst0;
	wire       inst_Mux_1toM_1_rdy_dst1;
	wire       inst_Mux_1toM_2_vld_src ;
	wire [3:0] inst_Mux_1toM_2_pld_src ;
	wire       inst_Mux_1toM_2_rdy_src ;
	wire       inst_Mux_1toM_2_sel_src ;
	wire       inst_Mux_1toM_2_vld_dst0;
	wire       inst_Mux_1toM_2_vld_dst1;
	wire [3:0] inst_Mux_1toM_2_pld_dst0;
	wire [3:0] inst_Mux_1toM_2_pld_dst1;
	wire       inst_Mux_1toM_2_rdy_dst0;
	wire       inst_Mux_1toM_2_rdy_dst1;
	wire       inst_Mux_1toM_3_vld_src ;
	wire [3:0] inst_Mux_1toM_3_pld_src ;
	wire       inst_Mux_1toM_3_rdy_src ;
	wire       inst_Mux_1toM_3_sel_src ;
	wire       inst_Mux_1toM_3_vld_dst0;
	wire       inst_Mux_1toM_3_vld_dst1;
	wire [3:0] inst_Mux_1toM_3_pld_dst0;
	wire [3:0] inst_Mux_1toM_3_pld_dst1;
	wire       inst_Mux_1toM_3_rdy_dst0;
	wire       inst_Mux_1toM_3_rdy_dst1;
	wire       inst_Mux_Nto1_0_clk     ;
	wire       inst_Mux_Nto1_0_rst_n   ;
	wire       inst_Mux_Nto1_0_vld_src0;
	wire       inst_Mux_Nto1_0_vld_src1;
	wire       inst_Mux_Nto1_0_vld_src2;
	wire       inst_Mux_Nto1_0_vld_src3;
	wire [3:0] inst_Mux_Nto1_0_pld_src0;
	wire [3:0] inst_Mux_Nto1_0_pld_src1;
	wire [3:0] inst_Mux_Nto1_0_pld_src2;
	wire [3:0] inst_Mux_Nto1_0_pld_src3;
	wire       inst_Mux_Nto1_0_rdy_src0;
	wire       inst_Mux_Nto1_0_rdy_src1;
	wire       inst_Mux_Nto1_0_rdy_src2;
	wire       inst_Mux_Nto1_0_rdy_src3;
	wire       inst_Mux_Nto1_0_vld_dst ;
	wire [3:0] inst_Mux_Nto1_0_pld_dst ;
	wire       inst_Mux_Nto1_0_rdy_dst ;
	wire       inst_Mux_Nto1_1_clk     ;
	wire       inst_Mux_Nto1_1_rst_n   ;
	wire       inst_Mux_Nto1_1_vld_src0;
	wire       inst_Mux_Nto1_1_vld_src1;
	wire       inst_Mux_Nto1_1_vld_src2;
	wire       inst_Mux_Nto1_1_vld_src3;
	wire [3:0] inst_Mux_Nto1_1_pld_src0;
	wire [3:0] inst_Mux_Nto1_1_pld_src1;
	wire [3:0] inst_Mux_Nto1_1_pld_src2;
	wire [3:0] inst_Mux_Nto1_1_pld_src3;
	wire       inst_Mux_Nto1_1_rdy_src0;
	wire       inst_Mux_Nto1_1_rdy_src1;
	wire       inst_Mux_Nto1_1_rdy_src2;
	wire       inst_Mux_Nto1_1_rdy_src3;
	wire       inst_Mux_Nto1_1_vld_dst ;
	wire [3:0] inst_Mux_Nto1_1_pld_dst ;
	wire       inst_Mux_Nto1_1_rdy_dst ;
	assign rdy_src0 = inst_Mux_1toM_0_rdy_src;
	
	assign rdy_src1 = inst_Mux_1toM_1_rdy_src;
	
	assign rdy_src2 = inst_Mux_1toM_2_rdy_src;
	
	assign rdy_src3 = inst_Mux_1toM_3_rdy_src;
	
	assign vld_dst0 = inst_Mux_Nto1_0_vld_dst;
	
	assign vld_dst1 = inst_Mux_Nto1_1_vld_dst;
	
	assign pld_dst0 = inst_Mux_Nto1_0_pld_dst;
	
	assign pld_dst1 = inst_Mux_Nto1_1_pld_dst;
	
	assign inst_Mux_1toM_0_vld_src = vld_src0;
	
	assign inst_Mux_1toM_0_pld_src = pld_src0;
	
	assign inst_Mux_1toM_0_sel_src = sel_src0;
	
	assign inst_Mux_1toM_0_rdy_dst0 = inst_Mux_Nto1_0_rdy_src0;
	
	assign inst_Mux_1toM_0_rdy_dst1 = inst_Mux_Nto1_1_rdy_src0;
	
	assign inst_Mux_1toM_1_vld_src = vld_src1;
	
	assign inst_Mux_1toM_1_pld_src = pld_src1;
	
	assign inst_Mux_1toM_1_sel_src = sel_src1;
	
	assign inst_Mux_1toM_1_rdy_dst0 = inst_Mux_Nto1_0_rdy_src1;
	
	assign inst_Mux_1toM_1_rdy_dst1 = inst_Mux_Nto1_1_rdy_src1;
	
	assign inst_Mux_1toM_2_vld_src = vld_src2;
	
	assign inst_Mux_1toM_2_pld_src = pld_src2;
	
	assign inst_Mux_1toM_2_sel_src = sel_src2;
	
	assign inst_Mux_1toM_2_rdy_dst0 = inst_Mux_Nto1_0_rdy_src2;
	
	assign inst_Mux_1toM_2_rdy_dst1 = inst_Mux_Nto1_1_rdy_src2;
	
	assign inst_Mux_1toM_3_vld_src = vld_src3;
	
	assign inst_Mux_1toM_3_pld_src = pld_src3;
	
	assign inst_Mux_1toM_3_sel_src = sel_src3;
	
	assign inst_Mux_1toM_3_rdy_dst0 = inst_Mux_Nto1_0_rdy_src3;
	
	assign inst_Mux_1toM_3_rdy_dst1 = inst_Mux_Nto1_1_rdy_src3;
	
	assign inst_Mux_Nto1_0_clk = clk;
	
	assign inst_Mux_Nto1_0_rst_n = rst_n;
	
	assign inst_Mux_Nto1_0_vld_src0 = inst_Mux_1toM_0_vld_dst0;
	
	assign inst_Mux_Nto1_0_vld_src1 = inst_Mux_1toM_1_vld_dst0;
	
	assign inst_Mux_Nto1_0_vld_src2 = inst_Mux_1toM_2_vld_dst0;
	
	assign inst_Mux_Nto1_0_vld_src3 = inst_Mux_1toM_3_vld_dst0;
	
	assign inst_Mux_Nto1_0_pld_src0 = inst_Mux_1toM_0_pld_dst0;
	
	assign inst_Mux_Nto1_0_pld_src1 = inst_Mux_1toM_1_pld_dst0;
	
	assign inst_Mux_Nto1_0_pld_src2 = inst_Mux_1toM_2_pld_dst0;
	
	assign inst_Mux_Nto1_0_pld_src3 = inst_Mux_1toM_3_pld_dst0;
	
	assign inst_Mux_Nto1_0_rdy_dst = rdy_dst0;
	
	assign inst_Mux_Nto1_1_clk = clk;
	
	assign inst_Mux_Nto1_1_rst_n = rst_n;
	
	assign inst_Mux_Nto1_1_vld_src0 = inst_Mux_1toM_0_vld_dst1;
	
	assign inst_Mux_Nto1_1_vld_src1 = inst_Mux_1toM_1_vld_dst1;
	
	assign inst_Mux_Nto1_1_vld_src2 = inst_Mux_1toM_2_vld_dst1;
	
	assign inst_Mux_Nto1_1_vld_src3 = inst_Mux_1toM_3_vld_dst1;
	
	assign inst_Mux_Nto1_1_pld_src0 = inst_Mux_1toM_0_pld_dst1;
	
	assign inst_Mux_Nto1_1_pld_src1 = inst_Mux_1toM_1_pld_dst1;
	
	assign inst_Mux_Nto1_1_pld_src2 = inst_Mux_1toM_2_pld_dst1;
	
	assign inst_Mux_Nto1_1_pld_src3 = inst_Mux_1toM_3_pld_dst1;
	
	assign inst_Mux_Nto1_1_rdy_dst = rdy_dst1;
	
	Mux_1toM inst_Mux_1toM_0 (
		.vld_src(inst_Mux_1toM_0_vld_src),
		.pld_src(inst_Mux_1toM_0_pld_src),
		.rdy_src(inst_Mux_1toM_0_rdy_src),
		.sel_src(inst_Mux_1toM_0_sel_src),
		.vld_dst0(inst_Mux_1toM_0_vld_dst0),
		.vld_dst1(inst_Mux_1toM_0_vld_dst1),
		.pld_dst0(inst_Mux_1toM_0_pld_dst0),
		.pld_dst1(inst_Mux_1toM_0_pld_dst1),
		.rdy_dst0(inst_Mux_1toM_0_rdy_dst0),
		.rdy_dst1(inst_Mux_1toM_0_rdy_dst1));
	Mux_1toM inst_Mux_1toM_1 (
		.vld_src(inst_Mux_1toM_1_vld_src),
		.pld_src(inst_Mux_1toM_1_pld_src),
		.rdy_src(inst_Mux_1toM_1_rdy_src),
		.sel_src(inst_Mux_1toM_1_sel_src),
		.vld_dst0(inst_Mux_1toM_1_vld_dst0),
		.vld_dst1(inst_Mux_1toM_1_vld_dst1),
		.pld_dst0(inst_Mux_1toM_1_pld_dst0),
		.pld_dst1(inst_Mux_1toM_1_pld_dst1),
		.rdy_dst0(inst_Mux_1toM_1_rdy_dst0),
		.rdy_dst1(inst_Mux_1toM_1_rdy_dst1));
	Mux_1toM inst_Mux_1toM_2 (
		.vld_src(inst_Mux_1toM_2_vld_src),
		.pld_src(inst_Mux_1toM_2_pld_src),
		.rdy_src(inst_Mux_1toM_2_rdy_src),
		.sel_src(inst_Mux_1toM_2_sel_src),
		.vld_dst0(inst_Mux_1toM_2_vld_dst0),
		.vld_dst1(inst_Mux_1toM_2_vld_dst1),
		.pld_dst0(inst_Mux_1toM_2_pld_dst0),
		.pld_dst1(inst_Mux_1toM_2_pld_dst1),
		.rdy_dst0(inst_Mux_1toM_2_rdy_dst0),
		.rdy_dst1(inst_Mux_1toM_2_rdy_dst1));
	Mux_1toM inst_Mux_1toM_3 (
		.vld_src(inst_Mux_1toM_3_vld_src),
		.pld_src(inst_Mux_1toM_3_pld_src),
		.rdy_src(inst_Mux_1toM_3_rdy_src),
		.sel_src(inst_Mux_1toM_3_sel_src),
		.vld_dst0(inst_Mux_1toM_3_vld_dst0),
		.vld_dst1(inst_Mux_1toM_3_vld_dst1),
		.pld_dst0(inst_Mux_1toM_3_pld_dst0),
		.pld_dst1(inst_Mux_1toM_3_pld_dst1),
		.rdy_dst0(inst_Mux_1toM_3_rdy_dst0),
		.rdy_dst1(inst_Mux_1toM_3_rdy_dst1));
	Mux_Nto1 inst_Mux_Nto1_0 (
		.clk(inst_Mux_Nto1_0_clk),
		.rst_n(inst_Mux_Nto1_0_rst_n),
		.vld_src0(inst_Mux_Nto1_0_vld_src0),
		.vld_src1(inst_Mux_Nto1_0_vld_src1),
		.vld_src2(inst_Mux_Nto1_0_vld_src2),
		.vld_src3(inst_Mux_Nto1_0_vld_src3),
		.pld_src0(inst_Mux_Nto1_0_pld_src0),
		.pld_src1(inst_Mux_Nto1_0_pld_src1),
		.pld_src2(inst_Mux_Nto1_0_pld_src2),
		.pld_src3(inst_Mux_Nto1_0_pld_src3),
		.rdy_src0(inst_Mux_Nto1_0_rdy_src0),
		.rdy_src1(inst_Mux_Nto1_0_rdy_src1),
		.rdy_src2(inst_Mux_Nto1_0_rdy_src2),
		.rdy_src3(inst_Mux_Nto1_0_rdy_src3),
		.vld_dst(inst_Mux_Nto1_0_vld_dst),
		.pld_dst(inst_Mux_Nto1_0_pld_dst),
		.rdy_dst(inst_Mux_Nto1_0_rdy_dst));
	Mux_Nto1 inst_Mux_Nto1_1 (
		.clk(inst_Mux_Nto1_1_clk),
		.rst_n(inst_Mux_Nto1_1_rst_n),
		.vld_src0(inst_Mux_Nto1_1_vld_src0),
		.vld_src1(inst_Mux_Nto1_1_vld_src1),
		.vld_src2(inst_Mux_Nto1_1_vld_src2),
		.vld_src3(inst_Mux_Nto1_1_vld_src3),
		.pld_src0(inst_Mux_Nto1_1_pld_src0),
		.pld_src1(inst_Mux_Nto1_1_pld_src1),
		.pld_src2(inst_Mux_Nto1_1_pld_src2),
		.pld_src3(inst_Mux_Nto1_1_pld_src3),
		.rdy_src0(inst_Mux_Nto1_1_rdy_src0),
		.rdy_src1(inst_Mux_Nto1_1_rdy_src1),
		.rdy_src2(inst_Mux_Nto1_1_rdy_src2),
		.rdy_src3(inst_Mux_Nto1_1_rdy_src3),
		.vld_dst(inst_Mux_Nto1_1_vld_dst),
		.pld_dst(inst_Mux_Nto1_1_pld_dst),
		.rdy_dst(inst_Mux_Nto1_1_rdy_dst));

endmodule