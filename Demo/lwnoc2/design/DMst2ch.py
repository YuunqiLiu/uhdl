# pylint: disable =unused-wildcard-import
from ....core import *
# pylint: enable  =unused-wildcard-import

from .Bundle import LwnocBundle


class DMst2ch(Component):

    def __init__(self, node, pld_type=LwnocBundle, forward=True):
        super().__init__()
        self.topo_node = node

        #tgt_list                = self.topo_node.get_tgt_list(forward)
        #tgt_id_route_id_dict    = self.topo_node.get_tgt_id_route_id_dict(forward)
        #channel_num             = len(tgt_list)

        # IO Define
        self.in0        = pld_type().reverse()
        self.out0       = self.in0.reverse()

        SmartAssign(self.in0, self.out0)

        


        #out_exclude_vld_rdy = [var.as_list(exclude=['rdy', 'vld']) for var in self.out_list]
        #in_exlucde_vld_rdy = self.in0.as_list(exclude=['rdy', 'vld'])

        #for out_bundle in out_exclude_vld_rdy:
        #    for i, out_slice in enumerate(out_bundle):
        #        out_slice += in_exlucde_vld_rdy[i]

