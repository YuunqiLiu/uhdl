# pylint: disable =unused-wildcard-import
from ....core import *
# pylint: enable  =unused-wildcard-import

from .Bundle import LwnocBundle


class DDec(Component):

    def __init__(self, node, pld_type=LwnocBundle, forward=True):
        super().__init__()
        self.topo_node = node

        tgt_list                = self.topo_node.get_tgt_list(forward)
        tgt_id_route_id_dict    = self.topo_node.get_tgt_id_route_id_dict(forward)
        channel_num             = len(tgt_list)

        # IO Define
        self.in0        = pld_type().reverse()
        self.out_list   = [self.set('out%s' % i, self.in0.reverse()) for i in range(channel_num)]


        # Valid Generation
        # for a normal decoder, the Valid signal should only propagate to 1 output port.
        # this port is select by tgt_id.
        # 
        # tgt_id_route_id_dict is a dict which record target id -> route_id mapping like this:
        #
        # +-----------+----------+
        # | target id | route id |
        # +-----------+----------+
        # |     0     |    0     |
        # |     1     |    0     |
        # |    ...    |   ...    |
        # |     5     |    1     |
        # +-----------+----------+
        # 
        # we have to impl a mask vector to mask valid signal from input valid to output valid according to this table.
        #
        route_id_hit_list_list = [[] for x in range(channel_num)]
        #for route_id in range(channel_num):
        #    route_id_hit_list_list[route_id] = []

        for tgt_id, route_id in tgt_id_route_id_dict.items():
            hit = self.set("hit_tgtid_%s__to_rteid_%s" % (tgt_id,route_id), Wire(UInt(1)))
            Assign(hit, Equal(self.in0.tgt_id,UInt(self.in0.tgt_id.attribute.width,tgt_id)))
            route_id_hit_list_list[route_id].append(hit)


        masked_rdy_list = []
        for route_id in range(channel_num):
            channel_mask = self.set("channel_mask_%s" % route_id , Wire(UInt(1)))
            Assign(channel_mask, OrList(*route_id_hit_list_list[route_id]))
            Assign(self.out_list[route_id].vld, And(self.in0.vld, channel_mask ))

            masked_rdy = self.set("masked_rdy_%s" % route_id , Wire(UInt(1)))
            Assign(masked_rdy, And(self.out_list[route_id].rdy, channel_mask))
            masked_rdy_list.append(masked_rdy)
                   
        Assign(self.in0.rdy, OrList(*masked_rdy_list))


        out_exclude_vld_rdy = [var.as_list(exclude=['rdy', 'vld']) for var in self.out_list]
        in_exlucde_vld_rdy = self.in0.as_list(exclude=['rdy', 'vld'])

        for out_bundle in out_exclude_vld_rdy:
            for i, out_slice in enumerate(out_bundle):
                out_slice += in_exlucde_vld_rdy[i]

