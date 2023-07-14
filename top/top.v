//[UHDL]Content Start [md5:64cdabf3d179af78f838adc116a3a30b]
module top (
	input   din1 ,
	output  dout1,
	input   din2 ,
	output  dout2);

	//Wire define for this module.

	//Wire define for sub module.
	wire  sub1_din0             ;
	wire  sub1_dout1            ;
	wire  sub2_TO_sub1_SIG_dout2;
	wire  sub1_dout2            ;
	wire  sub2_din0             ;
	wire  sub1_TO_sub2_SIG_dout1;
	wire  sub1_TO_sub2_SIG_dout2;

	//Wire define for Inout.

	//Wire sub module connect to this module and inter module connect.

	//Wire this module connect to sub module.
	assign sub1_din0 = 1'b0;
	
	assign sub2_din0 = (sub1_dout1 && sub1_dout2);
	
	assign sub2_din1 = sub1_dout1;
	
	assign sub2_din2 = sub1_dout2;
	

	//module inst.
	sub_mod sub1 (
		.din0(sub1_din0),
		.din1(din1),
		.dout1(sub1_dout1),
		.din2(sub2_TO_sub1_SIG_dout2),
		.dout2(sub1_dout2));
	sub_mod sub2 (
		.din0(sub2_din0),
		.din1(sub2_din1),
		.dout1(dout1),
		.din2(sub2_din2),
		.dout2(sub2_TO_sub1_SIG_dout2));

endmodule
//[UHDL]Content End [md5:64cdabf3d179af78f838adc116a3a30b]

