# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import

from .mapping import topo_impl_mapping_dict

class LwnocWrap(Component):

    def __init__(self, N):
        super().__init__()

        for i, node in enumerate(N.G.nodes()):
            print(type(node))


            print(topo_impl_mapping_dict[type(node)])

            impl_type = topo_impl_mapping_dict[type(node)]
            print(node)

            self.set("t%s" % i, impl_type(4, 32))

