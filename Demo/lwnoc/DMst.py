# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import


class DMst(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node

        self.in0_vld = Input(UInt(1))
        self.in0_rdy = Output(UInt(1))
        self.in0_head = Input(UInt(1))
        self.in0_tail = Input(UInt(1))
        self.in0_pld = Input(UInt(self.node.src_width))
        self.in0_id = Input(UInt(self.node.id_width))

        self.out0_vld = Output(UInt(1))
        self.out0_rdy = Input(UInt(1))
        self.out0_head = Output(UInt(1))
        self.out0_tail = Output(UInt(1))
        self.out0_pld = Output(UInt(self.node.dst_width))
        self.out0_id = Output(UInt(self.node.id_width))

        self.out0_vld += self.in0_vld
        self.in0_rdy += self.out0_rdy
        self.out0_head += self.in0_head
        self.out0_tail += self.in0_tail
        self.out0_pld += self.in0_pld
        self.out0_id += self.in0_id



class DMstAxi(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node
        slave_id_width = self.node.network.slave_id_width
        master_id_width = self.node.network.master_id_width
        slave_axi_id_width = self.node.network.slave_axi_id_width
        master_axi_id_width = self.node.network.master_axi_id_width
        

        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))

        self.out_aw_vld = Output(UInt(1))
        self.out_aw_rdy = Input(UInt(1))
        self.out_aw_addr = Output(UInt(32))
        self.out_aw_id = Output(UInt(master_axi_id_width))
        self.out_aw_user = Output(UInt(self.node.network.user_width))

        self.out_w_vld = Output(UInt(1))
        self.out_w_rdy = Input(UInt(1))
        self.out_w_last = Output(UInt(1))
        self.out_w_strb = Output(UInt(int(self.node.network.data_width/8)))
        self.out_w_data = Output(UInt(self.node.network.data_width))

        self.out_b_vld = Input(UInt(1))
        self.out_b_rdy = Output(UInt(1))
        self.out_b_id = Input(UInt(master_axi_id_width))
        self.out_b_resp = Input(UInt(2))

        self.in0_req_vld = Input(UInt(1))
        self.in0_req_rdy = Output(UInt(1))
        self.in0_req_head = Input(UInt(1))
        self.in0_req_tail = Input(UInt(1))
        self.in0_req_pld = Input(UInt(self.node.network.req_pld_width))
        self.in0_req_mst_id = Input(UInt(master_id_width))
        self.in0_req_slv_id = Input(UInt(slave_id_width))

        self.in0_ack_vld = Output(UInt(1))
        self.in0_ack_rdy = Input(UInt(1))
        self.in0_ack_head = Output(UInt(1))
        self.in0_ack_tail = Output(UInt(1))
        self.in0_ack_pld = Output(UInt(self.node.network.ack_pld_width))
        self.in0_ack_mst_id = Output(UInt(master_id_width))
        self.in0_ack_slv_id = Output(UInt(slave_id_width))

        ################################################################
        # Req Channel
        ################################################################

        self.in0_req_rdy += And(self.out_aw_vld, self.out_aw_rdy)
        
        self.out_aw_vld += AndList(self.in0_req_rdy, self.in0_req_vld, self.in0_req_head)
        self.out_w_vld += And(self.in0_req_rdy, self.in0_req_vld)
        









        self.internal_slave_axi_id = Wire(UInt(slave_axi_id_width))

        Unpack(self.in0_req_pld, self.out_aw_addr, self.internal_slave_axi_id, self.out_aw_user, self.out_w_strb, self.out_w_data)

        self.out_aw_id += Combine(self.in0_req_slv_id, self.internal_slave_axi_id)

        ################################################################
        # Ack Channel
        ################################################################

        self.in0_ack_vld += self.out_b_vld
        self.in0_ack_pld += Combine(self.out_b_id[master_axi_id_width-slave_id_width-1:0], self.out_b_resp)
        self.in0_ack_mst_id += UInt(master_id_width, self.node.master_id)
        self.in0_ack_slv_id += self.out_b_id[master_axi_id_width-1:master_axi_id_width-slave_id_width]
        self.in0_ack_head += UInt(1, 1)
        self.in0_ack_tail += UInt(1, 1)
        
        self.out_b_rdy += self.in0_ack_rdy


