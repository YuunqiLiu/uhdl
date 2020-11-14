
ExternalRegion = True
InternalRegion = False

DirectionLeft   = 0
DirectionRight  = 1
DirectionAnalog = 2

class ConnectionProperty(object):

    def __init__(self):
        super().__init__()
        self.internal = UnitConnectionProperty()
        self.internal.region_type = InternalRegion
        self.external = UnitConnectionProperty()
        self.external.region_type = ExternalRegion

    def Assignable(self,other):
        return  self.internal.Assignable(other.internal) or \
                self.internal.Assignable(other.external) or \
                self.external.Assignable(other.internal) or \
                self.external.Assignable(other.external)

    def AssignPair(self,other):
        res = []
        if self.internal.Assignable(other.internal): res.append((self.internal,other.internal))
        if self.internal.Assignable(other.external): res.append((self.internal,other.external))
        if self.external.Assignable(other.internal): res.append((self.external,other.internal))
        if self.external.Assignable(other.external): res.append((self.external,other.external))
        return res

class UnitConnectionProperty(object):

    def __init__(self):
        super().__init__()
        self.region           = None
        self.region_type      = None
        self.as_left          = False
        self.as_right         = False
        self.as_bidirectional = False

    def Assignable(self,other):
        region_match    = self.region == other.region
        direction_match = \
            (self.as_left          and not other.as_right    ) or \
            (self.as_right         and not other.as_left     ) or \
            (self.as_bidirectional and other.as_bidirectional)
        return True if region_match and direction_match else False
