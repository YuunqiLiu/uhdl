
import networkx as nx
import matplotlib.pyplot as plt
from .TopoEdge import *
from .TopoNode import *

from .TopoLogging import *

class Network(object):

    def __init__(self, name='network0') -> None:
        self.name = name
        self.logger = init_logger(self.name)
        
        self.G = nx.MultiDiGraph()

        self.txn_id_width = 8
        self.src_id_width = 4
        self.tgt_id_width = 4
        self.addr_width = 32
        self.user_width = 32
        self.data_width = 256
        #self.ack_user_width = 0

        self.src_list = []
        self.tgt_list = []
        self.switch_list = []
        self.node_list = []
        #self.global_master_id_list = []
        self._global_master_id_list = []
        self._global_slave_id_list = []
        self._global_address_range_dict = {}
        self._global_address_range_id_map_dict = {}

        self._sam_addrrange_tgtid_dict = {}

        self._src_id_list = []
        self._dst_id_list = []




    @property
    def _global_id_address_range_map_dict(self):
        return dict(zip(self._global_address_range_id_map_dict.values(), self._global_address_range_id_map_dict.keys()))

    def add(self, node):
        if isinstance(node, Slave):
            self.src_list.append(node)
        elif isinstance(node, Master):
            self.tgt_list.append(node)
        elif isinstance(node, Switch):
            self.switch_list.append(node)
        else:
            raise Exception()
        self.logger.info('add %s to network.' % node)
        self.node_list.append(node)
        node.network = self
        self.G.add_node(node)

    def link(self, src, dst):
        self.logger.info('link %s to %s.' % (src, dst))
        src.add_dst(dst)
        dst.add_src(src)
        self.G.add_node(src)
        self.G.add_node(dst)
        self.G.add_edge(src, dst)





    def _src_id_propagation(self):
        self.logger.info('src id propagation start.')
        G_reverse = self.G.reverse(copy=False)

        # get all edge's src-dst pair with BFM search.
        edge_pair_list = []
        for src in self.src_list:
            for tgt in self.tgt_list:
                for path in nx.all_simple_paths(G_reverse, source=tgt, target=src):
                    self.logger.info('Find a backward path: %s' % [x.name for x in path])
                    for i in range(1, len(path)):
                        edge_pair_list.append((path[i-1], path[i]))
        

        # foward propagate src id from edge src to dst
        for src, dst in list(reversed(edge_pair_list)):
            self.logger.info('%s reachable src id update from %s.' % (src.name, dst.name))
            self.logger.info('%s src id list: %s' % (dst.name, dst.reachable_src_id_list))
            self.logger.info('%s src id list before update: %s' % (src.name, src.reachable_src_id_list))

            src.reachable_src_id_list += dst.reachable_src_id_list
            src.reachable_src_id_list = list(set(src.reachable_src_id_list))

            self.logger.info('%s src id list after update: %s' % (src.name, src.reachable_src_id_list))

        #max_useful_slave_id_width = len(format(max(self._global_master_id_list), "b"))
        self.logger.info('src id propagation finish.')



    def _tgt_id_propagation(self):
        self.logger.info('tgt id propagation start.')

        # get all edge's src-dst pair with BFM search.
        edge_pair_list = []
        for tgt in self.tgt_list:
            for src in self.src_list:
                for path in nx.all_simple_paths(self.G, source=src, target=tgt):
                    self.logger.info('Find a forward path: %s' % [x.name for x in path])
                    for i in range(1, len(path)):
                        edge_pair_list.append((path[i-1], path[i]))

        # back propagate master id from edge dst to src
        for src, dst in list(reversed(edge_pair_list)):
            self.logger.info('%s reachable tgt id update from %s.' % (src.name, dst.name))
            self.logger.info('%s tgt id list: %s' % (dst.name, dst.reachable_tgt_id_list))
            self.logger.info('%s tgt id list before update: %s' % (src.name, src.reachable_tgt_id_list))

            src.reachable_tgt_id_list += dst.reachable_tgt_id_list
            src.reachable_tgt_id_list = list(set(src.reachable_tgt_id_list))

            self.logger.info('%s tgt id list after update: %s' % (src.name, src.reachable_tgt_id_list))

        # set layer for GUI plan.
        for src, dst in list(reversed(edge_pair_list)):
            if src.layer == 0 or src.layer > dst.layer -1:
                src.layer = dst.layer - 1

        self.logger.info('tgt id propagation finish.')


    def _generate_system_address_mapping(self):
        self.logger.info('System address mapping generation start.')
        self._sam_addrrange_tgtid_dict = {}
        for tgt in self.tgt_list:
            for addr_range in tgt.address_range_list:
                self.logger.info('Find a mapping: %s -> %s' %(addr_range, tgt.tgt_id))
                self._sam_addrrange_tgtid_dict[addr_range] = tgt.tgt_id

    def _generate_local_port_id_mapping(self):
        for node in self.node_list:
            node._generate_local_port_id_mapping()





    def _report(self):
        for node in self.node_list:
            node.report()


    def _show(self):
        for src in self.src_list:
            src.layer = -100

        for node in self.G.nodes():
            self.G.nodes[node]['layer'] = node.layer

        pos = nx.multipartite_layout(self.G, subset_key="layer")
        plt.figure(figsize=(8, 8))

        color = [x.color for x in self.src_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.src_list, node_size = 3000, node_shape ='s')

        color = [x.color for x in self.tgt_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.tgt_list, node_size = 3000, node_shape ='s')

        color = [x.color for x in self.switch_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.switch_list, node_size =3000, node_shape ='o')

        nx.draw_networkx_edges(self.G, pos, node_size=2400, node_shape='s')
        nx.draw_networkx_labels(self.G, pos, font_color="black")
        plt.axis("equal")
        plt.show()


    def __str__(self):
        return self.name




    # @property
    # def w_req_pld_width(self):
    #     return self.data_width + int(self.data_width/8) + self.user_width + self.addr_width

    # @property
    # def r_req_pld_width(self):
    #     return self.user_width + self.addr_width

    # @property
    # def w_ack_pld_width(self):
    #     return 2

    # @property
    # def r_ack_pld_width(self):
    #     return 2 + self.data_width + 1



