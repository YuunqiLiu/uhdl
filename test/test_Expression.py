import os,sys
import unittest

# pylint: disable =unused-wildcard-import
from ..core import *
# pylint: enable  =unused-wildcard-import

from ..core             import  ErrAttrMismatch         ,\
                                ErrExpInTypeWrong       ,\
                                ErrListExpNeedMultiOp   ,\
                                ErrCutExpSliceInvalid   ,\
                                ErrAttrTypeWrong        ,\
                                ErrBitsValOverflow      ,\
                                ErrBitsInvalidStr

from ..core             import InternalTool as IT


class TestValue(unittest.TestCase):

    def WaitException(self,exp_type,op,*param):
        try                  : op(*param)
        except exp_type  as e: print(e)
        except Exception as e: raise Exception('Expect a %s.But get \n\t%s:%s' % (IT.GetClsNameFromCls(exp_type),IT.GetClsNameFromObj(e),e))
        else                 : raise Exception('Expect a %s.But not get any Exception.' % IT.GetClsNameFromCls(exp_type) )

    def ErrExpInTypeWrongTest(self,op,*param):
        self.WaitException(ErrExpInTypeWrong,op,*param)

    def ErrAttrMismatchTest(self,op,*param):
        self.WaitException(ErrAttrMismatch,op,*param)

    def ErrListExpNeedMultiOpTest(self,op,*param):
        self.WaitException(ErrListExpNeedMultiOp,op,*param)

    def ErrCutExpSliceInvalidTest(self,op,hbound,lbound):
        self.WaitException(ErrCutExpSliceInvalid,Cut,op,hbound,lbound)

    def ErrAttrTypeWrongTest(self,op,*param):
        self.WaitException(ErrAttrTypeWrong,op,*param)

    def ErrBitsOverflowTest(self,op,*param):
        self.WaitException(ErrBitsValOverflow,op,*param)

    def ErrBitsInvalidStrTest(self,op,*param):
        self.WaitException(ErrBitsInvalidStr,op,*param)

class TestVariable(TestValue):
    

    def SingleVarTest(self,op):
        self.ErrAttrTypeWrongTest(op,1)
        op(UInt(1))



    def BitsTest(self,op):
        op(1,1)
        op("1'b1")
        self.ErrBitsOverflowTest(op,1,2)
        self.ErrBitsOverflowTest(op,"1'b10")
        self.ErrBitsInvalidStrTest(op,'asdf')

    def test_Reg(self):
        raise Exception()

    def test_Wire(self):
        raise Exception()

    def test_UInt(self):
        self.BitsTest(UInt)

    def test_SInt(self):
        self.BitsTest(SInt)

    def test_Parameter(self):
        raise Exception()

    def test_Input(self):
        self.SingleVarTest(Input)

    def test_Output(self):
        self.SingleVarTest(Output)

    def test_Inout(self):
        self.SingleVarTest(Inout)


