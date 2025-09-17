import os,sys
import unittest

# pylint: disable =unused-wildcard-import
from uhdl import *
# pylint: enable  =unused-wildcard-import

from uhdl.core.Exception import  ErrAttrMismatch         ,\
                                ErrExpInTypeWrong       ,\
                                ErrListExpNeedMultiOp   ,\
                                ErrCutExpSliceInvalid   ,\
                                ErrAttrTypeWrong        ,\
                                ErrBitsValOverflow      ,\
                                ErrBitsInvalidStr       ,\
                                ErrLogicSigAttrWrong    ,\
                                ErrConstInWrong         ,\
                                ErrNeedBool             ,\
                                ErrWhenExpOperateWrong

from uhdl.core             import InternalTool as IT


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
        # wrong attribute type
        self.ErrAttrTypeWrongTest(lambda tpl: Reg(tpl, Wire(UInt(1))), 1)
        # wrong flag types
        self.WaitException(ErrNeedBool, lambda: Reg(UInt(8), Wire(UInt(1)), Wire(UInt(1)), async_rst="x"))
        self.WaitException(ErrNeedBool, lambda: Reg(UInt(8), Wire(UInt(1)), Wire(UInt(1)), rst_active_low=123))
        self.WaitException(ErrNeedBool, lambda: Reg(UInt(8), Wire(UInt(1)), Wire(UInt(1)), clk_active_neg="no"))

        # minimal component to exercise verilog strings and attributes
        class C(Component):
            def circuit(self):
                self.clk = Wire(UInt(1))
                self.rst = Wire(UInt(1))
                self.r   = Reg(UInt(8), self.clk, self.rst, async_rst=True, rst_active_low=True, clk_active_neg=False)
                # assign a value so verilog_assignment is produced
                self.r += UInt(8, 0xAB)

        c = C()
        self.assertEqual(c.r.attribute, UInt(8))
        va = "\n".join(c.r.verilog_assignment)
        self.assertIn("always @(posedge", va)
        self.assertIn("if(~", va)  # low-active reset

        # negedge clock case
        class C2(Component):
            def circuit(self):
                self.clk = Wire(UInt(1))
                self.r   = Reg(UInt(8), self.clk, None, async_rst=True, rst_active_low=True, clk_active_neg=True)
                self.r += UInt(8, 0)
        c2 = C2()
        va2 = "\n".join(c2.r.verilog_assignment)
        self.assertIn("negedge", va2)

    def test_Wire(self):
        # wrong attribute type
        self.ErrAttrTypeWrongTest(Wire, 1)
        # minimal component to check def keyword switching
        class C(Component):
            def circuit(self):
                self.w = Wire(UInt(8))
        c = C()
        self.assertEqual(c.w.attribute, UInt(8))
        self.assertEqual(c.w.verilog_def, ['wire [7:0] w'])

        # After assigning an AlwaysComb expression, wire def should become 'reg'
        class C2(Component):
            def circuit(self):
                self.w = Wire(UInt(8))
                expr = When(UInt(1,1)).then(UInt(8,0)).otherwise(UInt(8,1))
                self.w += expr
        c2 = C2()
        self.assertEqual(c2.w.verilog_def, ['reg [7:0] w'])

    def test_UInt(self):
        self.BitsTest(UInt)

    def test_SInt(self):
        self.BitsTest(SInt)

    def test_Parameter(self):
        # wrong attribute type
        self.ErrAttrTypeWrongTest(Parameter, 1)
        # in a component, parameter name and def formatting
        class C(Component):
            def circuit(self):
                self.P = Parameter(UInt(8, 5))
        c = C()
        # parameter definition string uses template rstring (binary by default)
        self.assertEqual(c.P.verilog_def, ["parameter P = 8'b101"])
        # parameter assignment (instantiation mapping) when unassigned
        self.assertEqual(c.P.verilog_assignment, [".P(8'b101)"])

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

    # ---------------- Additional coverage ----------------
    def test_Add_Sub_Mul(self):
        # same width and same attributes required by current impl
        self.assertEqual(Add(UInt(8, 10), UInt(8, 20)).attribute, UInt(9))
        self.assertEqual(Sub(UInt(8, 10), UInt(8, 20)).attribute, UInt(9))
        self.assertEqual(Mul(UInt(8, 3),  UInt(8, 4)).attribute,  UInt(16))
        # different width currently not allowed (TwoSameOp checks attribute equality)
        self.ErrAttrMismatchTest(Add, UInt(5, 1), UInt(7, 2))
        self.ErrAttrMismatchTest(Sub, UInt(5, 1), UInt(7, 2))
        self.ErrAttrMismatchTest(Mul, UInt(5, 1), UInt(7, 2))
        # type mismatch should raise
        self.ErrAttrMismatchTest(Add, UInt(4, 1), SInt(4, 1))
        self.ErrAttrMismatchTest(Sub, UInt(4, 1), SInt(4, 1))
        self.ErrAttrMismatchTest(Mul, UInt(4, 1), SInt(4, 1))

    def test_Shifts(self):
        # shift amounts must be Value, not raw int
        a = UInt(8, 0xF)
        sh1 = a << UInt(3, 1)
        sh2 = a >> UInt(3, 2)
        self.assertEqual(sh1.attribute, UInt(8))
        self.assertEqual(sh2.attribute, UInt(8))
        # wrong type (int) should raise type error via operator overload
        self.ErrExpInTypeWrongTest(lambda x, y: x << y, a, 1)
        self.ErrExpInTypeWrongTest(lambda x, y: x >> y, a, 1)

    def test_AndList_actual(self):
        # AndList returns UInt(1) regardless of operand widths/types (but all must be Value)
        self.assertEqual(AndList(UInt(1, 1), UInt(2, 1)).attribute, UInt(1))
        # non-Value input should raise
        self.ErrExpInTypeWrongTest(AndList, UInt(1, 1), 1)

    def test_OrList_actual(self):
        self.assertEqual(OrList(UInt(1, 0), UInt(4, 1)).attribute, UInt(1))
        self.ErrExpInTypeWrongTest(OrList, UInt(1, 1), "x")

    def test_Fanout(self):
        x = UInt(4, 0xA)
        f1 = Fanout(x, 1)
        f3 = Fanout(x, 3)
        self.assertEqual(f1.attribute, UInt(4))
        self.assertEqual(f3.attribute, UInt(12))

    def test_Case_basic(self):
        sel = UInt(2, 0)
        v0  = UInt(8, 0xAA)
        v1  = UInt(8, 0x55)
        dft = UInt(8, 0)
        expr = Case(sel, [(UInt(2, 0), v0), (UInt(2, 1), v1)], dft)
        self.assertEqual(expr.attribute, UInt(8))
        # key type mismatch
        self.ErrAttrMismatchTest(lambda s, kv, d: Case(s, kv, d), sel, [(UInt(3, 0), v0)], dft)
        # value type mismatch
        self.ErrAttrMismatchTest(lambda s, kv, d: Case(s, kv, d), sel, [(UInt(2, 0), UInt(7, 0))], dft)

    def test_Case_value_mismatch_without_default(self):
        # case values mismatch and default is None should raise
        sel = UInt(2, 0)
        self.ErrAttrMismatchTest(lambda: Case(sel, [(UInt(2,0), UInt(8,0)), (UInt(2,1), UInt(7,0))], None))

    def test_When_basic(self):
        cond1 = UInt(1, 1)
        cond2 = UInt(1, 0)
        a = UInt(8, 1)
        b = UInt(8, 2)
        d = UInt(8, 0)
        expr = When(cond1).then(a).when(cond2).then(b).otherwise(d)
        self.assertEqual(expr.attribute, UInt(8))
        # when input must be 1-bit
        self.WaitException(ErrLogicSigAttrWrong, lambda: When(UInt(2, 0)))
        # then/otherwise attribute mismatch
        self.ErrAttrMismatchTest(lambda: When(cond1).then(UInt(7, 1)).otherwise(UInt(8, 0)))

    def test_When_errors(self):
        # then without preceding when (use EmptyWhen to start)
        from uhdl.core.Operator import EmptyWhen
        self.WaitException(ErrWhenExpOperateWrong, lambda: EmptyWhen().then(UInt(8,1)))
        # duplicate otherwise
        def dup_otherwise():
            w = When(UInt(1,1)).then(UInt(8,1)).otherwise(UInt(8,0))
            return w.otherwise(UInt(8,0))
        self.WaitException(ErrWhenExpOperateWrong, dup_otherwise)

    def test_Cut_normal(self):
        # normal multi-bit slice
        self.assertEqual(Cut(UInt(8, 0xAB), 7, 4).attribute, UInt(4))
        # single-bit slice keeps scalar attribute UInt(1)
        self.assertEqual(Cut(UInt(8, 0xAB), 3, 3).attribute, UInt(1))

    def test_Const_type_errors(self):
        # wrong type for width or string
        self.WaitException(ErrConstInWrong, lambda: UInt([4,5]))
        self.WaitException(ErrConstInWrong, lambda: UInt(None))