#######################################################################################################################


        self.out_ar_vld  = Output(UInt(1))
        self.out_ar_rdy  = Input(UInt(1))
        self.out_ar_addr = Output(UInt(32))
        self.out_ar_id   = Output(UInt(master_axi_id_width))
        self.out_ar_user = Output(UInt(self.node.network.user_width))

        self.out_r_vld   = Input(UInt(1))
        self.out_r_rdy   = Output(UInt(1))
        self.out_r_id    = Input(UInt(master_axi_id_width))
        self.out_r_data  = Input(UInt(self.node.network.data_width))
        self.out_r_resp  = Input(UInt(2))
        self.out_r_last  = Input(UInt(1))



        self.in0_r_req_vld      = Input(UInt(1))
        self.in0_r_req_rdy      = Output(UInt(1))
        self.in0_r_req_head     = Input(UInt(1))
        self.in0_r_req_tail     = Input(UInt(1))
        self.in0_r_req_pld      = Input(UInt(self.node.network.r_req_pld_width))
        self.in0_r_req_mst_id   = Input(UInt(master_id_width))
        self.in0_r_req_slv_id   = Input(UInt(slave_id_width))

        self.in0_r_ack_vld      = Output(UInt(1))
        self.in0_r_ack_rdy      = Input(UInt(1))
        self.in0_r_ack_head     = Output(UInt(1))
        self.in0_r_ack_tail     = Output(UInt(1))
        self.in0_r_ack_pld      = Output(UInt(self.node.network.r_ack_pld_width))
        self.in0_r_ack_mst_id   = Output(UInt(master_id_width))
        self.in0_r_ack_slv_id   = Output(UInt(slave_id_width))


        ################################################################
        # Req Channel
        ################################################################
        self.internal_slave_r_axi_id = Wire(UInt(slave_axi_id_width))
        Unpack(self.in0_r_req_pld, self.out_ar_user, self.out_ar_addr, self.internal_slave_r_axi_id)

        self.out_ar_vld += self.in0_r_req_vld
        self.out_ar_id += Combine(self.in0_r_req_slv_id, self.internal_slave_r_axi_id)

        self.in0_r_req_rdy += self.out_ar_rdy




        ################################################################
        # Ack Channel
        ################################################################
        self.in0_r_ack_vld    += self.out_r_vld
        self.out_r_rdy        += self.in0_r_ack_rdy
        self.in0_r_ack_head   += UInt(1, 1)
        self.in0_r_ack_tail   += UInt(1, 1)
        self.in0_r_ack_pld    += Combine(self.out_r_id[slave_axi_id_width-1:0], self.out_r_resp, self.out_r_data)
        self.in0_r_ack_mst_id += UInt(master_id_width, self.node.master_id)
        self.in0_r_ack_slv_id += self.out_r_id[master_axi_id_width-1:master_axi_id_width-slave_id_width]


        #strb_width = int(self.node.network.data_width/8)
        # self.out_aw_addr += self.in0_req_pld[self.node.network.data_width + strb_width + self.node.network.user_width + master_axi_id_width + 32 - 1 :self.node.network.data_width + strb_width + self.node.network.user_width + master_axi_id_width]
        # self.out_aw_id += self.in0_req_pld[self.node.network.data_width + strb_width + self.node.network.user_width + master_axi_id_width -1 :self.node.network.data_width + strb_width + self.node.network.user_width]
        # self.out_aw_user += self.in0_req_pld[self.node.network.data_width + strb_width + self.node.network.user_width -1:self.node.network.data_width + strb_width]
        # self.out_w_strb += self.in0_req_pld[self.node.network.data_width + strb_width - 1 :self.node.network.data_width]
        # self.out_w_data += self.in0_req_pld[self.node.network.data_width-1:0]


                #self.out_aw_vld_pre_rs = Wire(UInt(1))
        #self.out_aw_rdy_pre_rs = Wire(UInt(1))

        #self.out_w_vld_pre_rs = Wire(UInt(1))
        #self.out_w_rdy_pre_rs = Wire(UInt(1))




        # self.in0_req_pld

        # self.out_aw_addr = Output(UInt(32))
        # self.out_aw_id = Output(UInt(self.master_axi_id_width))
        # self.out_aw_user = Output(UInt(self.node.network.user_width))

        # self.out_w_vld = Output(UInt(1))
        # self.out_w_rdy = Input(UInt(1))
        # self.out_w_last = Output(UInt(1))
        # self.out_w_strb = Output(UInt(1))