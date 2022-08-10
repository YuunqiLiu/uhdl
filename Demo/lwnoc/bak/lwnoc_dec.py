# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import


class LwnocDec(Component):

    def __init__(self, num, pld_width, id_width):
        super().__init__()

        # Parameter Check
        if not type(num) is int:
            raise Exception('Input parameter \"num\" should be integer but get %s' % type(num))

        self.num = num
        self.pld_width = pld_width
        self.id_width = id_width


        self.vld_list = []
        self.rdy_list = []
        self.id_list = []
        self.pld_list = []

        # Create Output
        for i in range(num):
            self.vld_list.append(self.create('out%s_vld' % i, Output(UInt(1))))
            self.rdy_list.append(self.create('out%s_rdy' % i, Input(UInt(1))))
            self.id_list.append(self.create('out%s_id' % i, Output(UInt(id_width))))
            self.pld_list.append(self.create('out%s_pld' % i, Output(UInt(pld_width))))

        # Create Input
        self.in_vld = Input(UInt(1))
        self.in_rdy = Output(UInt(1))
        self.in_id = Input(UInt(id_width))
        self.in_pld = Output(UInt(pld_width))


        # bin2onehot
        self.rdy_masked_list = []
        for i in range(num):
            sel_bit = self.create("sel_bit%s" % i,Wire(UInt(1)))
            sel_bit += Equal(self.in_id, UInt(id_width, i))

            self.vld_list[i] += And(sel_bit, self.in_vld)

            self.pld_list[i] += self.in_pld
            self.id_list[i] += self.in_id

            self.rdy_masked_list.append(And(sel_bit, self.rdy_list[i]))

        
        self.in_rdy += OrList(*self.rdy_masked_list)


        # Output valid merge
        #self.out_vld += SelfOr(Combine(*self.vld_list))

        # # Fix priority arbiter
        # self.bit_sel_list = []
        # for i in range(num):
        #     self.bit_sel_list.append(self.create('bit_sel_%s'%i, Wire(UInt(1))))

        # for i in range(num):
        #     if i == 0: 
        #         self.bit_sel_list[i] += self.vld_list[i]
        #     else:
        #         self.bit_sel_list[i] += And(self.vld_list[i], Not(self.bit_sel_list[i-1]))

        #     self.rdy_list[i] += And(self.bit_sel_list[i],self.out_rdy)

        # # Output payload merge
        # pld_masked_list = []
        # for i in range(num):
        #     pld_masked_list.append(BitAnd(self.pld_list[i], Fanout(self.bit_sel_list[i],self.pld_width)))


        # self.out_pld += BitOrList(*pld_masked_list)

