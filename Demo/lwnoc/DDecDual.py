# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import
from .DDec import *
from .DArb import *

class DDecDual(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node

        num              = len(self.node.dst_list)
        req_pld_width    = node.network.req_pld_width
        ack_pld_width    = node.network.ack_pld_width
        master_id_width  = node.master_id_width
        slave_id_width   = node.slave_id_width

        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))

        # Create Output
        self.out_req_vld_list    = [self.create('out%s_req_vld'     % i, Output(UInt(1)))               for i in range(num)]
        self.out_req_rdy_list    = [self.create('out%s_req_rdy'     % i, Input(UInt(1)))                for i in range(num)]
        self.out_req_head_list   = [self.create('out%s_req_head'    % i, Output(UInt(1)))               for i in range(num)]
        self.out_req_tail_list   = [self.create('out%s_req_tail'    % i, Output(UInt(1)))               for i in range(num)]
        self.out_req_pld_list    = [self.create('out%s_req_pld'     % i, Output(UInt(req_pld_width)))   for i in range(num)]
        self.out_req_mst_id_list = [self.create('out%s_req_mst_id'  % i, Output(UInt(master_id_width))) for i in range(num)]
        self.out_req_slv_id_list = [self.create('out%s_req_slv_id'  % i, Output(UInt(slave_id_width)))  for i in range(num)]

        self.out_ack_vld_list    = [self.create('out%s_ack_vld'     % i, Input(UInt(1)))                for i in range(num)]
        self.out_ack_rdy_list    = [self.create('out%s_ack_rdy'     % i, Output(UInt(1)))               for i in range(num)]
        self.out_ack_head_list   = [self.create('out%s_ack_head'    % i, Input(UInt(1)))                for i in range(num)]
        self.out_ack_tail_list   = [self.create('out%s_ack_tail'    % i, Input(UInt(1)))                for i in range(num)]
        self.out_ack_pld_list    = [self.create('out%s_ack_pld'     % i, Input(UInt(ack_pld_width)))    for i in range(num)]
        self.out_ack_mst_id_list = [self.create('out%s_ack_mst_id'  % i, Input(UInt(master_id_width)))  for i in range(num)]
        self.out_ack_slv_id_list = [self.create('out%s_ack_slv_id'  % i, Input(UInt(slave_id_width)))   for i in range(num)]

        # Create Input
        self.in0_req_vld     = Input(UInt(1))
        self.in0_req_rdy     = Output(UInt(1))
        self.in0_req_head    = Input(UInt(1))
        self.in0_req_tail    = Input(UInt(1))
        self.in0_req_pld     = Input(UInt(req_pld_width))
        self.in0_req_mst_id  = Input(UInt(master_id_width))
        self.in0_req_slv_id  = Input(UInt(slave_id_width))

        self.in0_ack_vld     = Output(UInt(1))
        self.in0_ack_rdy     = Input(UInt(1))
        self.in0_ack_head    = Output(UInt(1))
        self.in0_ack_tail    = Output(UInt(1))
        self.in0_ack_pld     = Output(UInt(ack_pld_width))
        self.in0_ack_mst_id  = Output(UInt(master_id_width))
        self.in0_ack_slv_id  = Output(UInt(slave_id_width))


        # Forward Decode
        self.dec = DDec(self.node, req_pld_width, id_type='mst')

        self.in0_req_rdy      += self.dec.in0_rdy
        self.dec.in0_vld      += self.in0_req_vld
        self.dec.in0_head     += self.in0_req_head
        self.dec.in0_tail     += self.in0_req_tail
        self.dec.in0_pld      += self.in0_req_pld
        self.dec.in0_mst_id   += self.in0_req_mst_id
        self.dec.in0_slv_id   += self.in0_req_slv_id

        for i in range(num):
            self.out_req_vld_list[i]    += self.dec.vld_list[i]    
            self.out_req_head_list[i]   += self.dec.head_list[i]   
            self.out_req_tail_list[i]   += self.dec.tail_list[i]   
            self.out_req_pld_list[i]    += self.dec.pld_list[i]    
            self.out_req_mst_id_list[i] += self.dec.mst_id_list[i] 
            self.out_req_slv_id_list[i] += self.dec.slv_id_list[i] 

            self.dec.rdy_list[i]        += self.out_req_rdy_list[i]


        # Backward Arbitration
        self.arb = DArb(self.node, ack_pld_width, id_type='mst')

        for i in range(num):
            self.arb.vld_list[i]        += self.out_ack_vld_list[i]    
            self.arb.head_list[i]       += self.out_ack_head_list[i]   
            self.arb.tail_list[i]       += self.out_ack_tail_list[i]   
            self.arb.pld_list[i]        += self.out_ack_pld_list[i]    
            self.arb.mst_id_list[i]     += self.out_ack_mst_id_list[i] 
            self.arb.slv_id_list[i]     += self.out_ack_slv_id_list[i] 

            self.out_ack_rdy_list[i]    += self.arb.rdy_list[i] 

        self.in0_ack_vld    += self.arb.out0_vld   
        self.in0_ack_head   += self.arb.out0_head  
        self.in0_ack_tail   += self.arb.out0_tail  
        self.in0_ack_pld    += self.arb.out0_pld   
        self.in0_ack_mst_id += self.arb.out0_mst_id
        self.in0_ack_slv_id += self.arb.out0_slv_id

        self.arb.out0_rdy   += self.in0_ack_rdy

        #for dst in self.node.dst_list:
        #    print(dst.global_id_list)

        #id_width = node.id_width

        # self.vld_list = []
        # self.rdy_list = []
        # self.head_list = []
        # self.tail_list = []
        # self.pld_list = []
        # self.mst_id_list = []
        # self.slv_id_list = []

        # for i in range(num):
        #     self.vld_list.append(self.create('out%s_vld' % i, Output(UInt(1))))
        #     self.rdy_list.append(self.create('out%s_rdy' % i, Input(UInt(1))))
        #     self.head_list.append(self.create('out%s_head' % i, Output(UInt(1))))
        #     self.tail_list.append(self.create('out%s_tail' % i, Output(UInt(1))))
        #     self.pld_list.append(self.create('out%s_pld' % i, Output(UInt(pld_width))))
        #     self.mst_id_list.append(self.create('out%s_id' % i, Output(UInt(master_id_width))))
        #     self.slv_id_list.append(self.create('out%s_id' % i, Output(UInt(slave_id_width))))
