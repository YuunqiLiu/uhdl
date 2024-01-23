# pylint: disable =unused-wildcard-import
from ....core import *
# pylint: enable  =unused-wildcard-import
from .Bundle import LwnocBundle
from .DDec import *
from .DArb import *



class DArb2ch(Component):

    def __init__(self, node, fwd_pld_type=LwnocBundle, bwd_pld_type=LwnocBundle):
        super().__init__()

        channel_num = len(node.dep_list)

        # IO Define
        self.clk            = Input(UInt(1))
        self.rst_n          = Input(UInt(1))
        self.out0_req       = fwd_pld_type()
        self.out0_ack       = bwd_pld_type().reverse()
        self.in_req_list    = [self.set('in%s_req' % i, self.out0_req.reverse()) for i in range(channel_num)]
        self.in_ack_list    = [self.set('in%s_ack' % i, self.out0_ack.reverse()) for i in range(channel_num)]

        # Forward Arbitration
        self.u_arb = DArb(node, pld_type=fwd_pld_type, forward=True)
        SmartAssign(self.u_arb.in_list,     self.in_req_list   )
        SmartAssign(self.u_arb.out0,        self.out0_req      )

        # Backward Decode
        self.u_dec = DDec(node, pld_type=bwd_pld_type, forward=False)
        SmartAssign(self.u_dec.out_list,    self.in_ack_list   )
        SmartAssign(self.u_dec.in0,         self.out0_ack      )

        Assign(self.u_arb.clk,   self.clk    )
        Assign(self.u_arb.rst_n, self.rst_n  )

