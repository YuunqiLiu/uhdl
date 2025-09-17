from uhdl import *
from typing import Dict, List, Optional


class SparseSwitchFabric(Component):
    def __init__(self, spec: Dict[str, List[str]], widths: Optional[Dict[str, int]] = None, DW: int = 32):
        super().__init__()
        self.spec = spec
        self.widths = widths or {}
        self.DW = DW

        # collect ports
        all_inputs = sorted({i for outs in spec.values() for i in outs})
        for i in all_inputs:
            w = self.widths.get(i, DW)
            self.set(i, Input(UInt(w)))

        for out, in_list in spec.items():
            if len(in_list) == 0:
                raise Exception(f"Output {out} has empty candidate list")
            w = self.widths.get(out, self.widths.get(in_list[0], DW))
            self.set(out, Output(UInt(w)))
            sel_w = 1
            while (1 << sel_w) < len(in_list):
                sel_w += 1
            self.set(f"sel_{out}", Input(UInt(sel_w if len(in_list) > 1 else 1)))

            sel_sig = self.get(f"sel_{out}")
            cases = []
            for idx, in_name in enumerate(in_list):
                src = self.get(in_name)
                if src.attribute.width > w:
                    src_expr = src[src.attribute.width-1:src.attribute.width-w]
                elif src.attribute.width < w:
                    pad = UInt(w - src.attribute.width, 0)
                    src_expr = Combine(pad, src)
                else:
                    src_expr = src
                cases.append((UInt(sel_sig.attribute.width, idx), src_expr))

            default_expr = UInt(w, 0)
            out_sig = self.get(out)
            out_sig += Case(sel_sig, cases, default_expr)