class TestExpression(TestValue):



    def ListExpressionTest(self,op):
        op(UInt(1,0),UInt(1,0))
        op(UInt(1,0),UInt(1,0),UInt(1,0))
        self.ErrExpInTypeWrongTest(op,1,1)
        
    def MultiListExpressionTest(self,op):
        pass
        #self.ErrListExpNeedMultiOpTest(op,UInt(1))

    def MultiSameListExpressionTest(self,op):
        #self.MultiListExpressionTest(op)
        self.ErrAttrMismatchTest(op,UInt(1),UInt(2))
        self.ErrAttrMismatchTest(op,UInt(1),SInt(1))

    def OneOpExpressionTest(self,op):
        op(UInt(1,0))
        self.ErrExpInTypeWrongTest(op,1)

    def OneOpU1ExpressionTest(self,op):
        self.OneOpExpressionTest(op)
        self.assertEqual(op(UInt(1)).attribute,UInt(1))
        self.assertEqual(op(UInt(2)).attribute,UInt(1))

    def OneOpBitExpressionTest(self,op):
        self.OneOpExpressionTest(op)
        self.assertEqual(op(UInt(1)).attribute,UInt(1))
        self.assertEqual(op(UInt(2)).attribute,UInt(2))

    def TwoOpExpressionTest(self,op):
        op(UInt(1,0),UInt(1,0))
        print(op)
        self.ErrExpInTypeWrongTest(op,1,1)

    def TwoSameOpExpressionTest(self,op):
        self.TwoOpExpressionTest(op)
        self.ErrAttrMismatchTest(op,UInt(2,0),UInt(1,0))
        self.ErrAttrMismatchTest(op,UInt(2,0),SInt(2,0))

    def TwoSameOpU1ExpressionTest(self,op):
        self.TwoSameOpExpressionTest(op)
        self.assertEqual(op(UInt(1,0),UInt(1,0)).attribute,UInt(1))
        self.assertEqual(op(UInt(2,0),UInt(2,0)).attribute,UInt(1))

    def TwoSameOpBitExpressionTest(self,op):
        self.TwoSameOpExpressionTest(op)
        self.assertEqual(op(UInt(1,0),UInt(1,0)).attribute,UInt(1))
        self.assertEqual(op(UInt(2,0),UInt(2,0)).attribute,UInt(2))

    #def test_Or(self):
    #    self.TwoSameOpU1ExpressionTest(Or)

    #def test_And(self):
    #    self.TwoSameOpU1ExpressionTest(And)

    def test_Greater(self):
        self.TwoSameOpU1ExpressionTest(Greater)

    def test_Less(self):
        self.TwoSameOpU1ExpressionTest(Less)

    def test_GreaterEqual(self):
        self.TwoSameOpU1ExpressionTest(GreaterEqual)

    def test_LessEqual(self):
        self.TwoSameOpU1ExpressionTest(LessEqual)

    def test_NotEqual(self):
        self.TwoSameOpU1ExpressionTest(NotEqual)

    def test_Equal(self):
        self.TwoSameOpU1ExpressionTest(Equal)

    def test_BitXnor(self):
        self.TwoSameOpBitExpressionTest(BitXnor)

    def test_BitXor(self):
        self.TwoSameOpBitExpressionTest(BitXor)

    def test_BitAnd(self):
        self.TwoSameOpBitExpressionTest(BitAnd)

    def test_BitOr(self):
        self.TwoSameOpBitExpressionTest(BitOr)

    def test_SelfXnor(self):
        self.OneOpU1ExpressionTest(SelfXnor)

    def test_SelfXor(self):
        self.OneOpU1ExpressionTest(SelfXor)

    def test_SelfAnd(self):
        self.OneOpU1ExpressionTest(SelfAnd)

    def test_SelfOr(self):
        self.OneOpU1ExpressionTest(SelfOr)

    def test_Not(self):
        self.OneOpU1ExpressionTest(Not)

    def test_Inverse(self):
        self.OneOpBitExpressionTest(Inverse)

    def test_BitXnorList(self):
        self.MultiSameListExpressionTest(BitXnorList)

    def test_BitXorList(self):
        self.MultiSameListExpressionTest(BitXorList)

    def test_BitOrList(self):
        self.MultiSameListExpressionTest(BitOrList)

    def test_BitAndList(self):
        self.MultiSameListExpressionTest(BitAndList)

    def test_OrList(self):
        self.MultiListExpressionTest(OrList)

    def test_AndList(self):
        self.MultiListExpressionTest(AndList)

    def test_Combine(self):
        self.ListExpressionTest(Combine)

    def test_Cut(self):
        self.ErrCutExpSliceInvalidTest(Wire(UInt(32)),1.3,2.3)
        self.ErrCutExpSliceInvalidTest(Wire(UInt(32)),1,2.3)
        self.ErrCutExpSliceInvalidTest(Wire(UInt(32)),-1,-1)
        self.ErrCutExpSliceInvalidTest(Wire(UInt(32)),0,-1)
        self.ErrCutExpSliceInvalidTest(Wire(UInt(32)),1,2)
        self.ErrCutExpSliceInvalidTest(Wire(UInt(32)),32,32)