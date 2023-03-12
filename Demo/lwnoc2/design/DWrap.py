

# pylint: disable =unused-wildcard-import
from ....core import *
# pylint: enable  =unused-wildcard-import
from ..TopoNode import *

class DWrap(Component):

    def __init__(self, network):
        super().__init__()
        self.network = network
        self.src_inst_list = []
        self.tgt_inst_list = []

        self.clk    = Input(UInt(1))
        self.rst_n  = Input(UInt(1))

        for node in self.network.G.nodes():
            dnode = self.set(node.name, node.create_vinst())

            if isinstance(node, Slave):
                self.src_inst_list.append(dnode)
            elif isinstance(node, Master):
                self.tgt_inst_list.append(dnode)

            # try to connect clk and rst_n
            if hasattr(dnode, 'clk'):
                dclk = dnode.get('clk')
                dclk += self.clk
            if hasattr(dnode, 'rst_n'):
                drstn = dnode.get('rst_n')
                drstn += self.rst_n

        for slv in self.src_inst_list:
            self.expose_io(slv.get_io('in'))

        for mst in self.tgt_inst_list:
            self.expose_io(mst.get_io('out'))

        for dep, dst in self.network.G.edges():
            dep_io_list = dep.get_vinst().get_io('out%s' % dep.get_dst_route_id(dst))
            dst_io_list = dst.get_vinst().get_io('in%s' % dst.get_dep_route_id(dep))
            SmartAssign(dep_io_list, dst_io_list)

            #src_io_list = src.get_vinst().get_io('out%s_r' % src_tgt_index)
            #tgt_io_list = tgt.get_vinst().get_io('in%s_r' % tgt_src_index)
            #SmartAssign(src_io_list, tgt_io_list)


