# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import

from .CmnArb import CmnAgeMtx

class DArb(Component):

    def __init__(self, node, pld_width, id_type='mst'):
        super().__init__()
        self.node = node

        if id_type == 'mst':    used_list = self.node.dst_list
        else:                   used_list = self.node.src_list

        num = len(used_list)


        #pld_width        = node.network.pld_width
        master_id_width  = node.master_id_width
        slave_id_width   = node.slave_id_width

        # Create Input
        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))

        self.vld_list    = [self.create('in%s_vld'      % i, Input(UInt(1)))               for i in range(num)]
        self.rdy_list    = [self.create('in%s_rdy'      % i, Output(UInt(1)))              for i in range(num)]
        self.head_list   = [self.create('in%s_head'     % i, Input(UInt(1)))               for i in range(num)]
        self.tail_list   = [self.create('in%s_tail'     % i, Input(UInt(1)))               for i in range(num)]
        self.pld_list    = [self.create('in%s_pld'      % i, Input(UInt(pld_width)))       for i in range(num)]
        self.mst_id_list = [self.create('in%s_mst_id'   % i, Input(UInt(master_id_width))) for i in range(num)]
        self.slv_id_list = [self.create('in%s_slv_id'   % i, Input(UInt(slave_id_width)))  for i in range(num)]

        # Create Output
        self.out0_vld    = Output(UInt(1))
        self.out0_rdy    = Input(UInt(1))
        self.out0_head   = Output(UInt(1))
        self.out0_tail   = Output(UInt(1))
        self.out0_pld    = Output(UInt(pld_width))
        self.out0_mst_id = Output(UInt(master_id_width))
        self.out0_slv_id = Output(UInt(slave_id_width))

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

            if len(age_bit_masked_list) > 1:    bit_sel += OrList(*age_bit_masked_list)
            else:                               bit_sel += age_bit_masked_list[0]
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
        vld_masked_list     = []
        pld_masked_list     = []
        mst_id_masked_list  = []
        slv_id_masked_list  = []
        head_masked_list    = []
        tail_masked_list    = []
        for i in range(num):
            vld_masked_list.append(And(self.vld_list[i], self.bit_sel_locked_list[i]))
            head_masked_list.append(And(self.head_list[i], self.bit_sel_locked_list[i]))
            tail_masked_list.append(And(self.tail_list[i], self.bit_sel_locked_list[i]))
            pld_masked_list.append(BitAnd(self.pld_list[i], Fanout(self.bit_sel_locked_list[i], pld_width)))
            mst_id_masked_list.append(BitAnd(self.mst_id_list[i], Fanout(self.bit_sel_locked_list[i], master_id_width)))
            slv_id_masked_list.append(BitAnd(self.slv_id_list[i], Fanout(self.bit_sel_locked_list[i], slave_id_width)))

            self.rdy_list[i] += And(self.bit_sel_locked_list[i], self.out0_rdy)


        if num>1:
            self.out0_vld    += BitOrList(*vld_masked_list)
            self.out0_head   += BitOrList(*head_masked_list)
            self.out0_tail   += BitOrList(*tail_masked_list)
            self.out0_pld    += BitOrList(*pld_masked_list)
            self.out0_mst_id += BitOrList(*mst_id_masked_list)
            self.out0_slv_id += BitOrList(*slv_id_masked_list)
        else:
            self.out0_vld    += vld_masked_list[0]
            self.out0_head   += head_masked_list[0]
            self.out0_tail   += tail_masked_list[0]
            self.out0_pld    += pld_masked_list[0]
            self.out0_mst_id += mst_id_masked_list[0]
            self.out0_slv_id += slv_id_masked_list[0]

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
