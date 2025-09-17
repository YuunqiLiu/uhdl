import unittest

# pylint: disable=unused-wildcard-import
from uhdl import *
from uhdl.Demo.DynamicPipeline.example_top import PipelineTop
# pylint: enable=unused-wildcard-import


class TestDemoDynamicPipeline(unittest.TestCase):
    def test_generate_verilog(self):
        top = PipelineTop()
        top.output_dir = 'test_build/demos/DynamicPipeline'
        top.generate_verilog(iteration=True)
