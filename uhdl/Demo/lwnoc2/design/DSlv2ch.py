# pylint: disable =unused-wildcard-import
from ....core import *
# pylint: enable  =unused-wildcard-import

from .Bundle import LwnocBundle


class DSlv2ch(Component):

    def __init__(self, node, fwd_pld_type=LwnocBundle, bwd_pld_type=LwnocBundle, forward=True):
        super().__init__()
        self.topo_node = node

        #tgt_list                = self.topo_node.get_tgt_list(forward)
        #tgt_id_route_id_dict    = self.topo_node.get_tgt_id_route_id_dict(forward)
        #channel_num             = len(tgt_list)

        # IO Define
        self.in0_req        = fwd_pld_type().reverse()
        self.in0_ack        = bwd_pld_type()
        self.out0_req       = self.in0_req.reverse()
        self.out0_ack       = self.in0_ack.reverse()

        SmartAssign(self.in0_req, self.out0_req )
        SmartAssign(self.in0_ack, self.out0_ack )

        


        #out_exclude_vld_rdy = [var.as_list(exclude=['rdy', 'vld']) for var in self.out_list]
        #in_exlucde_vld_rdy = self.in0.as_list(exclude=['rdy', 'vld'])

        #for out_bundle in out_exclude_vld_rdy:
        #    for i, out_slice in enumerate(out_bundle):
        #        out_slice += in_exlucde_vld_rdy[i]

