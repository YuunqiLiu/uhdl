# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import





class LwnocXbar(object):


    class Slave(object):

        def __init__(self, access_id_list=[]):
            self.access_id_list = access_id_list
            self.access_master_set = set()

        def add_master(self):
            pass


    class Master(object):

        def __init__(self, access_id_list=list()):
            self.access_id_list = access_id_list
            self.access_slave_set = set()

        def add_slave(self):
            pass

    def __init__(self):
        super().__init__()
        self.slave_list = []
        self.master_list = []
        self.global_id_to_mst_id_mapping_dict = dict()

    def add_slave(self, input_port):
        self.slave_list.append(input_port)

    def add_master(self, output_port):
        self.master_list.append(output_port)


    def compute_topology(self):

        # build master - id mapping relationship
        for master_id, master in enumerate(self.master_list):
            for global_id in master.access_id_list:
                if global_id in self.global_id_to_mst_id_mapping_dict.keys():
                    raise Exception()
                else:
                    self.global_id_to_mst_id_mapping_dict[global_id] = master_id

        # check slave port global id
        for slave in self.slave_list:
            for global_id in slave.access_id_list:
                if global_id not in self.global_id_to_mst_id_mapping_dict.keys():
                    raise Exception()

        # update connectivity for in/out port
        for slave_id, slave in enumerate(self.slave_list):
            for global_id in slave.access_id_list:
                master_id = self.global_id_to_mst_id_mapping_dict[global_id]
                slave.access_master_set.add(master_id)
                self.master_list[master_id].access_slave_set.add(slave_id)



        # build connectivicty message
        edge_id = 0
        for slave_id, slave in enumerate(self.slave_list):
            for salve_port_id, master_id in enumerate(slave.access_master_set):
                print(slave_id, ' ', salve_port_id, ' ', edge_id , ' ', master_id)
                edge_id += 1

                print(self.master_list[master_id].access_slave_set)

        #    print(in_port.access_master_set)

        #for out_port in self.master_list:
        #    print(out_port.access_slave_set)

        #print(self.id_mapping_dict)
