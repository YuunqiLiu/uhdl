
from .DMst import *
from .DSlv import *
from .DArb import *
from .DDec import *

#########################################################
#
#########################################################
class Node(object):

    color = 'gray'
    dst_num_limit = 128
    src_num_limit = 128
    src_width = 32
    dst_width = 32
    id_width = 8

    def __init__(self) -> None:
        self.global_id_list = []
        self.layer = 0
        self.dst_list = []
        self.src_list = []

    def add_dst(self, dst):
        if len(self.dst_list) > self.dst_num_limit:
            raise Exception()
        self.dst_list.append(dst)

    def add_src(self, src):
        if len(self.src_list) > self.src_num_limit:
            raise Exception()
        self.src_list.append(src)


    def get_src_index(self, src):
        return self.src_list.index(src)

    def get_dst_index(self, dst):
        return self.dst_list.index(dst)



#########################################################
#
#########################################################
class Slave(Node):

    color = 'blue'
    slave_id = 0
    dst_num_limit = 1
    src_num_limit = 0

    def __init__(self) -> None:
        super().__init__()
        self.inst_id = self.slave_id
        Slave.slave_id += 1
    

    @property
    def name(self) -> str:
        return 'S%s' % self.inst_id

    def __str__(self) -> str:
        return 'S%s' % self.inst_id

    def get_vinst(self):
        return self.vinst

    def create_vinst(self):
        self.vinst = DSlv(self)
        return self.vinst

#########################################################
#
#########################################################
class Master(Node):

    color = 'red'
    master_id = 0
    dst_num_limit = 0
    src_num_limit = 1

    def __init__(self) -> None:
        super().__init__()
        self.inst_id = self.master_id
        Master.master_id += 1

    @property
    def name(self) -> str:
        return 'M%s' % self.inst_id

    def __str__(self) -> str:
        return 'M%s' % self.inst_id

    def get_vinst(self):
        return self.vinst

    def create_vinst(self):
        self.vinst = DMst(self)
        return self.vinst


#########################################################
#
#########################################################
class Switch(Node):

    color = 'green'
    switch_id = 0

    def __init__(self) -> None:
        super().__init__()
        self.inst_id = self.switch_id
        Switch.switch_id += 1

    @property
    def name(self) -> str:
        return 'D%s' % self.inst_id

    def __str__(self) -> str:
        return 'D%s' % self.inst_id

    def get_vinst(self):
        raise NotImplementedError()

#########################################################
#
#########################################################
class Arbiter(Switch):

    color = 'green'
    arbiter_id = 0
    dst_num_limit = 1
    src_num_limit = 128
    pld_width = 32

    def __init__(self) -> None:
        super().__init__()
        self.inst_id = self.arbiter_id
        Arbiter.arbiter_id += 1

    @property
    def name(self) -> str:
        return 'A%s' % self.inst_id

    def __str__(self) -> str:
        return 'A%s' % self.inst_id

    def get_vinst(self):
        return self.vinst

    def create_vinst(self):
        self.vinst = DArb(self)
        return self.vinst


#########################################################
#
#########################################################
class Decoder(Switch):

    color = 'green'
    decoder_id = 0
    src_num_limit = 1
    dst_num_limit = 128
    pld_width = 32
    id_width = 8

    def __init__(self) -> None:
        super().__init__()
        self.inst_id = self.decoder_id
        Decoder.decoder_id += 1

    @property
    def name(self) -> str:
        return 'D%s' % self.inst_id

    def __str__(self) -> str:
        return 'D%s' % self.inst_id

    def get_vinst(self):
        return self.vinst

    def create_vinst(self):
        self.vinst = DDec(self)
        return self.vinst

