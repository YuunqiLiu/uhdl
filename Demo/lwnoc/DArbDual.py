# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import
from .DDec import *
from .DArb import *
from .BasciHdsk import BasicHdsk, BasicHdskReverse

class DArbDual(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node

        num              = len(self.node.src_list)
        req_pld_width    = node.network.req_pld_width
        ack_pld_width    = node.network.ack_pld_width
        master_id_width  = node.tgt_id_width
        slave_id_width   = node.src_id_width

        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))



    ###############################################################################################
    # Write
    ###############################################################################################


        # Create Input
        self.in_req_vld_list    = [self.create('in%s_req_vld'       % i, Input(UInt(1)))                for i in range(num)]
        self.in_req_rdy_list    = [self.create('in%s_req_rdy'       % i, Output(UInt(1)))               for i in range(num)]
        self.in_req_head_list   = [self.create('in%s_req_head'      % i, Input(UInt(1)))                for i in range(num)]
        self.in_req_tail_list   = [self.create('in%s_req_tail'      % i, Input(UInt(1)))                for i in range(num)]
        self.in_req_pld_list    = [self.create('in%s_req_pld'       % i, Input(UInt(req_pld_width)))    for i in range(num)]
        self.in_req_mst_id_list = [self.create('in%s_req_mst_id'    % i, Input(UInt(master_id_width)))  for i in range(num)]
        self.in_req_slv_id_list = [self.create('in%s_req_slv_id'    % i, Input(UInt(slave_id_width)))   for i in range(num)]

        self.in_ack_vld_list    = [self.create('in%s_ack_vld'       % i, Output(UInt(1)))               for i in range(num)]
        self.in_ack_rdy_list    = [self.create('in%s_ack_rdy'       % i, Input(UInt(1)))                for i in range(num)]
        self.in_ack_head_list   = [self.create('in%s_ack_head'      % i, Output(UInt(1)))               for i in range(num)]
        self.in_ack_tail_list   = [self.create('in%s_ack_tail'      % i, Output(UInt(1)))               for i in range(num)]
        self.in_ack_pld_list    = [self.create('in%s_ack_pld'       % i, Output(UInt(ack_pld_width)))   for i in range(num)]
        self.in_ack_mst_id_list = [self.create('in%s_ack_mst_id'    % i, Output(UInt(master_id_width))) for i in range(num)]
        self.in_ack_slv_id_list = [self.create('in%s_ack_slv_id'    % i, Output(UInt(slave_id_width)))  for i in range(num)]

        # Create Output
        self.out0_req_vld     = Output(UInt(1))
        self.out0_req_rdy     = Input(UInt(1))
        self.out0_req_head    = Output(UInt(1))
        self.out0_req_tail    = Output(UInt(1))
        self.out0_req_pld     = Output(UInt(req_pld_width))
        self.out0_req_mst_id  = Output(UInt(master_id_width))
        self.out0_req_slv_id  = Output(UInt(slave_id_width))

        self.out0_ack_vld     = Input(UInt(1))
        self.out0_ack_rdy     = Output(UInt(1))
        self.out0_ack_head    = Input(UInt(1))
        self.out0_ack_tail    = Input(UInt(1))
        self.out0_ack_pld     = Input(UInt(ack_pld_width))
        self.out0_ack_mst_id  = Input(UInt(master_id_width))
        self.out0_ack_slv_id  = Input(UInt(slave_id_width))


        # Forward Arb
        self.arb = DArb(self.node, req_pld_width, id_type='slv')

        self.arb.out0_rdy       += self.out0_req_rdy
        
        self.out0_req_vld      += self.arb.out0_vld     
        self.out0_req_head     += self.arb.out0_head    
        self.out0_req_tail     += self.arb.out0_tail    
        self.out0_req_pld      += self.arb.out0_pld     
        self.out0_req_mst_id   += self.arb.out0_mst_id  
        self.out0_req_slv_id   += self.arb.out0_slv_id  

        for i in range(num):
            self.arb.vld_list[i]     += self.in_req_vld_list[i]   
            self.arb.head_list[i]    += self.in_req_head_list[i]  
            self.arb.tail_list[i]    += self.in_req_tail_list[i]  
            self.arb.pld_list[i]     += self.in_req_pld_list[i]   
            self.arb.mst_id_list[i]  += self.in_req_mst_id_list[i]
            self.arb.slv_id_list[i]  += self.in_req_slv_id_list[i]

            self.in_req_rdy_list[i] += self.arb.rdy_list[i]

        # Backward Decode
        self.dec = DDec(self.node, ack_pld_width, id_type='slv')

        for i in range(num):
            self.in_ack_vld_list[i]     += self.dec.vld_list[i]   
            self.in_ack_head_list[i]    += self.dec.head_list[i]  
            self.in_ack_tail_list[i]    += self.dec.tail_list[i]  
            self.in_ack_pld_list[i]     += self.dec.pld_list[i]   
            self.in_ack_mst_id_list[i]  += self.dec.mst_id_list[i]
            self.in_ack_slv_id_list[i]  += self.dec.slv_id_list[i]

            self.dec.rdy_list[i]        += self.in_ack_rdy_list[i]


        self.dec.in0_vld    += self.out0_ack_vld   
        self.dec.in0_head   += self.out0_ack_head  
        self.dec.in0_tail   += self.out0_ack_tail  
        self.dec.in0_pld    += self.out0_ack_pld   
        self.dec.in0_mst_id += self.out0_ack_mst_id
        self.dec.in0_slv_id += self.out0_ack_slv_id

        self.out0_ack_rdy   += self.dec.in0_rdy 

    ###############################################################################################
    # Read
    ###############################################################################################

        # Create Input
        self.in_r_req_vld_list    = [self.create('in%s_r_req_vld'       % i, Input(UInt(1)))                                    for i in range(num)]
        self.in_r_req_rdy_list    = [self.create('in%s_r_req_rdy'       % i, Output(UInt(1)))                                   for i in range(num)]
        self.in_r_req_head_list   = [self.create('in%s_r_req_head'      % i, Input(UInt(1)))                                    for i in range(num)]
        self.in_r_req_tail_list   = [self.create('in%s_r_req_tail'      % i, Input(UInt(1)))                                    for i in range(num)]
        self.in_r_req_pld_list    = [self.create('in%s_r_req_pld'       % i, Input(UInt(self.node.network.r_req_pld_width)))    for i in range(num)]
        self.in_r_req_mst_id_list = [self.create('in%s_r_req_mst_id'    % i, Input(UInt(master_id_width)))                      for i in range(num)]
        self.in_r_req_slv_id_list = [self.create('in%s_r_req_slv_id'    % i, Input(UInt(slave_id_width)))                       for i in range(num)]

        self.in_r_ack_vld_list    = [self.create('in%s_r_ack_vld'       % i, Output(UInt(1)))                                   for i in range(num)]
        self.in_r_ack_rdy_list    = [self.create('in%s_r_ack_rdy'       % i, Input(UInt(1)))                                    for i in range(num)]
        self.in_r_ack_head_list   = [self.create('in%s_r_ack_head'      % i, Output(UInt(1)))                                   for i in range(num)]
        self.in_r_ack_tail_list   = [self.create('in%s_r_ack_tail'      % i, Output(UInt(1)))                                   for i in range(num)]
        self.in_r_ack_pld_list    = [self.create('in%s_r_ack_pld'       % i, Output(UInt(self.node.network.r_ack_pld_width)))   for i in range(num)]
        self.in_r_ack_mst_id_list = [self.create('in%s_r_ack_mst_id'    % i, Output(UInt(master_id_width)))                     for i in range(num)]
        self.in_r_ack_slv_id_list = [self.create('in%s_r_ack_slv_id'    % i, Output(UInt(slave_id_width)))                      for i in range(num)]

        # Create Output
        self.out0_r_req_vld     = Output(UInt(1))
        self.out0_r_req_rdy     = Input(UInt(1))
        self.out0_r_req_head    = Output(UInt(1))
        self.out0_r_req_tail    = Output(UInt(1))
        self.out0_r_req_pld     = Output(UInt(self.node.network.r_req_pld_width))
        self.out0_r_req_mst_id  = Output(UInt(master_id_width))
        self.out0_r_req_slv_id  = Output(UInt(slave_id_width))

        self.out0_r_ack_vld     = Input(UInt(1))
        self.out0_r_ack_rdy     = Output(UInt(1))
        self.out0_r_ack_head    = Input(UInt(1))
        self.out0_r_ack_tail    = Input(UInt(1))
        self.out0_r_ack_pld     = Input(UInt(self.node.network.r_ack_pld_width))
        self.out0_r_ack_mst_id  = Input(UInt(master_id_width))
        self.out0_r_ack_slv_id  = Input(UInt(slave_id_width))


        # Forward Arb
        self.arbr = DArb(self.node, self.node.network.r_req_pld_width, id_type='slv')

        self.arbr.out0_rdy       += self.out0_r_req_rdy
        
        self.out0_r_req_vld      += self.arbr.out0_vld     
        self.out0_r_req_head     += self.arbr.out0_head    
        self.out0_r_req_tail     += self.arbr.out0_tail    
        self.out0_r_req_pld      += self.arbr.out0_pld     
        self.out0_r_req_mst_id   += self.arbr.out0_mst_id  
        self.out0_r_req_slv_id   += self.arbr.out0_slv_id  

        for i in range(num):
            self.arbr.vld_list[i]     += self.in_r_req_vld_list[i]   
            self.arbr.head_list[i]    += self.in_r_req_head_list[i]  
            self.arbr.tail_list[i]    += self.in_r_req_tail_list[i]  
            self.arbr.pld_list[i]     += self.in_r_req_pld_list[i]   
            self.arbr.mst_id_list[i]  += self.in_r_req_mst_id_list[i]
            self.arbr.slv_id_list[i]  += self.in_r_req_slv_id_list[i]

            self.in_r_req_rdy_list[i] += self.arbr.rdy_list[i]

        # Backward Decode
        self.decr = DDec(self.node, self.node.network.r_ack_pld_width, id_type='slv')

        for i in range(num):
            self.in_r_ack_vld_list[i]     += self.decr.vld_list[i]   
            self.in_r_ack_head_list[i]    += self.decr.head_list[i]  
            self.in_r_ack_tail_list[i]    += self.decr.tail_list[i]  
            self.in_r_ack_pld_list[i]     += self.decr.pld_list[i]   
            self.in_r_ack_mst_id_list[i]  += self.decr.mst_id_list[i]
            self.in_r_ack_slv_id_list[i]  += self.decr.slv_id_list[i]

            self.decr.rdy_list[i]        += self.in_r_ack_rdy_list[i]


        self.decr.in0_vld    += self.out0_r_ack_vld   
        self.decr.in0_head   += self.out0_r_ack_head  
        self.decr.in0_tail   += self.out0_r_ack_tail  
        self.decr.in0_pld    += self.out0_r_ack_pld   
        self.decr.in0_mst_id += self.out0_r_ack_mst_id
        self.decr.in0_slv_id += self.out0_r_ack_slv_id

        self.out0_r_ack_rdy   += self.decr.in0_rdy 




