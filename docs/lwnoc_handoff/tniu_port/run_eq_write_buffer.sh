#!/usr/bin/env bash
# Generate the UHDL write buffer and compare it cycle by cycle with the lwnoc_mnoc RTL (closed-loop traffic model).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
W=${TMPDIR:-$HERE/build}/write_buffer_eq; rm -rf $W; mkdir -p $W/ux
TMPDIR=$W PYTHONPATH=/workspace/lwnoc_dev/uhdl_work /workspace/lwnoc_dev/.venv/bin/python $HERE/write_buffer.py --out $W/gen > /dev/null
for f in $W/gen/*.v $W/gen/*.sv; do
  sed -e 's/\blwmnoc_downstream_write_buffer\b/write_buffer_uhdl/g; s/\blwmnoc_downstream_write_buffer_sender\b/write_buffer_sender_uhdl/g' \
      -e 's/\blwmnoc_downstream_write_rob\b/write_rob_uhdl/g; s/\blwmnoc_downstream_rob_entry\b/rob_entry_uhdl/g' $f > $W/ux/$(basename $f)
done
TMPDIR=$W verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -O1 --top-module tb_eq -Mdir $W/obj \
  -f $HERE/rtl_write_buffer.f $W/ux/*.sv $W/ux/*.v $HERE/tb_write_buffer_eq.sv > $W/build.log 2>&1 || { grep -E '^%Error' $W/build.log | head; exit 1; }
$W/obj/Vtb_eq | grep -E "RESULT|MISMATCH"
[ -n "$KEEP" ] || rm -rf $W
