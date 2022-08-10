# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import

from .CmnArb import CmnAgeMtx

class DArb(Component):

    def __init__(self, node):
        super().__init__()
        self.node = node

        num = len(node.src_list)
        pld_width = node.pld_width
        id_width = node.id_width

        # Create Input
        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))

        self.vld_list = []
        self.rdy_list = []
        self.head_list = []
        self.tail_list = []
        self.pld_list = []
        self.id_list = []

        for i in range(num):
            self.vld_list.append(self.create('in%s_vld' % i, Input(UInt(1))))
            self.rdy_list.append(self.create('in%s_rdy' % i, Output(UInt(1))))
            self.head_list.append(self.create('in%s_head' % i, Input(UInt(1))))
            self.tail_list.append(self.create('in%s_tail' % i, Input(UInt(1))))
            self.pld_list.append(self.create('in%s_pld' % i, Input(UInt(pld_width))))
            self.id_list.append(self.create('in%s_id' % i, Input(UInt(id_width))))

        # Create Output
        self.out0_vld = Output(UInt(1))
        self.out0_rdy = Input(UInt(1))
        self.out0_head = Output(UInt(1))
        self.out0_tail = Output(UInt(1))
        self.out0_pld = Output(UInt(pld_width))
        self.out0_id = Output(UInt(id_width))

        # Arbiter
        self.msg_update_en_list = []
        for i in range(num):
            self.msg_update_en_list.append(AndList(self.get('in%s_vld' % i), self.get('in%s_rdy' % i), self.get('in%s_head' % i)))
        self.msg_update_en = Wire(UInt(num))
        self.msg_update_en += Combine(*self.msg_update_en_list)

        self.arb_msg = CmnAgeMtx(num)
        self.arb_msg.update_en += self.msg_update_en

        self.bit_sel_list = []
        for i in range(num):
            age_bit_masked_list = []
            for j in range(num):
                age_bit_masked_list.append(And(self.arb_msg.get('age_bits_row_%s' % i)[j], self.get('in%s_vld' % j)))
            bit_sel = self.create('bit_sel_%s' % i, Wire(UInt(1)))
            bit_sel += OrList(*age_bit_masked_list)
            self.bit_sel_list.append(bit_sel)

        self.arb_unlock = Wire(UInt(1))
        self.arb_unlock += AndList(self.out0_vld, self.out0_rdy, self.out0_tail)
        self.arb_lock = Wire(UInt(1))
        self.arb_lock += AndList(self.out0_vld, self.out0_rdy, self.out0_head)


        self.arb_lock_reg = Reg(UInt(1), self.clk, self.rst_n)
        self.arb_lock_reg += when(self.arb_lock).then(UInt(1, 1)).when(self.arb_unlock).then(UInt(1, 0))

        self.bit_sel_reg_list = []
        for i in range(num):
            bit_set_reg = self.create('bit_set_reg_%s' % i, Reg(UInt(1), self.clk, self.rst_n))
            bit_set_reg += when(self.arb_lock).then(self.bit_sel_list[i])
            self.bit_sel_reg_list.append(bit_set_reg)

        self.bit_sel_locked_list = []
        for i in range(num):
            bit_set_locked = self.create('bit_set_locked_%s' % i, Wire(UInt(1))) 
            bit_set_locked += when(self.arb_lock_reg).then(self.bit_sel_reg_list[i]).otherwise(self.bit_sel_list[i])
            self.bit_sel_locked_list.append(bit_set_locked)

        # Output payload merge
        vld_masked_list = []
        pld_masked_list = []
        id_masked_list = []
        head_masked_list = []
        tail_masked_list = []
        for i in range(num):
            vld_masked_list.append(And(self.vld_list[i], self.bit_sel_locked_list[i]))
            head_masked_list.append(And(self.head_list[i], self.bit_sel_locked_list[i]))
            tail_masked_list.append(And(self.tail_list[i], self.bit_sel_locked_list[i]))
            pld_masked_list.append(BitAnd(self.pld_list[i], Fanout(self.bit_sel_locked_list[i], pld_width)))
            id_masked_list.append(BitAnd(self.id_list[i], Fanout(self.bit_sel_locked_list[i], id_width)))

            self.rdy_list[i] += And(self.bit_sel_locked_list[i], self.out0_rdy)

        self.out0_vld += BitOrList(*vld_masked_list)
        self.out0_head += BitOrList(*head_masked_list)
        self.out0_tail += BitOrList(*tail_masked_list)
        self.out0_pld += BitOrList(*pld_masked_list)
        self.out0_id += BitOrList(*id_masked_list)


        #print('233')
        #print(self.PARAM.UHDL_MODU_NAME_POST_FIX)


        ## Output valid merge
        #self.out0_vld += SelfOr(Combine(*self.vld_list))



        # self.bit_sel_list = []
        # for i in range(num):
#             self.bit_sel_list.append(self.create('bit_sel_%s'%i, Wire(UInt(1))))

        # for i in range(num):
#             if i == 0:
                # self.bit_sel_list[i] += self.vld_list[i]
#             else:
                # self.bit_sel_list[i] += And(self.vld_list[i], Not(self.bit_sel_list[i-1]))
