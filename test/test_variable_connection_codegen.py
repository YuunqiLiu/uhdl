from pathlib import Path
import re
import shutil
import unittest

from uhdl import *


BUILD_ROOT = Path("test_build/test_variable_connection_codegen")


class SelfAssignTop(Component):
    def __init__(self):
        super().__init__()
        self.loop = Wire(UInt(1))
        self.loop += self.loop


class ChildOutput(Component):
    def __init__(self):
        super().__init__()
        self.data = Output(UInt(1))


class ParentWithExistingChildWire(Component):
    def __init__(self):
        super().__init__()
        self.child_data = Wire(UInt(1))
        self.child = ChildOutput()
        self.child_data += self.child.data


class TestVariableConnectionCodegen(unittest.TestCase):
    def setUp(self):
        if BUILD_ROOT.exists():
            shutil.rmtree(BUILD_ROOT)

    def test_self_assignment_is_not_emitted(self):
        top = SelfAssignTop()
        top.output_dir = str(BUILD_ROOT)
        top.generate_verilog(iteration=True)

        rtl = (BUILD_ROOT / "SelfAssignTop" / "SelfAssignTop.v").read_text()
        self.assertNotRegex(rtl, r"\bassign\s+(\w+)\s*=\s*\1\s*;")

    def test_existing_parent_wire_is_not_redeclared_for_child_output(self):
        top = ParentWithExistingChildWire()
        top.output_dir = str(BUILD_ROOT)
        top.generate_verilog(iteration=True)

        rtl = (BUILD_ROOT / "ParentWithExistingChildWire" / "ParentWithExistingChildWire.v").read_text()
        child_data_wire_defs = re.findall(r"\bwire\s+\[0:0\]\s+child_data\s*;", rtl)

        self.assertEqual(len(child_data_wire_defs), 1)
        self.assertIn(".data(child_data)", rtl)
        self.assertNotIn(".data()", rtl)


if __name__ == "__main__":
    unittest.main()
