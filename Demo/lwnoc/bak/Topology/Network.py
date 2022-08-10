
import networkx as nx
import matplotlib.pyplot as plt
from .Node import *
from .Edge import *


class Network(object):


    def __init__(self) -> None:
        self.G = nx.MultiDiGraph()
        self.slv_list = []
        self.mst_list = []
        self.switch_list = []

    def add(self, node):
        if isinstance(node, Slave):
            self.slv_list.append(node)
        elif isinstance(node, Master):
            self.mst_list.append(node)
        elif isinstance(node, Switch):
            self.switch_list.append(node)
        else:
            raise Exception()
        self.G.add_node(node)

    def link(self, src, dst):
        src.add_dst(dst)
        dst.add_src(src)
        self.G.add_node(src)
        self.G.add_node(dst)
        self.G.add_edge(src, dst)


    def _id_propagation(self):
        print(self.mst_list)
        print(self.slv_list)
        edge_pair_list = []
        for mst in self.mst_list:
            for slv in self.slv_list:
                for path in nx.all_simple_paths(self.G, source=slv, target=mst):
                    for i in range(1, len(path)):
                        edge_pair_list.append((path[i-1], path[i]))

        for src, dst in list(reversed(edge_pair_list)):
            if src.layer == 0 or src.layer > dst.layer -1:
                src.layer = dst.layer - 1

            src.global_id_list += dst.global_id_list
            src.global_id_list = list(set(src.global_id_list))
            print(src, src.layer)
            print(src.global_id_list)


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
    mst1.global_id_list = [1,2,3]
    mst2 = Master()
    mst2.global_id_list = [4,5,6]
    mst3 = Master()
    mst3.global_id_list = [7,8,9]

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