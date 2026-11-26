#!/usr/bin/env bash
# Generate the UHDL rob_entry and compare it cycle by cycle with the lwnoc_mnoc RTL (200k random cycles).
set -e
HERE=$(cd "$(dirname "$0")" && pwd); R=/workspace/lwnoc_dev/lwnoc/lwnoc_mnoc/de/rtl
W=${TMPDIR:-$HERE/build}/rob_entry_eq; rm -rf $W; mkdir -p $W
PYTHONPATH=/workspace/lwnoc_dev/uhdl_work /workspace/lwnoc_dev/.venv/bin/python $HERE/rob_entry.py --out $W/gen > /dev/null
sed 's/^module lwmnoc_downstream_rob_entry (/module rob_entry_uhdl (/' $W/gen/lwmnoc_downstream_rob_entry.v > $W/uhdl_rob_entry.v
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -O1 --top-module tb_eq -Mdir $W/obj \
  $R/lwmnoc_define.sv $R/lwmnoc_pack.sv $R/tniu_sys_side/lwmnoc_downstream_rob_entry.sv $W/uhdl_rob_entry.v $HERE/tb_rob_entry_eq.sv > $W/build.log 2>&1
$W/obj/Vtb_eq | grep RESULT
rm -rf $W
