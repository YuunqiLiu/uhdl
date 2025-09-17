import unittest

# pylint: disable=unused-wildcard-import
from uhdl import *
from uhdl.Demo.Bitfield.example_top import BitfieldTop
# pylint: enable=unused-wildcard-import


class TestDemoBitfield(unittest.TestCase):
    def test_generate_verilog(self):
        top = BitfieldTop()
        top.output_dir = 'test_build/demos/Bitfield'
        top.generate_verilog(iteration=True)
