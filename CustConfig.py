from .Config import UHDLConfig,CFG_PRI_LOW

#class ComCfgStruct(UHDLConfig):



class ComponentConfig(UHDLConfig):

    def __init__(self, priority=CFG_PRI_LOW):
        super().__init__(priority=priority)
        self.STRUCT_CHECK = True