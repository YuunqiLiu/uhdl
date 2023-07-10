from copy import deepcopy

IGNORE_ERROR = False


CFG_PRI_LOW        = 0
CFG_PRI_MID        = 1000
CFG_PRI_HIGH       = 2000
CFG_PRI_ULTRA_HIGH = 3000

def rich_ext_setattr(self,key,value):
    if key != 'priority': raise Exception()
    self.__dict__[key] = value

def rich_ext_set_all_priority(self,priority):
    self.__dict__['priority'] = priority

class uhdl_cfg_rich_bool(int):

    __setattr__ = rich_ext_setattr

    set_all_priority = rich_ext_set_all_priority

    def __bool__(self):
        return True if self != 0 else False

    def __str__(self):
        return 'True' if self != 0 else 'False'


class uhdl_cfg_descriptor(object):

    def __init__(self,value,priority=CFG_PRI_LOW):
        self.__value    = value
        self.__priority = priority

    def __get__(self,obj,type=None):
        return self.__value

    def __set__(self,obj,val):
        self.__value = val

    @property
    def value(self):
        return self.__value

    @property
    def priority(self):
        return self.__priority
    @priority.setter
    def priority(self,value):
        self.__priority = value


class UHDLConfig(object):

    def __init__(self,priority = CFG_PRI_LOW):
        super().__init__()
        if not isinstance(priority,int) :raise Exception()
        self.__dict__['priority'] = priority

    def __setattr__(self,key,value):
        if isinstance(value,UHDLConfig):
            object.__setattr__(self,key,value)
        elif isinstance(value,bool):
            pass
            object.__setattr__(self,key,uhdl_cfg_rich_bool(value))
        else:
            new_type  = type('uhdl_cfg_rich_%s' % value.__class__.__name__, (type(value),),
                {'priority'         :self.__dict__['priority']  ,\
                 '__setattr__'      :rich_ext_setattr           ,
                 'set_all_priority' :rich_ext_set_all_priority  })
            object.__setattr__(self,key,new_type(value))

    def set_all_priority(self,priority=CFG_PRI_LOW):
        self.__dict__['priority'] = priority
        for k,v in {k:v for k,v in self.__dict__.items() if k != 'priority'}.items():
            #if isinstance(v,UHDLConfig):
            #    v.set_all_priority(priority=priority)
            #else:
            #    v.priority = priority
            v.set_all_priority(priority=priority)

    def update_by(self,other):
        if other.priority > self.__dict__['priority']:
            if type(self) != type(other): raise Exception()
            for k,v in {k:v for k,v in other.__dict__.items() if k != 'priority'}.items():
                if hasattr(self,k):
                    if isinstance(v,UHDLConfig):
                        other.__dict__[k].update_by(v)
                    elif other.__dict__[k].priority > self.__dict__[k].priority:
                        old_priority = self.__dict__[k].priority
                        self.__dict__[k] = deepcopy(other.__dict__[k])
                        self.__dict__[k].priority = old_priority
                else:
                    self.__dict__[k] = v
                    self.__dict__[k].priority = self.__dict__['priority']
