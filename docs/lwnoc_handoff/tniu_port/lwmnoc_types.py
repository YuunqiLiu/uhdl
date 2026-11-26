"""Types and parameters of lwmnoc_pack, read from the SV package itself (single source of truth)."""
from uhdl import import_sv_package

MNOC = '/workspace/lwnoc_dev/lwnoc/lwnoc_mnoc/de/rtl'
PACK = [f'{MNOC}/lwmnoc_define.sv', f'{MNOC}/niu_base/lwmnoc_common_define.sv', f'{MNOC}/lwmnoc_pack.sv']
pk = import_sv_package(PACK, 'lwmnoc_pack')
