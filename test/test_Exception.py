
# pylint: disable =unused-wildcard-import
from ..core import *
# pylint: enable  =unused-wildcard-import

from ..core             import  ErrAttrMismatch         ,\
                                ErrExpInTypeWrong       ,\
                                ErrListExpNeedMultiOp   ,\
                                ErrCutExpSliceInvalid   ,\
                                ErrAttrTypeWrong        ,\
                                ErrBitsValOverflow      ,\
                                ErrBitsInvalidStr       ,\
                                ErrVarNotBelongComponent,\
                                ErrAssignTypeWrong 

from ..core             import InternalTool as IT

def _wait_exception(self,exp_type,op,*param):
    try                  : op(*param)
    except exp_type  as e: print(e)
    except Exception as e: raise Exception('Expect a %s.But get \n\t%s:%s' % (IT.GetClsNameFromCls(exp_type),IT.GetClsNameFromObj(e),e))
    else                 : raise Exception('Expect a %s.But not get any Exception.' % IT.GetClsNameFromCls(exp_type) )



def test_ErrVarNotBelongComponent():
    # check if var belongs to a component, exception will not be raised.
    c = Component()
    c.var = Wire(UInt(1))
    print(c.var.father)
    c.var += UInt(1,0)

    # check if var not belongs to a component, exception will be raised.
    exception_type = ErrVarNotBelongComponent
    try:
        var = Wire(UInt(1))
        var += Or(UInt(1,0),UInt(1,0))
    except exception_type   as e: pass
    except Exception        as e: raise Exception('Expect a %s.But get \n\t%s:%s' % (IT.GetClsNameFromCls(exception_type),IT.GetClsNameFromObj(e),e))
    else                        : raise Exception('Expect a %s.But not get any Exception.' % IT.GetClsNameFromCls(exception_type))

def test_ErrAssignTypeWrong():
    exception_type = ErrAssignTypeWrong
    try:
        c = Component()
        c.var = Wire(UInt(1))
        c.var += 1               # an error, Wire(UInt(1)) shoud be assigned by Wire(UInt(1))
    except exception_type       as e: pass
    except Exception            as e: raise Exception('Expect a %s.But get \n\t%s:%s' % (IT.GetClsNameFromCls(exception_type),IT.GetClsNameFromObj(e),e))
    else                            : raise Exception('Expect a %s.But not get any Exception.' % IT.GetClsNameFromCls(exception_type))


def test_ErrAttrMismatch():
    exception_type = ErrAttrMismatch


    Config.IGNORE_ERROR = True

    class C(Component):

        def __init__(self):
            super().__init__()
            self.var = Wire(UInt(1))
            self.var += Add(UInt(2,0),UInt(2,0))

    c = C()
    #c = Component()
    #c.var = Wire(UInt(1))
    #c.var += UInt(2)


    Config.IGNORE_ERROR = False
    try:
        c = Component()
        c.var = Wire(UInt(1))
        c.var += UInt(2)
    except ErrAttrMismatch      as e: pass
    except Exception            as e: raise Exception('Expect a %s.But get \n\t%s:%s' % (IT.GetClsNameFromCls(exception_type),IT.GetClsNameFromObj(e),e))
    else                            : raise Exception('Expect a %s.But not get any Exception.' % IT.GetClsNameFromCls(exception_type))
