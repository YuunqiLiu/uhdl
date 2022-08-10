# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import


class DDec(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node

        num = len(self.node.dst_list)
        pld_width = node.pld_width
        id_width = node.id_width

        self.vld_list = []
        self.rdy_list = []
        self.head_list = []
        self.tail_list = []
        self.pld_list = []
        self.id_list = []

        # Create Output
        for i in range(num):
            self.vld_list.append(self.create('out%s_vld' % i, Output(UInt(1))))
            self.rdy_list.append(self.create('out%s_rdy' % i, Input(UInt(1))))
            self.head_list.append(self.create('out%s_head' % i, Output(UInt(1))))
            self.tail_list.append(self.create('out%s_tail' % i, Output(UInt(1))))
            self.pld_list.append(self.create('out%s_pld' % i, Output(UInt(pld_width))))
            self.id_list.append(self.create('out%s_id' % i, Output(UInt(id_width))))

        # Create Input
        self.in0_vld = Input(UInt(1))
        self.in0_rdy = Output(UInt(1))
        self.in0_head = Input(UInt(1))
        self.in0_tail = Input(UInt(1))
        self.in0_pld = Input(UInt(pld_width))
        self.in0_id = Input(UInt(id_width))

        # bin2onehot
        self.rdy_masked_list = []
        for i, dst in enumerate(self.node.dst_list):
            id_hit_list = []
            for gid in dst.global_id_list:
                id_hit = self.create("id_hit_p%s_id%s" % (i,gid), Wire(UInt(1)))
                id_hit += Equal(self.in0_id, UInt(id_width, gid))
                id_hit_list.append(id_hit)

            sel_bit = self.create("sel_bit%s" % i,Wire(UInt(1)))
            sel_bit += BitOrList(*id_hit_list)

            self.vld_list[i] += And(sel_bit, self.in0_vld)

            self.head_list[i] += self.in0_head
            self.tail_list[i] += self.in0_tail
            self.pld_list[i] += self.in0_pld
            self.id_list[i] += self.in0_id

            self.rdy_masked_list.append(And(sel_bit, self.rdy_list[i]))

        self.in0_rdy += OrList(*self.rdy_masked_list)

        #for dst in self.node.dst_list:
        #    print(dst.global_id_list)
