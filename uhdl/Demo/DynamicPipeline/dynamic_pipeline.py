from uhdl import *
from typing import List, Dict, Optional


def _op_apply(op: str, a, b):
    op = op.lower()
    if op == 'id':
        return a
    if op == 'add':
        return a + (b if b is not None else a)
    if op == 'sub':
        return a - (b if b is not None else a)
    if op == 'mul':
        return a * (b if b is not None else a)
    if op == 'and':
        return a & (b if b is not None else a)
    if op == 'or':
        return a | (b if b is not None else a)
    if op == 'xor':
        return a ^ (b if b is not None else a)
    raise Exception(f"Unsupported op: {op}")


class DynamicPipeline(Component):
    def __init__(self, stages: List[Dict]):
        super().__init__()
        assert len(stages) >= 1, 'stages must be non-empty'
        self.stages = stages

        self.din = Input(UInt(stages[0]['w']))
        self.dout = Output(UInt(stages[-1]['w']))

        # optional global clk/rst for registers; expose to top to allow tying
        self.clk = Input(UInt(1))
        self.rst_n = Input(UInt(1))

        cur = self.din
        for idx, st in enumerate(stages):
            w = int(st['w'])
            op = st.get('op', 'id')
            use_reg = bool(st.get('reg', False))
            const = st.get('const', None)

            # adapt width if needed by slicing/zero-extend (simple policy: cut MSBs or zero-extend)
            if cur.attribute.width > w:
                cur = cur[cur.attribute.width-1:cur.attribute.width-w]
            elif cur.attribute.width < w:
                pad = UInt(w - cur.attribute.width, 0)
                cur = Combine(pad, cur)

            rhs_b = UInt(w, int(const)) if const is not None else None
            cur = _op_apply(op, cur, rhs_b)

            # After operation, 'cur' width may grow (e.g., add/mul). Re-align to stage width.
            if cur.attribute.width > w:
                cur = cur[cur.attribute.width-1:cur.attribute.width-w]
            elif cur.attribute.width < w:
                pad2 = UInt(w - cur.attribute.width, 0)
                cur = Combine(pad2, cur)

            if use_reg:
                r = Reg(UInt(w), self.clk, self.rst_n)
                r_name = f's{idx}_reg'
                self.set(r_name, r)
                Assign(r, cur)
                cur = r

        # final width adapt to output if needed
        if cur.attribute.width > self.dout.attribute.width:
            cur = cur[cur.attribute.width-1:cur.attribute.width-self.dout.attribute.width]
        elif cur.attribute.width < self.dout.attribute.width:
            pad = UInt(self.dout.attribute.width - cur.attribute.width, 0)
            cur = Combine(pad, cur)

        self.dout += cur
