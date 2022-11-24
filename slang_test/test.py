import sys, os

sys.path.insert(0, os.path.abspath('../..'))
from uhdl import *



v = VComponent('test.v','adder_param',WIDTH=16,DEPTH=3)


print(v.din1.attribute)
print(v.din3.attribute)