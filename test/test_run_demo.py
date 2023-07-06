import os,sys
import unittest

# pylint: disable =unused-wildcard-import
from ..Demo         import *
from ..core import *
# pylint: enable  =unused-wildcard-import



class TestRunDemo(unittest.TestCase):

    def test_Crossbar(self):
        res = Crossbar(2,2,32,1)
        res.output_path = './Vout/Demo/Crossbar'
        res.generate_verilog(iteration=True)
        #print(Demo)
