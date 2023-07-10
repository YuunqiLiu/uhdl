# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import
from .BasciHdsk import BasicHdsk, BasicHdskReverse
from .AxiInterface import *






class DSlvAxi(Component):

    def addr_tgt_id_mapping(self, addr):
        res = EmptyWhen()
        for addr_range, tgt_id in self.node.network._sam_addrrange_tgtid_dict.items():
            res.when(And(GreaterEqual(UInt(32, addr_range[0]), addr), LessEqual(addr, UInt(32, addr_range[1])))).\
                then(UInt(self.node.tgt_id_width, tgt_id))
        res.otherwise(UInt(self.node.tgt_id_width, 0))
        return res

    def __init__(self, node):
        super().__init__()
        self.node = node

        # Create IO
        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))

        self.out0_r_req = BasicHdsk(node.src_id_width, node.tgt_id_width, node.txn_id_width, node.r_req_pld_width)
        self.out0_w_req = BasicHdsk(node.src_id_width, node.tgt_id_width, node.txn_id_width, node.w_req_pld_width)
        self.out0_r_ack = BasicHdskReverse(node.src_id_width, node.tgt_id_width, node.txn_id_width, node.r_ack_pld_width)
        self.out0_w_ack = BasicHdskReverse(node.src_id_width, node.tgt_id_width, node.txn_id_width, node.w_ack_pld_width)

        self.in0 = AxiReverse(node.txn_id_width, node.addr_width, node.data_width, node.user_width)


        ################################################################
        # Write Req Channel
        ################################################################

        self.wait_aw_reg = Reg(UInt(1), self.clk, self.rst_n)
        self.wait_aw_reg += when(AndList(self.in0.w_vld, self.in0.w_rdy, self.in0.w_last)).then(UInt(1, 1)).\
                            when(And(self.in0.aw_vld, self.in0.aw_rdy)).then(UInt(1, 0))

        Assign(self.out0_w_req.pld     ,Combine(self.in0.aw_addr, self.in0.aw_user, self.in0.w_strb, self.in0.w_data))
        Assign(self.out0_w_req.vld     ,when(self.wait_aw_reg).then(And(self.in0.aw_vld, self.in0.w_vld)).otherwise(self.in0.w_vld))
        Assign(self.out0_w_req.head    ,And(self.in0.aw_vld, self.in0.aw_rdy))
        Assign(self.out0_w_req.tail    ,self.in0.w_last)
        Assign(self.out0_w_req.tgt_id  ,self.addr_tgt_id_mapping(self.in0.aw_addr))
        Assign(self.out0_w_req.txn_id  ,self.in0.aw_id)
        Assign(self.out0_w_req.src_id  ,UInt(node.src_id_width, self.node.src_id))

        Assign(self.in0.aw_rdy ,AndList(self.out0_w_req.vld, self.out0_w_req.rdy, self.wait_aw_reg))
        Assign(self.in0.w_rdy  ,AndList(self.out0_w_req.vld, self.out0_w_req.rdy))


        ################################################################
        # Write Ack Channel
        ################################################################

        Assign(self.out0_w_ack.rdy ,self.in0.b_rdy)
        Assign(self.in0.b_vld      ,self.out0_w_ack.vld)
        Assign(self.in0.b_id       ,self.out0_w_ack.txn_id)
        Assign(self.in0.b_resp     ,self.out0_w_ack.pld[1:0])


        ################################################################
        # Read Req Channel
        ################################################################

        Assign(self.out0_r_req.vld     ,self.in0.ar_vld)
        Assign(self.in0.ar_rdy         ,self.out0_r_req.rdy)
        Assign(self.out0_r_req.head    ,UInt(1, 1))
        Assign(self.out0_r_req.tail    ,UInt(1, 1))
        Assign(self.out0_r_req.pld     ,Combine(self.in0.ar_addr, self.in0.ar_user))
        Assign(self.out0_r_req.src_id  ,UInt(node.src_id_width, self.node.src_id))
        Assign(self.out0_r_req.txn_id  ,self.in0.ar_id)
        Assign(self.out0_r_req.tgt_id  ,self.addr_tgt_id_mapping(self.in0.ar_addr))


        ################################################################
        # Ack Channel
        ################################################################

        Assign(self.in0.r_vld      ,self.out0_r_ack.vld)
        Assign(self.out0_r_ack.rdy ,self.in0.r_rdy)
        Assign(self.in0.r_id       ,self.out0_r_ack.txn_id)

        Unpack(self.out0_r_ack.pld, self.in0.r_resp, self.in0.r_data, self.in0.r_last)





