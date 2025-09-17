from uhdl import *
from typing import Dict, List, Tuple, Union, Optional
import os

KV = Union[Dict[int, int], List[Tuple[int, int]]]

def _load_kv(data: Union[str, KV]) -> List[Tuple[int, int]]:
    if isinstance(data, dict):
        return sorted([(int(k), int(v)) for k, v in data.items()], key=lambda x: x[0])
    if isinstance(data, list):
        return sorted([(int(k), int(v)) for k, v in data], key=lambda x: x[0])
    if isinstance(data, str):
        path = data
        if not os.path.exists(path):
            raise Exception(f"ROM file not found: {path}")
        items = []
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [p.strip() for p in (line.split(',') if ',' in line else line.split())]
                if len(parts) != 2:
                    raise Exception(f"Invalid ROM line: {line}")
                k, v = int(parts[0], 0), int(parts[1], 0)
                items.append((k, v))
        return sorted(items, key=lambda x: x[0])
    raise Exception("Unsupported ROM data type")

class RomFromFile(Component):
    def __init__(self, data: Union[str, KV], key_w: int, val_w: int, default: int = 0):
        super().__init__()
        self.key = Input(UInt(key_w))
        self.val = Output(UInt(val_w))

        kv = _load_kv(data)
        cases = []
        for k, v in kv:
            cases.append((UInt(key_w, k), UInt(val_w, v)))
        self.val += Case(self.key, cases, UInt(val_w, default))
