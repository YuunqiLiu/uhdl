import unittest

# pylint: disable=unused-wildcard-import
from uhdl import *
from uhdl.Demo.Bitfield.example_top import BitfieldTop
from uhdl.Demo.DynamicPipeline.example_top import PipelineTop
from uhdl.Demo.SparseSwitch.example_top import SparseSwitchTop
from uhdl.Demo.RomFromFile.example_top import RomTop
# pylint: enable=unused-wildcard-import


class TestDemos(unittest.TestCase):
    def test_bitfield_generate_verilog(self):
        top = BitfieldTop()
        top.output_dir = 'test_build/demos/Bitfield'
        top.generate_verilog(iteration=True)
        top.generate_filelist(abs_path=True)
        top.run_slang_compile()

    def test_dynamic_pipeline_generate_verilog(self):
        top = PipelineTop()
        top.output_dir = 'test_build/demos/DynamicPipeline'
        top.generate_verilog(iteration=True)
        top.generate_filelist(abs_path=True)
        top.run_slang_compile()

    def test_sparse_switch_generate_verilog(self):
        top = SparseSwitchTop()
        top.output_dir = 'test_build/demos/SparseSwitch'
        top.generate_verilog(iteration=True)
        top.generate_filelist(abs_path=True)
        top.run_slang_compile()

    def test_rom_from_file_generate_verilog(self):
        top = RomTop()
        top.output_dir = 'test_build/demos/RomFromFile'
        top.generate_verilog(iteration=True)
        top.generate_filelist(abs_path=True)
        top.run_slang_compile()
