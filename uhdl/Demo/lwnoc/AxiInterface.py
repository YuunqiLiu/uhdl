# pylint: disable =unused-wildcard-import
from ...core import *
# pylint: enable  =unused-wildcard-import

class Axi(Bundle):

    def __init__(self, id_width, addr_width, data_width, user_width):
        super().__init__()
        self.id_width    = id_width
        self.addr_width  = addr_width
        self.data_width  = data_width
        self.user_width  = user_width

        strb_width = int(data_width/8)

        self.aw_vld  = Output(UInt(1))
        self.aw_rdy  = Input(UInt(1))
        self.aw_addr = Output(UInt(addr_width))
        self.aw_id   = Output(UInt(id_width))
        self.aw_user = Output(UInt(user_width))

        self.w_vld   = Output(UInt(1))
        self.w_rdy   = Input(UInt(1))
        self.w_last  = Output(UInt(1))
        self.w_data  = Output(UInt(data_width))
        self.w_strb  = Output(UInt(strb_width))
        #self.w_user  = Output(UInt(user_width))

        self.b_vld   = Input(UInt(1))
        self.b_rdy   = Output(UInt(1))
        self.b_id    = Input(UInt(id_width))
        self.b_resp  = Input(UInt(2))

        self.ar_vld  = Output(UInt(1))
        self.ar_rdy  = Input(UInt(1))
        self.ar_addr = Output(UInt(addr_width))
        self.ar_id   = Output(UInt(id_width))
        self.ar_user = Output(UInt(user_width))

        self.r_vld   = Input(UInt(1))
        self.r_rdy   = Output(UInt(1))
        self.r_id    = Input(UInt(id_width))
        self.r_data  = Input(UInt(data_width))
        self.r_resp  = Input(UInt(2))
        self.r_last  = Input(UInt(1))

    def copy(self):
        return Axi(self.id_width, self.addr_width, self.data_width, self.user_width)

    def copy_reverse(self):
        return AxiReverse(self.id_width, self.addr_width, self.data_width, self.user_width)

class AxiReverse(Bundle):

    def __init__(self, id_width, addr_width, data_width, user_width):
        super().__init__()
        self.id_width    = id_width
        self.addr_width  = addr_width
        self.data_width  = data_width
        self.user_width  = user_width

        strb_width = int(data_width/8)

        self.aw_vld  = Input(UInt(1))
        self.aw_rdy  = Output(UInt(1))
        self.aw_addr = Input(UInt(addr_width))
        self.aw_id   = Input(UInt(id_width))
        self.aw_user = Input(UInt(user_width))

        self.w_vld   = Input(UInt(1))
        self.w_rdy   = Output(UInt(1))
        self.w_last  = Input(UInt(1))
        self.w_data  = Input(UInt(data_width))
        self.w_strb  = Input(UInt(strb_width))
        #self.w_user  = Input(UInt(user_width))

        self.b_vld   = Output(UInt(1))
        self.b_rdy   = Input(UInt(1))
        self.b_id    = Output(UInt(id_width))
        self.b_resp  = Output(UInt(2))

        self.ar_vld  = Input(UInt(1))
        self.ar_rdy  = Output(UInt(1))
        self.ar_addr = Input(UInt(addr_width))
        self.ar_id   = Input(UInt(id_width))
        self.ar_user = Input(UInt(user_width))

        self.r_vld   = Output(UInt(1))
        self.r_rdy   = Input(UInt(1))
        self.r_id    = Output(UInt(id_width))
        self.r_data  = Output(UInt(data_width))
        self.r_resp  = Output(UInt(2))
        self.r_last  = Output(UInt(1))

    def copy(self):
        return AxiReverse(self.id_width, self.addr_width, self.data_width, self.user_width)

    def copy_reverse(self):
        return Axi(self.id_width, self.addr_width, self.data_width, self.user_width)



# class AxiAxCh(Bundle):

#     def __init__(self, id_width, addr_width, user_width):
#         super().__init__()
#         self.id_width = id_width
#         self.addr_width = addr_width
#         self.user_width = user_width

#         self.vld  = Output(UInt(1))
#         self.rdy  = Input(UInt(1))
#         self.addr = Output(UInt(addr_width))
#         self.id   = Output(UInt(id_width))
#         self.user = Output(UInt(user_width))

#     def copy(self):


# class AxiAxChReverse(Bundle):

#     def __init__(self, id_width, addr_width, user_width):
#         super().__init__()
#         self.id_width = id_width
#         self.addr_width = addr_width
#         self.user_width = user_width

#         self.vld  = Input(UInt(1))
#         self.rdy  = Output(UInt(1))
#         self.addr = Input(UInt(addr_width))
#         self.id   = Input(UInt(id_width))
#         self.user = Input(UInt(user_width))






# class AxiWCh(Bundle):
    
#     def __init__(self, data_width):
#         super().__init__()
#         self.data_width = data_width

#         self.vld   = Output(UInt(1))
#         self.rdy   = Input(UInt(1))
#         self.last  = Output(UInt(1))
#         self.strb  = Output(UInt(int(data_width/8)))
#         self.data  = Output(UInt(data_width))

# class AxiBCh(Bundle):

#     def __init__(self, id_width):
#         super().__init__()
#         self.id_width = id_width

#         self.vld  = Output(UInt(1))
#         self.rdy  = Input(UInt(1))
#         self.id   = Output(UInt(id_width))
#         self.resp = Output(UInt(2))


# class AxiRCh(Bundle):

#     def __init__(self, id_width, data_width):
#         super().__init__()
#         self.id_width = id_width
#         self.data_width = data_width

#         self.vld   = Output(UInt(1))
#         self.rdy   = Input(UInt(1))
#         self.id    = Output(UInt(id_width))
#         self.data  = Output(UInt(data_width))
#         self.resp  = Output(UInt(2))
#         self.last  = Output(UInt(1))
