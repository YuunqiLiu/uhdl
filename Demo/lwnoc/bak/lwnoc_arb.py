# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import


class LwnocArb(Component):

    def __init__(self, num, pld_width):
        super().__init__()

        # Parameter Check
        if not type(num) is int:
            raise Exception('Input parameter \"num\" should be integer but get %s' % type(num))

        self.num = num
        self.pld_width = pld_width

        self.vld_list = []
        self.rdy_list = []
        self.pld_list = []

        # Create Input
        for i in range(num):
            self.vld_list.append(self.create('in%s_vld' % i, Input(UInt(1))))
            self.rdy_list.append(self.create('in%s_rdy' % i, Output(UInt(1))))
            self.pld_list.append(self.create('in%s_pld' % i, Input(UInt(pld_width))))

        # Create Output
        self.out_vld = Output(UInt(1))
        self.out_rdy = Input(UInt(1))
        self.out_pld = Output(UInt(pld_width))

        # Output valid merge
        self.out_vld += SelfOr(Combine(*self.vld_list))

        # Fix priority arbiter
        self.bit_sel_list = []
        for i in range(num):
            self.bit_sel_list.append(self.create('bit_sel_%s'%i, Wire(UInt(1))))

        for i in range(num):
            if i == 0: 
                self.bit_sel_list[i] += self.vld_list[i]
            else:
                self.bit_sel_list[i] += And(self.vld_list[i], Not(self.bit_sel_list[i-1]))

            self.rdy_list[i] += And(self.bit_sel_list[i],self.out_rdy)

        # Output payload merge
        pld_masked_list = []
        for i in range(num):
            pld_masked_list.append(BitAnd(self.pld_list[i], Fanout(self.bit_sel_list[i],self.pld_width)))


        self.out_pld += BitOrList(*pld_masked_list)

