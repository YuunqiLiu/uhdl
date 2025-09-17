import unittest

# pylint: disable=unused-wildcard-import
from uhdl import *
from uhdl.Demo.SparseSwitch.example_top import SparseSwitchTop
# pylint: enable=unused-wildcard-import


class TestDemoSparseSwitch(unittest.TestCase):
    def test_generate_verilog(self):
        top = SparseSwitchTop()
        top.output_dir = 'test_build/demos/SparseSwitch'
        top.generate_verilog(iteration=True)
