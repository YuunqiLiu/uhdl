
# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import


class BasicHdsk(Bundle):

    def __init__(self, src_id_width, tgt_id_width, txn_id_width, pld_width):
        super().__init__()
        self.src_id_width   = src_id_width
        self.tgt_id_width   = tgt_id_width
        self.txn_id_width   = txn_id_width
        self.pld_width      = pld_width
        self.vld            = Output(UInt(1))
        self.rdy            = Input(UInt(1))
        self.head           = Output(UInt(1))
        self.tail           = Output(UInt(1))
        self.pld            = Output(UInt(pld_width))
        self.src_id         = Output(UInt(src_id_width))
        self.tgt_id         = Output(UInt(tgt_id_width))
        self.txn_id         = Output(UInt(txn_id_width))

    def copy(self):
        return BasicHdsk(self.src_id_width, self.tgt_id_width, self.txn_id_width, self.pld_width)

    def copy_reverse(self):
        return BasicHdskReverse(self.src_id_width, self.tgt_id_width, self.txn_id_width, self.pld_width)




class BasicHdskReverse(Bundle):

    def __init__(self, src_id_width, tgt_id_width, txn_id_width, pld_width):
        super().__init__()
        self.src_id_width   = src_id_width
        self.tgt_id_width   = tgt_id_width
        self.txn_id_width   = txn_id_width
        self.pld_width      = pld_width
        self.vld            = Input(UInt(1))
        self.rdy            = Output(UInt(1))
        self.head           = Input(UInt(1))
        self.tail           = Input(UInt(1))
        self.pld            = Input(UInt(pld_width))
        self.src_id         = Input(UInt(src_id_width))
        self.tgt_id         = Input(UInt(tgt_id_width))
        self.txn_id         = Input(UInt(txn_id_width))

    def copy(self):
        return BasicHdskReverse(self.src_id_width, self.tgt_id_width, self.txn_id_width, self.pld_width)

    def copy_reverse(self):
        return BasicHdsk(self.src_id_width, self.tgt_id_width, self.txn_id_width, self.pld_width)