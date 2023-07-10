
#########################################################
#
#########################################################
class Node(object):

    color = 'gray'
    dst_num_limit = 128
    src_num_limit = 128
    src_width = 32
    dst_width = 32

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
        self.id = self.slave_id
        Slave.slave_id += 1

    def __str__(self) -> str:
        return 'S%s' % self.id

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
        self.id = self.master_id
        Master.master_id += 1

    def __str__(self) -> str:
        return 'M%s' % self.id

#########################################################
#
#########################################################
class Switch(Node):

    color = 'green'
    switch_id = 0

    def __init__(self) -> None:
        super().__init__()
        self.id = self.switch_id
        Switch.switch_id += 1


    def __str__(self) -> str:
        return 'D%s' % self.id

#########################################################
#
#########################################################
class Arbiter(Switch):

    color = 'green'
    arbiter_id = 0
    dst_num_limit = 1
    src_num_limit = 128


    def __init__(self) -> None:
        super().__init__()
        self.id = self.arbiter_id
        Arbiter.arbiter_id += 1

    def __str__(self) -> str:
        return 'A%s' % self.id


#########################################################
#
#########################################################
class Decoder(Switch):
    
    color = 'green'
    decoder_id = 0
    src_num_limit = 1
    dst_num_limit = 128

    def __init__(self) -> None:
        super().__init__()
        self.id = self.decoder_id
        Decoder.decoder_id += 1

    def __str__(self) -> str:
        return 'D%s' % self.id




