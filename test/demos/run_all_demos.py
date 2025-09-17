# This script instantiates each demo top and generates Verilog into test_build/.
# It does not execute external tools or run unit tests.
from uhdl import *

# Bitfield
from uhdl.Demo.Bitfield.example_top import BitfieldTop
# DynamicPipeline
from uhdl.Demo.DynamicPipeline.example_top import PipelineTop
# SparseSwitch
from uhdl.Demo.SparseSwitch.example_top import SparseSwitchTop
# RomFromFile
from uhdl.Demo.RomFromFile.example_top import RomTop


def build(comp):
    comp.output_dir = 'test_build'
    comp.generate_verilog(iteration=True)


def main():
    build(BitfieldTop())
    build(PipelineTop())
    build(SparseSwitchTop())
    build(RomTop())


if __name__ == '__main__':
    main()
