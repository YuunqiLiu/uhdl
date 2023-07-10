# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import


class SyncFIFO(Component):

    def __init__(self, pld_width):
        super().__init__()

        self.clk            = Input(UInt(1))
        self.rst_n          = Input(UInt(1))

        self.in_vld         = Input(UInt(1))
        self.in_rdy         = Output(UInt(1))
        self.in_pld         = Input(UInt(pld_width))

        self.out_vld        = Output(UInt(1))
        self.out_rdy        = Input(UInt(1))
        self.out_pld        = Output(UInt(pld_width))

        self.out_vld        += self.in_vld
        self.in_rdy         += self.out_rdy
        self.out_pld        += self.in_pld




class DCdtRegSliceS(Component):

    def __init__(self, node, pld_width):
        super().__init__()
        self.node = node

        master_id_width  = node.master_id_width
        slave_id_width   = node.slave_id_width

        self.clk            = Input(UInt(1))
        self.rst_n          = Input(UInt(1))

        # Create Input
        self.in0_vld        = Input(UInt(1))
        self.in0_rdy        = Output(UInt(1))
        self.in0_head       = Input(UInt(1))
        self.in0_tail       = Input(UInt(1))
        self.in0_pld        = Input(UInt(pld_width))
        self.in0_mst_id     = Input(UInt(master_id_width))
        self.in0_slv_id     = Input(UInt(slave_id_width))

        # Create Output
        self.out0_en        = Output(UInt(1))
        self.out0_head      = Output(UInt(1))
        self.out0_tail      = Output(UInt(1))
        self.out0_pld       = Output(UInt(pld_width))
        self.out0_mst_id    = Output(UInt(master_id_width))
        self.out0_slv_id    = Output(UInt(slave_id_width))
        self.out0_cdt       = Input(UInt(1))

        self.out0_en     += And(self.in0_vld, self.in0_rdy)
        self.out0_head   += self.in0_head
        self.out0_tail   += self.in0_tail
        self.out0_pld    += self.in0_pld
        self.out0_mst_id += self.in0_mst_id 
        self.out0_slv_id += self.in0_slv_id 

        self.cdt_cnt = Reg(UInt(4), self.clk, self.rst_n)

        self.cdt_cnt += when(And(self.out0_en, self.out0_cdt)).then(self.cdt_cnt).\
                        when(self.out0_en).then(self.cdt_cnt - UInt(4, 1)).\
                        when(self.out0_cdt).then(self.cdt_cnt + UInt(4, 1))

        self.in0_rdy += NotEqual(self.cdt_cnt, UInt(4, 0))



class DCdtRegSliceM(Component):

    def __init__(self, node, pld_width):
        super().__init__()
        self.node = node

        buffer_depth = 4

        master_id_width  = node.master_id_width
        slave_id_width   = node.slave_id_width

        self.clk            = Input(UInt(1))
        self.rst_n          = Input(UInt(1))

        # Create Input
        self.in0_en         = Input(UInt(1))
        self.in0_head       = Input(UInt(1))
        self.in0_tail       = Input(UInt(1))
        self.in0_pld        = Input(UInt(pld_width))
        self.in0_mst_id     = Input(UInt(master_id_width))
        self.in0_slv_id     = Input(UInt(slave_id_width))
        self.in0_cdt        = Output(UInt(1))

        # Create Output
        self.out0_vld       = Output(UInt(1))
        self.out0_rdy       = Input(UInt(1))
        self.out0_head      = Output(UInt(1))
        self.out0_tail      = Output(UInt(1))
        self.out0_pld       = Output(UInt(pld_width))
        self.out0_mst_id    = Output(UInt(master_id_width))
        self.out0_slv_id    = Output(UInt(slave_id_width))


        fifo = SyncFIFO(1+1+pld_width+master_id_width+slave_id_width)

        fifo.in_vld += self.in0_en
        fifo.in_pld += Combine(self.in0_head, self.in0_tail, self.in0_pld, self.in0_mst_id, self.in0_slv_id)

        self.out0_vld += fifo.out_vld
        fifo.out_rdy  += self.out0_rdy
        Unpack(fifo.out_pld, self.out0_head, self.out0_tail, self.out0_pld, self.out0_mst_id, self.out0_slv_id)



        self.out0_en = Wire(UInt(1))
        self.out0_en += And(self.out0_vld, self.out0_rdy)

        self.cdt_cnt = Reg(UInt(4, buffer_depth), self.clk, self.rst_n)
        self.cdt_cnt += when(And(self.out0_en, self.in0_cdt)).then(self.cdt_cnt).\
                        when(self.out0_en).then(self.cdt_cnt + UInt(4, 1)).\
                        when(self.in0_cdt).then(self.cdt_cnt - UInt(4, 1))

        self.in0_cdt += NotEqual(self.cdt_cnt, UInt(4, 0))