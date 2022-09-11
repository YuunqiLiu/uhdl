

# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import
from .TopoNode import *

class DWrap(Component):

    def __init__(self, network):
        super().__init__()
        self.network = network
        self.src_inst_list = []
        self.tgt_inst_list = []

        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))

        for node in self.network.G.nodes():
            dnode = self.set(node.name, node.create_vinst())

            if isinstance(node, Slave):
                self.src_inst_list.append(dnode)
            elif isinstance(node, Master):
                self.tgt_inst_list.append(dnode)

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


        for src, tgt in self.network.G.edges():
            src_tgt_index = src.get_tgt_index(tgt)
            tgt_src_index = tgt.get_src_index(src)

            src_io_list = src.get_vinst().get_io('out%s_w' % src_tgt_index)
            tgt_io_list = tgt.get_vinst().get_io('in%s_w' % tgt_src_index)
            SmartAssign(src_io_list, tgt_io_list)

            src_io_list = src.get_vinst().get_io('out%s_r' % src_tgt_index)
            tgt_io_list = tgt.get_vinst().get_io('in%s_r' % tgt_src_index)
            SmartAssign(src_io_list, tgt_io_list)


    
            # print(src.name,tgt.name)
            # for sio, dio in zip(src_io_list, tgt_io_list):


            #     print(sio.name,dio.name)



            #     if isinstance(sio, Input):
            #         sio += dio
            #     elif isinstance(dio, Input):
            #         dio += sio
            #     else:
            #         raise Exception()