class DSlv(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node

        self.in0_vld = Input(UInt(1))
        self.in0_rdy = Output(UInt(1))
        self.in0_head = Input(UInt(1))
        self.in0_tail = Input(UInt(1))
        self.in0_pld = Input(UInt(self.node.src_width))
        self.in0_mst_id = Input(UInt(self.node.master_id_width))

        self.out0_req_vld = Output(UInt(1))
        self.out0_req_rdy = Input(UInt(1))
        self.out0_req_head = Output(UInt(1))
        self.out0_req_tail = Output(UInt(1))
        self.out0_req_pld = Output(UInt(self.node.dst_width))
        self.out0_req_mst_id = Output(UInt(self.node.master_id_width))
        self.out0_req_slv_id = Output(UInt(self.node.slave_id_width))

        self.out0_req_vld += self.in0_vld
        self.in0_rdy += self.out0_req_rdy
        self.out0_req_pld += self.in0_pld
        self.out0_req_mst_id += self.in0_mst_id






# class DSlvAxi(Component):


    # def addr_id_mapping(self, tgt_id, addr):
        # res = EmptyWhen()
        # for global_id in self.node.global_master_id_list:
            # addr_range = self.node.network._global_id_address_range_map_dict[global_id]
            # res.when(And(GreaterEqual(UInt(32, addr_range[0]), addr), LessEqual(addr, UInt(32, addr_range[1])))).\
                # then(UInt(self.node.tgt_id_width, global_id))
        # res.otherwise(UInt(self.node.tgt_id_width, 0))
        # tgt_id += res
        # tgt_id += UInt(self.node.src_id_width, self.node.slave_id)

    # def __init__(self, node):
        # super().__init__()
        # self.node = node
        # slave_id_width = self.node.src_id_width
        # master_id_width = self.node.tgt_id_width
        # slave_axi_id_width = self.node.network.txn_id_width


        # self.clk = Input(UInt(1))
        # self.rst_n = Input(UInt(1))

        # self.in_aw_vld = Input(UInt(1))
        # self.in_aw_rdy = Output(UInt(1))
        # self.in_aw_addr = Input(UInt(32))
        # self.in_aw_id = Input(UInt(slave_axi_id_width))
        # self.in_aw_user = Input(UInt(self.node.network.user_width))

        # self.in_w_vld = Input(UInt(1))
        # self.in_w_rdy = Output(UInt(1))
        # self.in_w_last = Input(UInt(1))
        # self.in_w_strb = Input(UInt(int(self.node.network.data_width/8)))
        # self.in_w_data = Input(UInt(self.node.network.data_width))

        # self.in_b_vld = Output(UInt(1))
        # self.in_b_rdy = Input(UInt(1))
        # self.in_b_id = Output(UInt(slave_axi_id_width))
        # self.in_b_resp = Output(UInt(2))

        # self.out0_req_vld = Output(UInt(1))
        # self.out0_req_rdy = Input(UInt(1))
        # self.out0_req_head = Output(UInt(1))
        # self.out0_req_tail = Output(UInt(1))
        # self.out0_req_pld = Output(UInt(self.node.network.req_pld_width))
        # self.out0_req_mst_id = Output(UInt(master_id_width))
        # self.out0_req_slv_id = Output(UInt(slave_id_width))
   
        # self.out0_ack_vld = Input(UInt(1))
        # self.out0_ack_rdy = Output(UInt(1))
        # self.out0_ack_head = Input(UInt(1))
        # self.out0_ack_tail = Input(UInt(1))
        # self.out0_ack_pld = Input(UInt(self.node.network.ack_pld_width))
        # self.out0_ack_mst_id = Input(UInt(master_id_width))
        # self.out0_ack_slv_id = Input(UInt(slave_id_width))







        #self.extended_axi_id = Wire(UInt(self.slave_id_width + self.slave_axi_id_width))
        #self.extended_axi_id += Combine(UInt(self.slave_id_width, self.node.slave_id), self.in_aw_id)


        ################################################################
        # Req Channel
        ################################################################
 #        self.out0_req_pld += Combine(self.in_aw_addr, self.in_aw_id, self.in_aw_user, self.in_w_strb, self.in_w_data)

 #        self.wait_aw_reg = Reg(UInt(1), self.clk, self.rst_n)
 #        self.wait_aw_reg += when(AndList(self.in_w_vld, self.in_w_rdy, self.in_w_last)).then(UInt(1, 1)).\
                             #when(And(self.in_aw_vld, self.in_aw_rdy)).then(UInt(1, 0))

 #        self.out0_req_vld += when(self.wait_aw_reg).then(And(self.in_aw_vld, self.in_w_vld)).otherwise(self.in_w_vld)
 #        self.out0_req_head += And(self.in_aw_vld, self.in_aw_rdy)
 #        self.out0_req_tail += self.in_w_last

 #        res = EmptyWhen()
 #        for global_id in self.node.global_master_id_list:
             #addr_range = self.node.network._global_id_address_range_map_dict[global_id]
             #res.when(And(GreaterEqual(UInt(32, addr_range[0]), self.in_aw_addr), LessEqual(self.in_aw_addr, UInt(32, addr_range[1])))).\
                 #then(UInt(master_id_width, global_id))
 #        res.otherwise(UInt(master_id_width, 0))
 #        self.out0_req_mst_id += res
 #        self.out0_req_slv_id += UInt(slave_id_width, self.node.slave_id)

 #        self.in_aw_rdy += AndList(self.out0_req_vld, self.out0_req_rdy, self.wait_aw_reg)
 #        self.in_w_rdy += AndList(self.out0_req_vld, self.out0_req_rdy)


 #        ################################################################
 #        # Ack Channel
 #        ################################################################

 #        self.out0_ack_rdy += self.in_b_rdy

 #        self.in_b_vld += self.out0_ack_vld
 #        self.in_b_id += self.out0_ack_pld[self.node.network.ack_pld_width-1:2]
 #        self.in_b_resp += self.out0_ack_pld[1:0]


 ########################################################################################################################

 #        self.in_ar_vld  = Input(UInt(1))
 #        self.in_ar_rdy  = Output(UInt(1))
 #        self.in_ar_addr = Input(UInt(32))
 #        self.in_ar_id   = Input(UInt(slave_axi_id_width))
 #        self.in_ar_user = Input(UInt(self.node.network.user_width))

 #        self.in_r_vld   = Output(UInt(1))
 #        self.in_r_rdy   = Input(UInt(1))
 #        self.in_r_id    = Output(UInt(slave_axi_id_width))
 #        self.in_r_data  = Output(UInt(self.node.network.data_width))
 #        self.in_r_resp  = Output(UInt(2))
 #        self.in_r_last  = Output(UInt(1))

 #        self.out0_r_req_vld      = Output(UInt(1))
 #        self.out0_r_req_rdy      = Input(UInt(1))
 #        self.out0_r_req_head     = Output(UInt(1))
 #        self.out0_r_req_tail     = Output(UInt(1))
 #        self.out0_r_req_pld      = Output(UInt(self.node.network.r_req_pld_width))
 #        self.out0_r_req_mst_id   = Output(UInt(master_id_width))
 #        self.out0_r_req_slv_id   = Output(UInt(slave_id_width))

 #        self.out0_r_ack_vld      = Input(UInt(1))
 #        self.out0_r_ack_rdy      = Output(UInt(1))
 #        self.out0_r_ack_head     = Input(UInt(1))
 #        self.out0_r_ack_tail     = Input(UInt(1))
 #        self.out0_r_ack_pld      = Input(UInt(self.node.network.r_ack_pld_width))
 #        self.out0_r_ack_mst_id   = Input(UInt(master_id_width))
 #        self.out0_r_ack_slv_id   = Input(UInt(slave_id_width))


 #        ################################################################
 #        # Req Channel
 #        ################################################################

 #        self.out0_r_req_vld     += self.in_ar_vld
 #        self.in_ar_rdy          += self.out0_r_ack_rdy
 #        self.out0_r_req_head    += UInt(1, 1)
 #        self.out0_r_req_tail    += UInt(1, 1)
 #        self.out0_r_req_pld     += Combine(self.in_ar_addr, self.in_ar_id, self.in_ar_user)
 #        self.out0_r_req_slv_id  += UInt(slave_id_width, self.node.slave_id)

 #        self.addr_id_mapping(self.out0_r_req_mst_id, self.in_ar_addr)

 #        ################################################################
 #        # Ack Channel
 #        ################################################################


 #        self.in_r_vld       += self.out0_r_ack_vld
 #        self.out0_r_ack_rdy += self.in_r_rdy
 #        Unpack(self.out0_r_ack_pld, self.in_r_id, self.in_r_resp, self.in_r_data, self.in_r_last)

