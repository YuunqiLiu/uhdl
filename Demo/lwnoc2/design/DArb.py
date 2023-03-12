# pylint: disable =unused-wildcard-import
from ....core import *
# pylint: enable  =unused-wildcard-import

from .CmnArb import CmnAgeMtx
from .Bundle import LwnocBundle


class DArb(Component):

    def __init__(self, node, pld_type=LwnocBundle, forward=True):
        super().__init__()
        self.topo_node  = node
        channel_num     = len(node.get_src_list(forward))

        # IO Define
        self.clk        = Input(UInt(1))
        self.rst_n      = Input(UInt(1))
        self.out0       = pld_type()
        self.in_list    = [self.set('in%s' % i, self.out0.reverse()) for i in range(channel_num)]

        # Arbiter
        self.msg_update_en = Wire(UInt(channel_num))

        self.msg_udpate_en_bit_list = []
        for i in range(channel_num):
            in_i = self.in_list[i] 
            bit_i = self.set('msg_update_en_bit_%s' % i, Wire(UInt(1)))
            Assign(bit_i, AndList(in_i.vld, in_i.rdy, in_i.head))
            self.msg_udpate_en_bit_list.append(bit_i)
        Assign(self.msg_update_en, Combine(*self.msg_udpate_en_bit_list))
        
        # RTL is hard to read 
        # self.msg_update_en += Combine(*[self.set('mst_update_en_bit_%s' % AndList(var_in.vld, var_in.rdy, var_in.head) for var_in in self.in_list])



        self.arb_msg = CmnAgeMtx(channel_num)
        self.arb_msg.update_en  += self.msg_update_en
        self.arb_msg.clk        += self.clk
        self.arb_msg.rst_n      += self.rst_n

        # Arbiter lock
        self.arb_unlock     = Wire(UInt(1))
        self.arb_unlock     += AndList(self.out0.vld, self.out0.rdy, self.out0.tail)
# 
        self.arb_lock       = Wire(UInt(1))
        self.arb_lock       += AndList(self.out0.vld, self.out0.rdy, self.out0.head)

        self.arb_lock_reg   = Reg(UInt(1), self.clk, self.rst_n)
        self.arb_lock_reg   +=  when(self.arb_unlock).then(UInt(1, 0)).\
                                when(self.arb_lock).then(UInt(1, 1))





        self.bit_sel_list = []
        for i in range(channel_num):
            age_bit_masked_list = []
            for j in range(channel_num):
                age_bit_masked_list.append(And(self.arb_msg.get('age_bits_row_%s' % i)[j], self.get('in%s_vld' % j)))
            bit_sel = self.set('bit_sel_%s' % i, Wire(UInt(1)))

            if len(age_bit_masked_list) > 1:    bit_sel += OrList(*age_bit_masked_list)
            else:                               bit_sel += age_bit_masked_list[0]
            self.bit_sel_list.append(bit_sel)



        self.bit_sel_reg_list = []
        for i in range(channel_num):
            bit_set_reg = self.set('bit_set_reg_%s' % i, Reg(UInt(1), self.clk, self.rst_n))
            bit_set_reg += when(self.arb_lock).then(self.bit_sel_list[i])
            self.bit_sel_reg_list.append(bit_set_reg)

        self.bit_sel_locked_list = []
        for i in range(channel_num):
            bit_set_locked = self.set('bit_set_locked_%s' % i, Wire(UInt(1))) 
            bit_set_locked += when(self.arb_lock_reg).then(self.bit_sel_reg_list[i]).otherwise(self.bit_sel_list[i])
            self.bit_sel_locked_list.append(bit_set_locked)



        # data mux
        in_list_exclude_rdy = [var_in.as_list(exclude=['rdy']) for var_in in self.in_list]
        out_exclude_rdy = self.out0.as_list(exclude=['rdy'])
        for i, out_slice in enumerate(out_exclude_rdy):
            in_slice_list_masked = [BitMask(in_exclude_rdy[i], self.bit_sel_locked_list[in_idx]) for in_idx, in_exclude_rdy in enumerate(in_list_exclude_rdy)]
            out_slice += BitOrList(*in_slice_list_masked)

        for i, var_in in enumerate(self.in_list):
            var_in.rdy += And(self.bit_sel_locked_list[i], self.out0.rdy)
