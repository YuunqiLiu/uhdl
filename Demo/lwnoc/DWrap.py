

# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import
from .TopoNode import *

class DWrap(Component):

    def __init__(self, network):
        super().__init__()
        self.network = network
        self.slv_inst_list = []
        self.mst_inst_list = []


        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))

        for node in self.network.G.nodes():
            dnode = self.set(node.name, node.create_vinst())

            if isinstance(node, Slave):
                self.slv_inst_list.append(dnode)
            elif isinstance(node, Master):
                self.mst_inst_list.append(dnode)

            if hasattr(dnode,'clk'):
                dclk = dnode.get('clk')
                dclk += self.clk
            if hasattr(dnode, 'rst_n'):
                drstn = dnode.get('rst_n')
                drstn += self.rst_n



        for slv in self.slv_inst_list:
            self.expose_io(slv.get_io('in'))

        for mst in self.mst_inst_list:
            self.expose_io(mst.get_io('out'))


        for src, dst in self.network.G.edges():
            src_dst_index = src.get_dst_index(dst)
            dst_src_index = dst.get_src_index(src)

            src_io_list = src.get_vinst().get_io('out%s' % src_dst_index)
            dst_io_list = dst.get_vinst().get_io('in%s' % dst_src_index)


            print(src.name,dst.name)
            for sio, dio in zip(src_io_list, dst_io_list):
                print(sio.name,dio.name)
                #print(sio, dio)
                #print(sio.attribute, dio.attribute)
                #print(sio.full_name(), dio.full_name())
                if isinstance(sio, Input):
                    sio += dio
                elif isinstance(dio, Input):
                    dio += sio
                else:
                    raise Exception()
                #print(sio, dio)
            #print(src.get_vinst(),dst.get_vinst())