if __name__ == "__main__":
    src1 = Slave()
    src2 = Slave()
    src3 = Slave()

    arb1 = Arbiter()
    arb2 = Arbiter()
    arb3 = Arbiter()

    dec1 = Decoder()
    dec2 = Decoder()

    tgt1 = Master()
    tgt1.global_master_id_list = [1,2,3]
    tgt2 = Master()
    tgt2.global_master_id_list = [4,5,6]
    tgt3 = Master()
    tgt3.global_master_id_list = [7,8,9]

    N = Network()
    N.add(src1)
    N.add(src2)
    N.add(src3)
    N.add(arb1)
    N.add(dec1)
    N.add(dec2)
    N.add(tgt1)
    N.add(tgt2)
    N.add(arb2)
    N.add(arb3)

    N.link(src2, arb1)
    N.link(src3, arb1)

    N.link(arb1, dec1)
    N.link(src1, dec2)
    N.link(dec1, arb2)
    N.link(dec1, arb3)
    N.link(dec2, arb2)
    N.link(dec2, arb3)

    N.link(arb2, tgt1)
    N.link(arb3, tgt2)


    N._id_propagation()
    N._show()



    # def _address_to_global_id_mapping(self):
    #     global_address_range_list = []
    #     for tgt in self.tgt_list:
    #         if isinstance(tgt, MasterAxi):
    #             raise Exception()
    #         for tgt_addr_range in tgt.address_range_list:
    #             if tgt_addr_range in global_address_range_list:
    #                 raise Exception()
    #             global_address_range_list.append(tgt_addr_range)



        #print(global_address_range_list)

        #self.slave_id_width     = 4
        #self.master_id_width    = 4
        #self.slave_axi_id_width = 8
        #self.master_axi_id_width = self.slave_id_width + self.slave_axi_id_width
        #self.axi_id_width = 8
        #self.id_width = 8



            # update master id list to network global list
           # self._global_master_id_list += dst.global_master_id_list
           # self._global_master_id_list = list(set(self._global_master_id_list))

        # set master id width
        #max_id = max(self._global_master_id_list)
        #max_id_width = len(format(max_id, "b"))

        #print(max_id_width)

        #for node in self.G.nodes():
        #    node.id_width = max_id_width


#     def _collect_init_global_master_id_list(self):
#         for tgt in self.tgt_list:
#             for tgt_global_id in tgt.global_master_id_list:
#                 if tgt_global_id in self._global_master_id_list:
#                     raise Exception()
#                 self._global_master_id_list.append(tgt_global_id)


#     def _collect_global_address_range_dict(self):
#         for tgt in self.tgt_list:
#             #if isinstance(tgt, MasterAxi):
#             #    raise Exception()
#             for tgt_addr_range in tgt.address_range_list:
#                 if tgt_addr_range in self._global_address_range_dict.keys():
#                     raise Exception()
#                 self._global_address_range_dict[tgt_addr_range] = tgt


#     def _map_address_range_to_global_id(self):
#         max_id = max(self._global_master_id_list+[0])
#         max_id_count = max_id + 1
#         for addr_range, tgt in self._global_address_range_dict.items():
#             self._global_address_range_id_map_dict[addr_range] = max_id_count
#             tgt.global_master_id_list.append(max_id_count)
#             max_id_count += 1