class DArbDual2(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node

        num              = len(self.node.src_list)
        req_pld_width    = node.network.req_pld_width
        ack_pld_width    = node.network.ack_pld_width
        master_id_width  = node.tgt_id_width
        slave_id_width   = node.src_id_width

        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))


        self.in_list = [self.create('in%s_req' % i, bundle_template.copy_reverse()) for i in range(num)]
        self.out = bundle_template.copy()

        w_req_bundle = BasicHdsk(node.src_id_width, node.tgt_id_width, node.txn_id_width, node.w_req_pld_width)
        w_ack_bundle = BasicHdsk(node.src_id_width, node.tgt_id_width, node.txn_id_width, node.w_ack_pld_width)
        r_req_bundle = BasicHdsk(node.src_id_width, node.tgt_id_width, node.txn_id_width, node.r_req_pld_width)
        r_ack_bundle = BasicHdsk(node.src_id_width, node.tgt_id_width, node.txn_id_width, node.r_ack_pld_width)

        self.in_w_req_list = [self.create('in%s_w_req' % i, w_req_bundle.copy_reverse()) for i in range(num)]
        self.in_r_req_list = [self.create('in%s_r_req' % i, r_req_bundle.copy_reverse()) for i in range(num)]
        self.in_w_ack_list = [self.create('in%s_w_ack' % i, w_ack_bundle.copy()) for i in range(num)]
        self.in_r_ack_list = [self.create('in%s_r_ack' % i, r_ack_bundle.copy()) for i in range(num)]

        self.out0_w_req = w_req_bundle.copy()
        self.out0_r_req = w_ack_bundle.copy()
        self.out0_w_ack = r_req_bundle.copy_reverse()
        self.out0_r_ack = r_ack_bundle.copy_reverse()


        self.warb = DArb(self.node, node.w_req_pld_width, id_type='slv')

        


    ###############################################################################################
    # Write
    ###############################################################################################

        # Forward Arb
        self.arb = DArb(self.node, req_pld_width, id_type='slv')

        self.arb.out0_rdy       += self.out0_req_rdy
        
        self.out0_req_vld      += self.arb.out0_vld     
        self.out0_req_head     += self.arb.out0_head    
        self.out0_req_tail     += self.arb.out0_tail    
        self.out0_req_pld      += self.arb.out0_pld     
        self.out0_req_mst_id   += self.arb.out0_mst_id  
        self.out0_req_slv_id   += self.arb.out0_slv_id  

        for i in range(num):
            self.arb.vld_list[i]     += self.in_req_vld_list[i]   
            self.arb.head_list[i]    += self.in_req_head_list[i]  
            self.arb.tail_list[i]    += self.in_req_tail_list[i]  
            self.arb.pld_list[i]     += self.in_req_pld_list[i]   
            self.arb.mst_id_list[i]  += self.in_req_mst_id_list[i]
            self.arb.slv_id_list[i]  += self.in_req_slv_id_list[i]

            self.in_req_rdy_list[i] += self.arb.rdy_list[i]

        # Backward Decode
        self.dec = DDec(self.node, ack_pld_width, id_type='slv')

        for i in range(num):
            self.in_ack_vld_list[i]     += self.dec.vld_list[i]   
            self.in_ack_head_list[i]    += self.dec.head_list[i]  
            self.in_ack_tail_list[i]    += self.dec.tail_list[i]  
            self.in_ack_pld_list[i]     += self.dec.pld_list[i]   
            self.in_ack_mst_id_list[i]  += self.dec.mst_id_list[i]
            self.in_ack_slv_id_list[i]  += self.dec.slv_id_list[i]

            self.dec.rdy_list[i]        += self.in_ack_rdy_list[i]


        self.dec.in0_vld    += self.out0_ack_vld   
        self.dec.in0_head   += self.out0_ack_head  
        self.dec.in0_tail   += self.out0_ack_tail  
        self.dec.in0_pld    += self.out0_ack_pld   
        self.dec.in0_mst_id += self.out0_ack_mst_id
        self.dec.in0_slv_id += self.out0_ack_slv_id

        self.out0_ack_rdy   += self.dec.in0_rdy 

    ###############################################################################################
    # Read
    ###############################################################################################


        # Forward Arb
        self.arbr = DArb(self.node, self.node.network.r_req_pld_width, id_type='slv')

        self.arbr.out0_rdy       += self.out0_r_req_rdy
        
        self.out0_r_req_vld      += self.arbr.out0_vld     
        self.out0_r_req_head     += self.arbr.out0_head    
        self.out0_r_req_tail     += self.arbr.out0_tail    
        self.out0_r_req_pld      += self.arbr.out0_pld     
        self.out0_r_req_mst_id   += self.arbr.out0_mst_id  
        self.out0_r_req_slv_id   += self.arbr.out0_slv_id  

        for i in range(num):
            self.arbr.vld_list[i]     += self.in_r_req_vld_list[i]   
            self.arbr.head_list[i]    += self.in_r_req_head_list[i]  
            self.arbr.tail_list[i]    += self.in_r_req_tail_list[i]  
            self.arbr.pld_list[i]     += self.in_r_req_pld_list[i]   
            self.arbr.mst_id_list[i]  += self.in_r_req_mst_id_list[i]
            self.arbr.slv_id_list[i]  += self.in_r_req_slv_id_list[i]

            self.in_r_req_rdy_list[i] += self.arbr.rdy_list[i]

        # Backward Decode
        self.decr = DDec(self.node, self.node.network.r_ack_pld_width, id_type='slv')

        for i in range(num):
            self.in_r_ack_vld_list[i]     += self.decr.vld_list[i]   
            self.in_r_ack_head_list[i]    += self.decr.head_list[i]  
            self.in_r_ack_tail_list[i]    += self.decr.tail_list[i]  
            self.in_r_ack_pld_list[i]     += self.decr.pld_list[i]   
            self.in_r_ack_mst_id_list[i]  += self.decr.mst_id_list[i]
            self.in_r_ack_slv_id_list[i]  += self.decr.slv_id_list[i]

            self.decr.rdy_list[i]        += self.in_r_ack_rdy_list[i]


        self.decr.in0_vld    += self.out0_r_ack_vld   
        self.decr.in0_head   += self.out0_r_ack_head  
        self.decr.in0_tail   += self.out0_r_ack_tail  
        self.decr.in0_pld    += self.out0_r_ack_pld   
        self.decr.in0_mst_id += self.out0_r_ack_mst_id
        self.decr.in0_slv_id += self.out0_r_ack_slv_id

        self.out0_r_ack_rdy   += self.decr.in0_rdy 
