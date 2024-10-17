
import networkx as nx
import matplotlib.pyplot as plt
from .TopoNode          import *
from .TopoLogging       import *
from .design.DWrap      import DWrap
from .design.Bundle     import LwnocBundle


class Network(object):

    def __init__(self, name='network0') -> None:
        self.name                       = name
        self.logger                     = init_logger(self.name)
        self.G                          = nx.MultiDiGraph()

        self.txn_id_width               = 8
        self.node_id_width              = 8

        self.slave_list                 = []
        self.master_list                = []
        self.switch_list                = []
        self.node_list                  = []
        self.rtl_prefix                 = ''
        self.default_interface_forward  = LwnocBundle
        self.default_interface_backward = LwnocBundle
        self._design                    = None
        self._lock_arbiter              = True


    def add(self, node):
        if isinstance(node, Slave):
            self.slave_list.append(node)
        elif isinstance(node, Master):
            self.master_list.append(node)
        elif isinstance(node, Switch):
            self.switch_list.append(node)
        else:
            raise Exception()
        self.logger.info('add %s to network.' % node)
        self.node_list.append(node)
        node.network = self
        node._father = self
        self.G.add_node(node)


    def link(self, src, dst):
        self.logger.info('link %s to %s.' % (src, dst))
        src.add_dst(dst)
        dst.add_dep(src)
        self.G.add_node(src)
        self.G.add_node(dst)
        self.G.add_edge(src, dst)


    def _report(self):
        for node in self.node_list:
            node.report()


    def _show(self):
        self.logger.info('network topology graphic generation start.')

        for slave in self.slave_list:
            slave.layer = -100
            self.logger.info('set %s nx_layer to -100.' % slave)

        for master in self.master_list:
            master.layer = 100
            self.logger.info('set %s nx_layer to 100.' % master)

        for node in self.G.nodes():
            self.G.nodes[node]['layer'] = node.layer

        #G = nx.complete_graph(4)



        pos = nx.nx_pydot.pydot_layout(self.G)
        pos = nx.nx_pydot.pydot_layout(self.G, prog="dot")
        pos = nx.nx_pydot.graphviz_layout(self.G, prog="dot")

        print(pos)

        #pos = nx.spiral_layout(self.G)
        #pos = nx.planar_layout(self.G)
        

        #pos = nx.multipartite_layout(self.G, subset_key="layer")
        plt.figure(figsize=(8, 8))

        color = [x.color for x in self.slave_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.slave_list, node_size = 3000, node_shape ='s')

        color = [x.color for x in self.master_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.master_list, node_size = 3000, node_shape ='s')

        color = [x.color for x in self.switch_list]
        nx.draw_networkx_nodes(self.G, pos, node_color=color, nodelist=self.switch_list, node_size =3000, node_shape ='o')

        nx.draw_networkx_edges(self.G, pos, node_size=2400, node_shape='s')
        nx.draw_networkx_labels(self.G, pos, font_color="black")
        plt.axis("equal")
        #plt.show()
        plt.savefig("%s.topology.png" % self, format='PNG')


    def __str__(self):
        return self.name

    @property
    def lock_arbiter(self):
        return self._lock_arbiter


    def generate_verilog(self):
        #design = DWrap(self)
        if(self._design is None):
            self._design = DWrap(self)
        self._design.set_module_name_prefix(self.rtl_prefix)
        self._design.generate_verilog(iteration=True)
        self._design.generate_filelist(prefix='$PRJ_ICDIR/',name='%s_flist.f' % self.rtl_prefix)



        #self.node_id_width  = 8
        #self.addr_width = 32
        #self.user_width = 32
        #self.data_width = 256
        #self.ack_user_width = 0


        #self.global_master_id_list = []
        #self._global_master_id_list = []
        #self._global_slave_id_list = []
        #self._global_address_range_dict = {}
        #self._global_address_range_id_map_dict = {}

        #self._sam_addrrange_tgtid_dict = {}

        #self._src_id_list = []
        #self._dst_id_list = []




    #@property
    #def _global_id_address_range_map_dict(self):
    #    return dict(zip(self._global_address_range_id_map_dict.values(), self._global_address_range_id_map_dict.keys()))





    # def _src_id_propagation(self):
    #     self.logger.info('src id propagation start.')
    #     G_reverse = self.G.reverse(copy=False)

    #     # get all edge's src-dst pair with BFM search.
    #     edge_pair_list = []
    #     for src in self.slave_list:
    #         for tgt in self.master_list:
    #             for path in nx.all_simple_paths(G_reverse, source=tgt, target=src):
    #                 self.logger.info('Find a backward path: %s' % [x.name for x in path])
    #                 for i in range(1, len(path)):
    #                     edge_pair_list.append((path[i-1], path[i]))
    #     

    #     # foward propagate src id from edge src to dst
    #     for src, dst in list(reversed(edge_pair_list)):
    #         self.logger.info('%s reachable src id update from %s.' % (src.name, dst.name))
    #         self.logger.info('%s src id list: %s' % (dst.name, dst.reachable_src_id_list))
    #         self.logger.info('%s src id list before update: %s' % (src.name, src.reachable_src_id_list))

    #         src.reachable_src_id_list += dst.reachable_src_id_list
    #         src.reachable_src_id_list = list(set(src.reachable_src_id_list))

    #         self.logger.info('%s src id list after update: %s' % (src.name, src.reachable_src_id_list))

    #     #max_useful_slave_id_width = len(format(max(self._global_master_id_list), "b"))
    #     self.logger.info('src id propagation finish.')



    # def _tgt_id_propagation(self):
    #     self.logger.info('tgt id propagation start.')

    #     # get all edge's src-dst pair with BFM search.
    #     edge_pair_list = []
    #     for tgt in self.master_list:
    #         for src in self.slave_list:
    #             for path in nx.all_simple_paths(self.G, source=src, target=tgt):
    #                 self.logger.info('Find a forward path: %s' % [x.name for x in path])
    #                 for i in range(1, len(path)):
    #                     edge_pair_list.append((path[i-1], path[i]))

    #     # back propagate master id from edge dst to src
    #     for src, dst in list(reversed(edge_pair_list)):
    #         self.logger.info('%s reachable tgt id update from %s.' % (src.name, dst.name))
    #         self.logger.info('%s tgt id list: %s' % (dst.name, dst.reachable_tgt_id_list))
    #         self.logger.info('%s tgt id list before update: %s' % (src.name, src.reachable_tgt_id_list))

    #         src.reachable_tgt_id_list += dst.reachable_tgt_id_list
    #         src.reachable_tgt_id_list = list(set(src.reachable_tgt_id_list))

    #         self.logger.info('%s tgt id list after update: %s' % (src.name, src.reachable_tgt_id_list))

    #     # set layer for GUI plan.
    #     for src, dst in list(reversed(edge_pair_list)):
    #         if src.layer == 0 or src.layer > dst.layer -1:
    #             src.layer = dst.layer - 1

    #     self.logger.info('tgt id propagation finish.')


    # def _generate_system_address_mapping(self):
    #     self.logger.info('System address mapping generation start.')
    #     self._sam_addrrange_tgtid_dict = {}
    #     for tgt in self.master_list:
    #         for addr_range in tgt.address_range_list:
    #             self.logger.info('Find a mapping: %s -> %s' %(addr_range, tgt.tgt_id))
    #             self._sam_addrrange_tgtid_dict[addr_range] = tgt.tgt_id

    # def _generate_local_port_id_mapping(self):
    #     for node in self.node_list:
    #         node._generate_local_port_id_mapping()
