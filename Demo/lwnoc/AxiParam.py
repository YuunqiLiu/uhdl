



# class AxiParam(object):


    # def __init__(self):
        # self.addr_width = 32
        # self.data_width = 128
        # self.user_width = 32


    # @property
    # def strb_width(self):
        # return int(self.data_width/8)

    

    # @property
    # def w_req_pld_width(self):
        # return self.data_width + self.strb_width + self.id_width + self.user_width + self.addr_width


    # @property
    # def w_ack_pld_width(self):
    #     return self.slave_axi_id_width + 2 + self.ack_user_width


        # self.req_pld_width = self.data_width + int(self.data_width/8) + self.slave_axi_id_width + self.user_width + self.addr_width
        # self.r_req_pld_width = self.slave_axi_id_width + self.user_width + self.addr_width
        # self.ack_pld_width = self.slave_axi_id_width + 2 + self.ack_user_width
        # self.r_ack_pld_width = self.slave_axi_id_width + 2 + self.ack_user_width + self.data_width + 1
        