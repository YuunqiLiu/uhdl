
import networkx as nx
import matplotlib.pyplot as plt
from .TopoEdge import *
from .TopoNode import *


class Network(object):

    def __init__(self) -> None:
        self.G = nx.MultiDiGraph()
        self.slave_id_width = 4
        self.master_id_width = 4
        self.slave_axi_id_width = 8
        self.master_axi_id_width = self.slave_id_width + self.slave_axi_id_width

        #self.axi_id_width = 8
        #self.id_width = 8
        self.addr_width = 32
        self.user_width = 32
        self.data_width = 256
        self.ack_user_width = 0


        self.req_pld_width = self.data_width + int(self.data_width/8) + self.slave_axi_id_width + self.user_width + self.addr_width
        self.r_req_pld_width = self.slave_axi_id_width + self.user_width + self.addr_width
        self.ack_pld_width = self.slave_axi_id_width + 2 + self.ack_user_width
        self.r_ack_pld_width = self.slave_axi_id_width + 2 + self.ack_user_width + self.data_width
        
        self.slv_list = []
        self.mst_list = []
        self.switch_list = []
        self.node_list = []
        #self.global_master_id_list = []
        self.name = 'network0'
        self._global_master_id_list = []
        self._global_slave_id_list = []
        self._global_address_range_dict = {}
        self._global_address_range_id_map_dict = {}


    @property
    def _global_id_address_range_map_dict(self):
        return dict(zip(self._global_address_range_id_map_dict.values(), self._global_address_range_id_map_dict.keys()))

    def add(self, node):
        if isinstance(node, Slave):
            self.slv_list.append(node)
        elif isinstance(node, Master):
            self.mst_list.append(node)
        elif isinstance(node, Switch):
            self.switch_list.append(node)
        else:
            raise Exception()
        print('add %s to node_list' % node)
        self.node_list.append(node)
        node.network = self
        self.G.add_node(node)

    def link(self, src, dst):
        src.add_dst(dst)
        dst.add_src(src)
        self.G.add_node(src)
        self.G.add_node(dst)
        self.G.add_edge(src, dst)


    def _slave_id_propagation(self):
        print('slave id propagation.')
        G_reverse = self.G.reverse(copy=False)

        # get all edge's src-dst pair with BFM search.
        edge_pair_list = []
        for slv in self.slv_list:
            for mst in self.mst_list:
                for path in nx.all_simple_paths(G_reverse, source=mst, target=slv):
                    for i in range(1, len(path)):
                        edge_pair_list.append((path[i-1], path[i]))
        
        # back propagate slvae id from edge dst to src
        for src, dst in list(reversed(edge_pair_list)):
            src.global_slave_id_list += dst.global_slave_id_list
            src.global_slave_id_list = list(set(src.global_slave_id_list))

            # update slave id list to network global list
            self._global_slave_id_list += dst.global_slave_id_list
            self._global_slave_id_list = list(set(self._global_slave_id_list))

        max_useful_slave_id_width = len(format(max(self._global_master_id_list), "b"))


    def _master_id_propagation(self):
        print('master id propagation.')

        # get all edge's src-dst pair with BFM search.
        edge_pair_list = []
        for mst in self.mst_list:
            for slv in self.slv_list:
                for path in nx.all_simple_paths(self.G, source=slv, target=mst):
                    for i in range(1, len(path)):
                        edge_pair_list.append((path[i-1], path[i]))

        # back propagate master id from edge dst to src
        for src, dst in list(reversed(edge_pair_list)):
            src.global_master_id_list += dst.global_master_id_list
            src.global_master_id_list = list(set(src.global_master_id_list))

            # update master id list to network global list
            self._global_master_id_list += dst.global_master_id_list
            self._global_master_id_list = list(set(self._global_master_id_list))

        # set master id width
        max_id = max(self._global_master_id_list)
        max_id_width = len(format(max_id, "b"))

        #print(max_id_width)

        for node in self.G.nodes():
            node.id_width = max_id_width


        # set layer for GUI plan.
        for src, dst in list(reversed(edge_pair_list)):
            if src.layer == 0 or src.layer > dst.layer -1:
                src.layer = dst.layer - 1


           # print(src, src.layer)
           # print(src.global_master_id_list)
            #print(dst.global_master_id_list)


    def _collect_init_global_master_id_list(self):
        for mst in self.mst_list:
            for mst_global_id in mst.global_master_id_list:
                if mst_global_id in self._global_master_id_list:
                    raise Exception()
                self._global_master_id_list.append(mst_global_id)


    def _collect_global_address_range_dict(self):
        for mst in self.mst_list:
            #if isinstance(mst, MasterAxi):
            #    raise Exception()
            for mst_addr_range in mst.address_range_list:
                if mst_addr_range in self._global_address_range_dict.keys():
                    raise Exception()
                self._global_address_range_dict[mst_addr_range] = mst


    def _map_address_range_to_global_id(self):
        max_id = max(self._global_master_id_list+[0])
        max_id_count = max_id + 1
        for addr_range, mst in self._global_address_range_dict.items():
            self._global_address_range_id_map_dict[addr_range] = max_id_count
            mst.global_master_id_list.append(max_id_count)
            max_id_count += 1


    def _report(self):
        for node in self.node_list:
            node.report()


    def _show(self):
        for slv in self.slv_list:
            slv.layer = -100

        for node in self.G.nodes():
            self.G.nodes[node]['layer'] = node.layer

        pos = nx.multipartite_layout(self.G, subset_key="layer")
        plt.figure(figsize=(8, 8))

        color = [x.color for x in self.slv_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.slv_list, node_size = 3000, node_shape ='s')

        color = [x.color for x in self.mst_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.mst_list, node_size = 3000, node_shape ='s')

        color = [x.color for x in self.switch_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.switch_list, node_size =3000, node_shape ='o')

        nx.draw_networkx_edges(self.G, pos, node_size=2400, node_shape='s')
        nx.draw_networkx_labels(self.G, pos, font_color="black")
        plt.axis("equal")
        plt.show()


    def __str__(self):
        return self.name


if __name__ == "__main__":
    slv1 = Slave()
    slv2 = Slave()
    slv3 = Slave()

    arb1 = Arbiter()
    arb2 = Arbiter()
    arb3 = Arbiter()

    dec1 = Decoder()
    dec2 = Decoder()

    mst1 = Master()
    mst1.global_master_id_list = [1,2,3]
    mst2 = Master()
    mst2.global_master_id_list = [4,5,6]
    mst3 = Master()
    mst3.global_master_id_list = [7,8,9]

    N = Network()
    N.add(slv1)
    N.add(slv2)
    N.add(slv3)
    N.add(arb1)
    N.add(dec1)
    N.add(dec2)
    N.add(mst1)
    N.add(mst2)
    N.add(arb2)
    N.add(arb3)

    N.link(slv2, arb1)
    N.link(slv3, arb1)

    N.link(arb1, dec1)
    N.link(slv1, dec2)
    N.link(dec1, arb2)
    N.link(dec1, arb3)
    N.link(dec2, arb2)
    N.link(dec2, arb3)

    N.link(arb2, mst1)
    N.link(arb3, mst2)


    N._id_propagation()
    N._show()



    # def _address_to_global_id_mapping(self):
    #     global_address_range_list = []
    #     for mst in self.mst_list:
    #         if isinstance(mst, MasterAxi):
    #             raise Exception()
    #         for mst_addr_range in mst.address_range_list:
    #             if mst_addr_range in global_address_range_list:
    #                 raise Exception()
    #             global_address_range_list.append(mst_addr_range)



        #print(global_address_range_list)