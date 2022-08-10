# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import



class CmnAgeMtx(Component):



    def __init__(self, width):
        super().__init__()

        # Create Input
        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))
        self.update_en = Input(UInt(width))

        for i in range(width):
            self.set("age_bits_row_%s" % i, Output(UInt(width)))

        # Age Matrix
        for i in range(width):
            for j in range(width):
                if i < j:
                    age_bit = self.set('age_bit_%s_%s' % (i, j), Reg(UInt(1), self.clk, self.rst_n))
                    age_bit += self.update_en[j]
                elif i == j:
                    age_bit = self.set('age_bit_%s_%s' % (i, j), Wire(UInt(1)))
                    age_bit += UInt(1, 0)

        for i in range(width):
            for j in range(width):
                if i > j:
                    age_bit = self.set('age_bit_%s_%s' % (i, j), Wire(UInt(1)))
                    age_bit += Not(self.get('age_bit_%s_%s' % (j, i)))

        for i in range(width):
            age_bit_row_list = []
            for j in range(width):
                age_bit_row_list.append(self.get('age_bit_%s_%s' % (i, j)))
            age_bit_row = self.get("age_bits_row_%s" % i)
            age_bit_row += Combine(*age_bit_row_list)



        #self.age_bits

        #self.vld_list = []
        #self.rdy_list = []
        #for i in range(width):
        #    self.vld_list.append(self.create('in%s_vld' % i, Input(UInt(1))))
        #    self.rdy_list.append(self.create('in%s_rdy' % i, Output(UInt(1))))

        # Create Output
        #self.out0_vld = Output(UInt(1))
        #self.out0_rdy = Input(UInt(1))
        #self.out0_sel_bitmap = Output(UInt(width))


        # bitmap_list = []
        # for i in range(width):
            # age_bit_list = []
            # age_bit_masked_list = []
            # for j in range(width):
                # age_bit = self.get('age_bit_%s_%s' % (i, j))
                # age_bit_list.append(age_bit)
                # age_bit_masked_list.append(And(age_bit, self.vld_list[j]))
            # bitmap_i = self.set('out0_sel_bitmap_%s' % i, Wire(UInt(1)))
            # bitmap_i += OrList(*age_bit_masked_list)
            # bitmap_list.append(bitmap_i)

        # self.out0_sel_bitmap += Combine(*bitmap_list)