import unittest
import os

# pylint: disable=unused-wildcard-import
from uhdl import *
from uhdl.Demo.Bitfield.example_top import BitfieldTop
from uhdl.Demo.DynamicPipeline.example_top import PipelineTop
from uhdl.Demo.SparseSwitch.example_top import SparseSwitchTop
from uhdl.Demo.RomFromFile.example_top import RomTop
# pylint: enable=unused-wildcard-import


class TestDemos(unittest.TestCase):
    def test_fir_parallel_generate_verilog(self):
        from uhdl.Demo.FIR.FIRParallel import FIRParallel
        fir = FIRParallel(tap_num=8, data_width=16, coef_width=16)
        fir.output_dir = 'test_build/demos/FIRParallel'
        fir.generate_verilog(iteration=True)
        fir.generate_filelist(abs_path=True)
        fir.run_slang_compile()
        # 生成并保存面积报告
        area_report = fir.report_area()
        os.makedirs('test_build/demos/FIRParallel/area_reports', exist_ok=True)
        with open('test_build/demos/FIRParallel/area_reports/fir_parallel_area_report.txt', 'w') as f:
            f.write(area_report)
        print("FIRParallel area report saved to test_build/demos/FIRParallel/area_reports/fir_parallel_area_report.txt")

    def test_bitfield_generate_verilog(self):
        top = BitfieldTop()
        top.output_dir = 'test_build/demos/Bitfield'
        top.generate_verilog(iteration=True)
        top.generate_filelist(abs_path=True)
        top.run_slang_compile()
        
        # Generate and save area report to file
        area_report = top.report_area()
        os.makedirs('test_build/demos/Bitfield/area_reports', exist_ok=True)
        with open('test_build/demos/Bitfield/area_reports/bitfield_area_report.txt', 'w') as f:
            f.write(area_report)
        print("Bitfield area report saved to test_build/demos/Bitfield/area_reports/bitfield_area_report.txt")

    def test_dynamic_pipeline_generate_verilog(self):
        top = PipelineTop()
        top.output_dir = 'test_build/demos/DynamicPipeline'
        top.generate_verilog(iteration=True)
        top.generate_filelist(abs_path=True)
        top.run_slang_compile()
        
        # Generate and save area report to file
        area_report = top.report_area()
        os.makedirs('test_build/demos/DynamicPipeline/area_reports', exist_ok=True)
        with open('test_build/demos/DynamicPipeline/area_reports/dynamic_pipeline_area_report.txt', 'w') as f:
            f.write(area_report)
        print("DynamicPipeline area report saved to test_build/demos/DynamicPipeline/area_reports/dynamic_pipeline_area_report.txt")

    def test_sparse_switch_generate_verilog(self):
        top = SparseSwitchTop()
        top.output_dir = 'test_build/demos/SparseSwitch'
        top.generate_verilog(iteration=True)
        top.generate_filelist(abs_path=True)
        top.run_slang_compile()
        
        # Generate and save area report to file
        area_report = top.report_area()
        os.makedirs('test_build/demos/SparseSwitch/area_reports', exist_ok=True)
        with open('test_build/demos/SparseSwitch/area_reports/sparse_switch_area_report.txt', 'w') as f:
            f.write(area_report)
        print("SparseSwitch area report saved to test_build/demos/SparseSwitch/area_reports/sparse_switch_area_report.txt")

    def test_rom_from_file_generate_verilog(self):
        top = RomTop()
        top.output_dir = 'test_build/demos/RomFromFile'
        top.generate_verilog(iteration=True)
        top.generate_filelist(abs_path=True)
        top.run_slang_compile()
        
        # Generate and save area report to file
        area_report = top.report_area()
        os.makedirs('test_build/demos/RomFromFile/area_reports', exist_ok=True)
        with open('test_build/demos/RomFromFile/area_reports/rom_from_file_area_report.txt', 'w') as f:
            f.write(area_report)
        print("RomFromFile area report saved to test_build/demos/RomFromFile/area_reports/rom_from_file_area_report.txt")
