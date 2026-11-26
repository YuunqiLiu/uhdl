#!/usr/bin/env bash
# Generate the UHDL write ROB and compare it cycle by cycle with the lwnoc_mnoc RTL (200k random cycles).
# The UHDL modules are renamed (*_uhdl) so both versions can live in one simulation; fcip/lwnoc IP is shared.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
W=${TMPDIR:-$HERE/build}/write_rob_eq; rm -rf $W; mkdir -p $W/ux
TMPDIR=$W PYTHONPATH=/workspace/lwnoc_dev/uhdl_work /workspace/lwnoc_dev/.venv/bin/python $HERE/write_rob.py --out $W/gen > /dev/null
for f in $W/gen/*.v $W/gen/*.sv; do
  sed -e 's/\blwmnoc_downstream_write_rob\b/write_rob_uhdl/g; s/\blwmnoc_downstream_rob_entry\b/rob_entry_uhdl/g' $f > $W/ux/$(basename $f)
done
TMPDIR=$W verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -O1 --top-module tb_eq -Mdir $W/obj \
  -f $HERE/rtl_write_rob.f $W/ux/*.sv $W/ux/*.v $HERE/tb_write_rob_eq.sv > $W/build.log 2>&1
$W/obj/Vtb_eq | grep RESULT
rm -rf $W
