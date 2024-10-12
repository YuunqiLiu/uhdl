#import traceback
#from abc import abstractmethod
from .BasicFunction import join_name

from .  import Component

class Root(object):


    def __init__(self):
        super().__init__()
        #super(Root,self).__init__()
        self._name        = None
        self._father      = None
        self._father_type = None               #保留father type为空，子类不修改father_type就会出错

    def set_name(self,name:str):
        object.__setattr__(self,'_name',name)

    def set_father(self,father):
        object.__setattr__(self,'_father',father)
    
    def set_father_type(self,*T):
        ''' 这个方法设置了本对象应当指向的father对象的类型,默认的father对象的类型为None'''
        self._father_type = T

    @property
    def name(self) -> str:
        return self._name

    @property
    def father(self):
        return self._father
    
    @property
    def hier(self):
        return self.name

    def level_until_root(self):
        if not self._father is None:
            return self._father.level_until_root() + 1
        else:
            return 0


    def __setattr__(self, name, value):
        if isinstance(value, Root):
            value.set_name(name)
            value.set_father(self)
            value._setattr_hook(self)
        object.__setattr__(self, name, value)
            #print(name,'  ',value)
            #print(value.name)

    def _setattr_hook(self,*args):
        pass
        #raise NotImplementedError



    @property
    def full_hier(self):
        if self.hier is None:
            return "TOP"
        else:
            return "%s.%s" %(self.father.full_hier, self.hier) if self.father is not None else self.hier

    #=============================================================================================
    # father get
    #=============================================================================================
    def father_until_component(self):
        return self.father_until(Component.Component)


    def father_until(self, T):
        #return self if isinstance(self,T) or self.father is None else self.father.father_until(T)
        #print(self,'    ',self.father)
        
        if isinstance(self, T):
            return self
        elif self.father is None:
            return None
        else:
            return self.father.father_until(T)

        
        #if self.father is None:
        #    return None
        #else:
        #    return self if isinstance(self, T) else self.father.father_until(T)

        #if isinstance(self,T) or self.father is None:
        #    return self
        #elif self.father is None:
        #    return self
        #else:
        #    return self.father.father_until(T)

    def father_until_not(self, T):
        return self if not isinstance(self, T) else self.father.father_until_not(T)    

        # if not isinstance(self,T):
        #     return self
        # elif self.father is None:
        #     return self
        # else:
        #     return self.father.father_until_not(T)        

    #=============================================================================================
    # name get
    #=============================================================================================

    # def join_name(self,*args):
    #     args_without_none = [x for x in args if x is not None]
    #     return '_'.join(args_without_none)

    def full_name(self):
        return '' if self.father is None else join_name(self.father.full_name(), self.name)
        
        # if self.father is None:
        #     return ''
        # else:
        #     return join_name(self.father.full_name,self.name)


    def name_until(self,T,join_str='_'):
        if self.father is None or self is T or (isinstance(T,type) and isinstance(self,T)):
            return self.name
        else:
            return join_name(self.father.name_until(T,join_str),self.name,join_str=join_str)

        # if isinstance(T,type):
        #     if isinstance(self,T):
        #         return self.name
        #     elif self.father is None:
        #         return ''
        #     else:
        #         return join_name(self.father.name_until(T,join_str),self.name,join_str=join_str)
        # else:
        #     if self is T:
        #         return self.name
        #     elif self.father is None:
        #         return ''
        #     else:
        #         return join_name(self.father.name_until(T,join_str),self.name,join_str=join_str)

    def name_before(self,T,join_str='_'):
        if self.father is None or self.father is T or (isinstance(T,type) and isinstance(self.father,T)):
            return self.name
        else:
            return join_name(self.father.name_before(T,join_str),self.name,join_str=join_str)


        # if isinstance(T,type):
        #     if isinstance(self.father,T) or self.father is None:
        #         return self.name
        #     else:
        #         return join_name(self.father.name_before(T,join_str),self.name,join_str=join_str)
        # else:
        #     if self.father is T or self.father is None:
        #         return self.name
        #     else:
        #         return join_name(self.father.name_before(T,join_str),self.name,join_str=join_str)


        # if isinstance(T,type):
        #     if isinstance(self.father,T):
        #         return self.name
        #     elif self.father is None:
        #         return ''
        #     else:
        #         return join_name(self.father.name_before(T,join_str),self.name,join_str=join_str)
        # else:
        #     if self.father is T:
        #         return self.name
        #     elif self.father is None:
        #         return ''
        #     else:
        #         return join_name(self.father.name_before(T,join_str),self.name,join_str=join_str)


    def name_until_not(self,T,join_str='_'):
        if not isinstance(self,T) or self.father is None:
            return self.name
        else:
            return join_name(self.father.name_until_not(T,join_str),self.name,join_str=join_str)
        #elif self.father is None:
        #    return self.name

    def name_before_not(self,T,join_str='_'):
        if self.father is None or not isinstance(self.father,T):
            return self.name
        else:
            return join_name(self.father.name_before_not(T,join_str),self.name,join_str=join_str)
        #elif not isinstance(self.father,T):
        #    return self.name

    def ancestors_core(self):
        return [self] + self._father.ancestors_core() if self._father is not None else [self]


    def ancestors(self,until=None,before=None,has_self=False,error=True):
        full_ancestors = self.ancestors_core()

        if until  != None and before != None                        :    raise Exception()
        if until  != None and until  not in full_ancestors and error:    raise Exception()
        if before != None and before not in full_ancestors and error:    raise Exception()
        
        if   until  in full_ancestors:  result = full_ancestors[:full_ancestors.index(until)+1]
        elif before in full_ancestors:  result = full_ancestors[:full_ancestors.index(before)]
        else:                           result = full_ancestors

        if not has_self:    result.remove(self)
        return result

        #if until != None:
            #elif not error:
            #    result = full_ancestors
        #elif before != None:
            #elif not error:
            #    result = full_ancestors
            #elif until not in full_ancestors:
            #    raise Exception()
            #elif before not in full_ancestors:
            #    raise Exception()

    def __str__(self):
        #print(self.father)
        return "%s %s" % (self.full_name(), super().__str__())



    def get_circuit(self,name:str):
        return get_circuit(self,name)

    def set_circuit(self,name:str,value):
        return set_circuit(self,name,value)

    get = get_circuit
    set = set_circuit

    Get = get_circuit
    Set = set_circuit


def get_circuit(obj:Root,name:str) -> Root:
    return getattr(obj,name)

def set_circuit(obj:Root,name:str,value:Root) -> Root:
    setattr(obj,name,value)
    return value



    # @father.setter
    # def father(self,father):
    #     ''' 获取father的时候应当检查father的类型是否正确，对于Root而言
    #         father必须是Root类型'''
    #     if not isinstance(father,self._father_type):
    #         raise TypeError("The father set is a %s,expect a %s." %(type(father),self._father_type))
    #     self._father = father
    # @abstractmethod






        #print(self.father,self.name)
        #print(T)
        #print(isinstance(self,T))

        
    #def __get_name(self):
    #    pass

    #def __not_define(self):
    #    raise Exception

    #@property
    #def full_name(self):
    #    return self.name_join(self.get_father_full_name(),self.name)
#
#
#
    #def name_join(self,*args):
    #    return '_'.join(args)


