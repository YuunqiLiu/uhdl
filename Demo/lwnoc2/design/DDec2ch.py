# pylint: disable =unused-wildcard-import
from ....core import *
# pylint: enable  =unused-wildcard-import
from .Bundle import LwnocBundle
from .DDec import *
from .DArb import *



class DDec2ch(Component):

    def __init__(self, node, pld_type=LwnocBundle):
        super().__init__()

        channel_num = len(node.dst_list)

        # IO Define
        self.clk            = Input(UInt(1))
        self.rst_n          = Input(UInt(1))
        self.in0_req        = pld_type().reverse()
        self.in0_ack        = pld_type()
        self.out_req_list   = [self.set('out%s_req' % i, self.in0_req.reverse()) for i in range(channel_num)]
        self.out_ack_list   = [self.set('out%s_ack' % i, self.in0_ack.reverse()) for i in range(channel_num)]

        # Forward Decode
        self.u_dec = DDec(node, pld_type=LwnocBundle, forward=True)
        SmartAssign(self.u_dec.out_list,    self.out_req_list   )
        SmartAssign(self.u_dec.in0,         self.in0_req        )

        # Backward Arbitration
        self.u_arb = DArb(node, pld_type=LwnocBundle, forward=False)
        SmartAssign(self.u_arb.in_list,     self.out_ack_list   )
        SmartAssign(self.u_arb.out0,        self.in0_ack        )

        Assign(self.u_arb.clk,   self.clk    )
        Assign(self.u_arb.rst_n, self.rst_n  )

