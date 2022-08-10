# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import


class DMst(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node

        self.in0_vld = Input(UInt(1))
        self.in0_rdy = Output(UInt(1))
        self.in0_head = Input(UInt(1))
        self.in0_tail = Input(UInt(1))
        self.in0_pld = Input(UInt(self.node.src_width))
        self.in0_id = Input(UInt(self.node.id_width))

        self.out0_vld = Output(UInt(1))
        self.out0_rdy = Input(UInt(1))
        self.out0_head = Output(UInt(1))
        self.out0_tail = Output(UInt(1))
        self.out0_pld = Output(UInt(self.node.dst_width))
        self.out0_id = Output(UInt(self.node.id_width))

        self.out0_vld += self.in0_vld
        self.in0_rdy += self.out0_rdy
        self.out0_head += self.in0_head
        self.out0_tail += self.in0_tail
        self.out0_pld += self.in0_pld
        self.out0_id += self.in0_id