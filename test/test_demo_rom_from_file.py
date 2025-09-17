import unittest

# pylint: disable=unused-wildcard-import
from uhdl import *
from uhdl.Demo.RomFromFile.example_top import RomTop
# pylint: enable=unused-wildcard-import


class TestDemoRomFromFile(unittest.TestCase):
    def test_generate_verilog(self):
        top = RomTop()
        top.output_dir = 'test_build/demos/RomFromFile'
        top.generate_verilog(iteration=True)
