
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
        self.global_master_id_list = []
        self.global_slave_id_list = []
        self.layer = 0
        self.dst_list = []
        self.src_list = []
        self.network = None


    @property
    def master_id_width(self):
        return self.network.master_id_width

    @property
    def slave_id_width(self):
        return self.network.slave_id_width


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


    def report(self):
        print('Node %s(%s):' % (self, type(self)))
        print('    master_id_list : %s' % self.global_master_id_list)
        print('    slave_id_list  : %s' % self.global_slave_id_list)


#########################################################
#
#########################################################
class Slave(Node):

    color = 'blue'
    cls_slave_id_cnt = 0
    dst_num_limit = 1
    src_num_limit = 0

    def __init__(self) -> None:
        super().__init__()
        self.slave_id = Slave.cls_slave_id_cnt
        Slave.cls_slave_id_cnt += 1
        self.global_slave_id_list = [self.slave_id]

    # @property
    # def global_slave_id_list(self):
    #     return [self.slave_id]
    
    @property
    def inst_id(self):
        return self.slave_id

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


class SlaveAxi(Slave):

    def __init__(self) -> None:
        super().__init__()
        self.addr_width = 32
        self.data_width = 32
        self.address_range_list = []


    def create_vinst(self):
        self.vinst = DSlvAxi(self)
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



class MasterAxi(Master):

    def __init__(self) -> None:
        super().__init__()
        self.address_range_list = []

    def create_vinst(self):
        self.vinst = DMstAxi(self)
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

