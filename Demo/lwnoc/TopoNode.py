
from .DMst import *
from .DSlv import *
from .DArb import *
from .DDec import *
from .DDecDual import *
from .DArbDual import *
from .Credit import *

#########################################################
#
#########################################################
class Node(object):

    color = 'gray'
    dst_num_limit = 128
    src_num_limit = 128
    #src_width = 32
    #dst_width = 32
    #id_width = 8

    

    def __init__(self) -> None:
        self.reachable_tgt_id_list = []
        self.reachable_src_id_list = []
        self.layer = 0
        self.tgt_list = []
        self.src_list = []

        self._port_tgt_id_mapping_dict = {}
        self._port_src_id_mapping_dict = {}
        self.network = None
        self.data_width = 32

    @property
    def src_id_width(self):
        return self.network.src_id_width

    @property
    def tgt_id_width(self):
        return self.network.tgt_id_width

    @property
    def txn_id_width(self):
        return self.network.txn_id_width


    @property
    def w_req_pld_width(self):
        return self.data_width + int(self.data_width/8) + self.user_width + self.addr_width

    @property
    def r_req_pld_width(self):
        return self.user_width + self.addr_width

    @property
    def w_ack_pld_width(self):
        return 2

    @property
    def r_ack_pld_width(self):
        return 2 + self.data_width + 1



    # @property
    # def r_req_pld_width(self):
    #     return self.network.r_req_pld_width
# 
    # @property
    # def w_req_pld_width(self):
    #     return self.network.w_req_pld_width
# 
    # @property
    # def r_ack_pld_width(self):
    #     return self.network.r_ack_pld_width
# 
    # @property
    # def w_ack_pld_width(self):
    #     return self.network.w_ack_pld_width

    @property
    def user_width(self):
        return self.network.user_width

    @property
    def addr_width(self):
        return self.network.addr_width

    #@property
    #def data



    # @property
    # def master_id_width(self):
    #     return self.network.master_id_width

    # @property
    # def slave_id_width(self):
    #     return self.network.slave_id_width


    def add_dst(self, dst):
        if len(self.tgt_list) > self.dst_num_limit:
            raise Exception()
        self.tgt_list.append(dst)

    def add_src(self, src):
        if len(self.src_list) > self.src_num_limit:
            raise Exception()
        self.src_list.append(src)


    def get_src_index(self, src):
        return self.src_list.index(src)

    def get_dst_index(self, dst):
        return self.dst_list.index(dst)

    @property
    def name(self) -> str:
        raise NotImplementedError()


    def report(self):
        print('Node %s(%s):' % (self, type(self)))
        print('    reacheable tgt_id_list : %s' % self.reachable_tgt_id_list)
        print('    reacheable src_id_list : %s' % self.reachable_src_id_list)


    def _generate_local_port_id_mapping(self):
        self.network.logger.info('[%s] start local port id mapping generation.' % self.name)
        self.network.logger.info('[%s] tgt id mapping:' % self.name)
        for i, tgt in enumerate(self.tgt_list):
            self.network.logger.info('forward port %s connect to %s, which has reachable tgt id list %s' % (i, tgt.name, tgt.reachable_tgt_id_list))
            self._port_tgt_id_mapping_dict[tgt] = tgt.reachable_tgt_id_list
        self.network.logger.info('[%s] tgt id mapping dict: %s' %(self.name ,self._port_tgt_id_mapping_dict))

        self.network.logger.info('[%s] src id mapping:' % self.name)
        for i, src in enumerate(self.src_list):
            self.network.logger.info('backward port %s connect to %s, which has reachable src id list %s' % (i, src.name, src.reachable_src_id_list))
            self._port_src_id_mapping_dict[src] = src.reachable_src_id_list
        self.network.logger.info('[%s] src id mapping dict: %s' %(self.name ,self._port_src_id_mapping_dict))


#########################################################
#
#########################################################
class Slave(Node):

    color = 'blue'
    cls_src_id_cnt = 0
    dst_num_limit = 1
    src_num_limit = 0

    def __init__(self) -> None:
        super().__init__()
        Slave.cls_src_id_cnt += 1
        self.src_id = Slave.cls_src_id_cnt
        self.reachable_src_id_list = [self.src_id]
        #self.data_width = 128

    # @property
    # def global_slave_id_list(self):
    #     return [self.slave_id]
    
    @property
    def inst_id(self):
        return self.src_id

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

    def __init__(self, data_width= 32) -> None:
        super().__init__()
        #self.addr_width = 32
        #self.data_width = 32
        self.data_width = data_width
        self.address_range_list = []


    def create_vinst(self):
        self.vinst = DSlvAxi(self)
        return self.vinst



#########################################################
#
#########################################################
class Master(Node):

    color = 'red'
    cls_tgt_id_cnt = 0
    dst_num_limit = 0
    src_num_limit = 1

    def __init__(self) -> None:
        super().__init__()
        Master.cls_tgt_id_cnt += 1
        self.tgt_id = Master.cls_tgt_id_cnt

        self.reachable_tgt_id_list = [self.tgt_id]
        #self.data_width = 128



    @property
    def inst_id(self):
        return self.tgt_id



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
        self.data_width = 128


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
    #pld_width = 32

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
        self.vinst = DArb2(self,32)
        return self.vinst

class ArbiterDual(Arbiter):

    def create_vinst(self):
        self.vinst = DArbDual(self)
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
        print('init a decoder')

    @property
    def name(self) -> str:
        return 'D%s' % self.inst_id

    def __str__(self) -> str:
        return 'D%s' % self.inst_id

    def get_vinst(self):
        return self.vinst

    def create_vinst(self):
        self.vinst = DDec2(self, 32)
        return self.vinst


    def report(self):
        super().report()
        print('    dst_list: %s' % self.dst_list)

class DecoderDual(Decoder):

    def create_vinst(self):
        self.vinst = DDecDual(self)
        return self.vinst



#########################################################
#
#########################################################

class Adapter(Node):


    adapter_id = 0

    def __init__(self) -> None:
        super().__init__()
        self.inst_id = self.adapter_id
        Adapter.adapter_id += 1

        self.data_width = 128

    @property
    def name(self) -> str:
        return 'Adapt%s' % self.inst_id

    def __str__(self) -> str:
        return 'Adapt%s' % self.inst_id

    def get_vinst(self):
        return self.vinst

    # def create_vinst(self):
    #     self.vinst = DDec(self)
    #     return self.vinst

  #class Handshake2Credit(Adapter):

      #def create_vinst(self):
          #self.vinst = DHdsk2Cdt()(self)
          #return self.vinst