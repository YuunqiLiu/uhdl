from uhdl import *
from uhdl.core.UHDLException import ErrUHDLStr
from typing import List, Dict, Optional, Tuple, Union

FieldSpec = Dict[str, Union[int, str, Dict[str, Union[int, str]]]]

def _field_width(field: Union[int, Dict[str, Union[int, str]]]) -> int:
    if isinstance(field, int):
        return field
    if isinstance(field, dict):
        if 'width' in field:
            return int(field['width'])
    raise ErrUHDLStr(f"Invalid field spec: {field}")


class BitfieldPack(Component):
    def __init__(self, spec: List[Tuple[str, Union[int, Dict[str, int]]]]):
        super().__init__()
        self.spec = spec

        widths = []
        for name, f in spec:
            w = _field_width(f)
            self.set(name, Input(UInt(w)))
            widths.append(w)

        total = sum(widths)
        self.out = Output(UInt(total))

        parts = [self.get(name) for name, _ in spec]
        self.out += Combine(*parts)


class BitfieldUnpack(Component):
    def __init__(self, spec: List[Tuple[str, Union[int, Dict[str, int]]]]):
        super().__init__()
        self.spec = spec

        widths = [_field_width(f) for _, f in spec]
        total = sum(widths)
        self.in_bus = Input(UInt(total))

        hi = total - 1
        for name, f in spec:
            w = _field_width(f)
            lo = hi - w + 1
            sig = Output(UInt(w))
            self.set(name, sig)
            sig += self.in_bus[hi:lo]
            hi = lo - 1
