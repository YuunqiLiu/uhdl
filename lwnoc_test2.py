import uhdl
from uhdl import *



N = Network(name='config_bus_hub')

s0 = Slave('s0',0)
s1 = Slave('s1',1)
s2 = Slave('s2',0)


s10 = Slave('s10',0)
s11 = Slave('s11',1)
s12 = Slave('s12',0)


d0 = Switch('d0',0)
d1 = Switch('d1',0)
d2 = Switch('d2',0)

a0 = Arbiter('a0',0)
a1 = Arbiter('a1',1)
a2 = Arbiter('a2',2)
an = Arbiter('an',0)

r0 = Switch('r0',0)
d0 = Decoder('d0',0)

m0 = Master('m0',3)
m1 = Master('m1',4)
m2 = Master('m2',0)

mn = Master('mn',0)

N.add(s0)
N.add(s1)
N.add(s2)

N.add(s10)
N.add(s11)
N.add(s12)

N.add(d0)
N.add(d1)
N.add(d2)

N.add(a0)
N.add(a1)
N.add(a2)

N.add(an)


N.add(m0)
N.add(m1)
N.add(m2)
N.add(mn)

N.link(s0,d0)
N.link(s1,d1)
N.link(s2,d2)

N.link(an,mn)

N.link(d0,an)
N.link(d0,a0)

N.link(d1,an)
N.link(d1,a1)

N.link(d2,an)
N.link(d2,a2)

N.link(s10,a0)
N.link(s11,a1)
N.link(s12,a2)


N.link(a0,m0)
N.link(a1,m1)
N.link(a2,m2)
#N.link(a0,d0)
#N.link(d0,m0)
#N.link(d0,m1)


N._show()
N.rtl_prefix = 'sc_cbh'
N.generate_verilog()
