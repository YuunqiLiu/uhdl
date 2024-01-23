from .design.DDec import DDec
# from .design.DArb import DArb
from .design.DArb2ch import DArb2ch
from .design.DDec2ch import DDec2ch
from .design.DMst2ch import DMst2ch
from .design.DSlv2ch import DSlv2ch

#########################################################
#
#########################################################
class Node(object):

    color = 'gray'
    dst_num_limit = 128
    dep_num_limit = 128

    def __init__(self,name,nodeid,design=DDec):
        self._name                      = name
        self.nodeid                     = nodeid
        self.reachable_tgt_id_list      = []
        self.reachable_src_id_list      = []
        self.layer                      = 0
        self.dst_list                   = []
        self.dep_list                   = []
        self._port_tgt_id_mapping_dict  = {}
        self._port_src_id_mapping_dict  = {}
        self.network                    = None
        self._design                    = design


    def get_vinst(self):
        return self.vinst

    def create_vinst(self, forward=True):
        design_class = self._design
        self.vinst = design_class(self, self._father.default_interface_forward, self._father.default_interface_backward)
        return self.vinst
    
    def generate_verilog(self):
        self.vinst.generate_verilog(iteration=True)

    # @property
    # def src_id_width(self):
    #     return self.network.src_id_width

    # @property
    # def tgt_id_width(self):
    #     return self.network.tgt_id_width

    # @property
    # def txn_id_width(self):
    #     return self.network.txn_id_width

    # @property
    # def user_width(self):
    #     return self.network.user_width

    # @property
    # def addr_width(self):
    #     return self.network.addr_width


    def add_dst(self, dst):
        if len(self.dst_list) > self.dst_num_limit:
            raise Exception()
        self.dst_list.append(dst)

    def add_dep(self, dep):
        if len(self.dep_list) > self.dep_num_limit:
            raise Exception()
        self.dep_list.append(dep)



    def get_dep_route_id(self, dep):
        return self.dep_list.index(dep)
    
    def get_dst_route_id(self, dst):
        return self.dst_list.index(dst)

    #def get_tgt_index(self, dst):
    #    return self.tgt_list.index(dst)

    @property
    def name(self) -> str:
        return self._name

    def __str__(self) -> str:
        return self._name


    def report(self):
        print('Node %s(%s):' % (self, type(self)))
        print('    reacheable tgt_id_list : %s' % self.reachable_tgt_id_list)
        print('    reacheable src_id_list : %s' % self.reachable_src_id_list)

    @property
    def fwd_id_list(self):
        _fwd_id_list = []
        for dst in self.dst_list:
            _fwd_id_list += dst.fwd_id_list
        return _fwd_id_list

    @property 
    def bwd_id_list(self):
        _bwd_id_list = []
        for dep in self.dep_list:
            _bwd_id_list += dep.bwd_id_list
        return  _bwd_id_list

    @property
    def fwd_id_route_id_map_dict(self):
        _dict = {}
        for index, dst in enumerate(self.dst_list):
            for fwd_id in dst.fwd_id_list:
                _dict[fwd_id] = index
        return _dict

    @property
    def bwd_id_route_id_map_dict(self):
        _dict = {}
        for index, dep in enumerate(self.dep_list):
            for bwd_id in dep.bwd_id_list:
                _dict[bwd_id] = index
        return _dict
    
    def get_tgt_id_route_id_dict(self, forward=True):
        if forward is True: return self.fwd_id_route_id_map_dict
        else:               return self.bwd_id_route_id_map_dict

    def get_tgt_list(self, forward=True):
        if forward is True: return self.dst_list
        else:               return self.dep_list


    def get_src_list(self, forward=True):
        if forward is True: return self.dep_list
        else:               return self.dst_list



###################################################################
# Slave
###################################################################

class Slave(Node):

    @property
    def bwd_id_list(self):
        return [self.nodeid]

    def __init__(self,name,nodeid,design=DSlv2ch):
        super().__init__(name,nodeid,design=design)



###################################################################
# Master
###################################################################

class Master(Node):

    @property
    def fwd_id_list(self):
        return [self.nodeid]
    
    def __init__(self,name,nodeid,design=DMst2ch):
        super().__init__(name,nodeid,design=design)


class Switch(Node):
    pass

class Arbiter(Switch):

    def __init__(self,name,nodeid,design=DArb2ch):
        super().__init__(name,nodeid,design=design)

class Decoder(Switch):

    def __init__(self,name,nodeid,design=DDec2ch):
        super().__init__(name,nodeid,design=design)




    # def _generate_route_id(self):
    #     self.network.logger.info('[%s] start RTEID mapping generation.' % self.name)
    #     self.network.logger.info('[%s] TGTID mapping:' % self.name)
    #     for i, tgt in enumerate(self.tgt_list):
    #         self.network.logger.info('forward port %s connect to %s, which has reachable tgt id list %s' % (i, tgt.name, tgt.reachable_tgt_id_list))
    #         self._port_tgt_id_mapping_dict[tgt] = tgt.reachable_tgt_id_list
    #     self.network.logger.info('[%s] tgt id mapping dict: %s' %(self.name ,self._port_tgt_id_mapping_dict))

    #     self.network.logger.info('[%s] src id mapping:' % self.name)
    #     for i, src in enumerate(self.src_list):
    #         self.network.logger.info('backward port %s connect to %s, which has reachable src id list %s' % (i, src.name, src.reachable_src_id_list))
    #         self._port_src_id_mapping_dict[src] = src.reachable_src_id_list
    #     self.network.logger.info('[%s] src id mapping dict: %s' %(self.name ,self._port_src_id_mapping_dict))
