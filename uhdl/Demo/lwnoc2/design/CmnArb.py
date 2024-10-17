# pylint: disable =unused-wildcard-import
from ....core import *
# pylint: enable  =unused-wildcard-import



class CmnAgeMtx(Component):



    def __init__(self, width):
        super().__init__()

        # IO Define
        self.clk        = Input(UInt(1))
        self.rst_n      = Input(UInt(1))
        self.update_en  = Input(UInt(width))

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
            age_bit_row_list.reverse()
            age_bit_row += Combine(*age_bit_row_list)

