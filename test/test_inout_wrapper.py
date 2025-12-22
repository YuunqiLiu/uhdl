"""
Test case for inout pin connections between wrapper and node modules.

Structure:
- Node module: 2 inout pins (func1, func2)
- Wrapper module: 4 inout pins (pad1, pad2, pad3, pad4)
- Wrapper instantiates 2 Node modules:
  - node1.func1 <-> pad1, node1.func2 <-> pad2
  - node2.func1 <-> pad3, node2.func2 <-> pad4
"""

import os
import sys
import unittest

from uhdl import *


class Node(Component):
    """Bottom-level module with two inout pins."""
    
    def __init__(self):
        super().__init__()
        
        # Define two inout pins
        self.inst1 = VComponent(file='test/verilog/inout_inst.v',top='inout_inst')
        self._connect_all()

    def _connect_all(self):
        self.inout_temp = [Inout(UInt(1)) for _ in range(2)]
        for i in range(2):
            self.set(f"p{i}", self.inout_temp[i])
            node_inout = self.get(f"p{i}")
            inst_inout = self.inst1.get(f"p{i}")
            SmartAssign(node_inout, inst_inout)

class Wrapper(Component):
    """Top-level wrapper module with four inout pins."""
    
    def __init__(self):
        super().__init__()
        
        self.node0 = Node()
        self.node1 = Node()
        self._connect_all()

    def _connect_all(self):
        self.inout_temp = [Inout(UInt(1)) for _ in range(4)]
        for i in range(4):
            self.set(f"pad{i}", self.inout_temp[i])
        
        for i in range(2):
            node = self.get(f"node{i}")
            for j in range(2):
                pad_inout = self.get(f"pad{i*2 + j}")
                node_inout = node.get(f"p{j}")
                SmartAssign(pad_inout, node_inout)
        

class TestInoutWrapper(unittest.TestCase):
    """Test case for inout wrapper design."""
    
    def test_generate_verilog(self):
        """Test generating Verilog for the wrapper design."""
        wrapper = Wrapper()
        wrapper.output_dir = 'test_build'
        wrapper.generate_verilog()
        
        # Check that the output files exist
        self.assertTrue(os.path.exists('test_build'))


if __name__ == '__main__':
    # For quick testing, just generate the Verilog
    wrapper = Wrapper()
    wrapper.output_dir = 'test_build/inout_wrapper'
    wrapper.generate_verilog(iteration=True)  # Generate all modules including sub-modules
    print("Verilog generated successfully in test_build/inout_wrapper/")
    
    # Print generated files
    import os
    for root, dirs, files in os.walk('test_build/inout_wrapper'):
        for f in files:
            if f.endswith('.v'):
                filepath = os.path.join(root, f)
                print(f"\n{'='*60}")
                print(f"File: {filepath}")
                print('='*60)
                with open(filepath, 'r') as vf:
                    print(vf.read())
