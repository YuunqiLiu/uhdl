#!/bin/bash
# grade.sh <project dir> <task> <component dir> : the hidden testbench on the agent's out/, plus `uhdl check`
P=$(cd "$1" && pwd); task=$2; C=$(cd "$3" && pwd); E=$(cd "$(dirname "$0")" && pwd); B=$P/.grade
rm -rf "$B"; mkdir -p "$B"
[ -f "$P/out/filelist.f" ] || { echo "GRADE FAIL: no out/filelist.f"; exit 1; }
SV=(); CK=()
if [ -d "$E/$task/assets/rtl" ]; then
  for f in "$E/$task/assets/rtl"/*.sv; do
    n=$(basename "$f"); SV+=("$P/rtl/$n"); CK+=(--sv "$P/rtl/$n")
    python3 -c 'import sys; sys.exit(open(sys.argv[1],"rb").read() != open(sys.argv[2],"rb").read())' "$f" "$P/rtl/$n" \
      || echo "WARNING: rtl/$n was modified"
  done
fi
# imported SV files the agent may have added to filelist.f are given once only
grep -v '/rtl/' "$P/out/filelist.f" > "$B/gen.f"
TMPDIR=$B verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb -Mdir "$B/obj" \
  "${SV[@]}" -f "$B/gen.f" "$E/$task/hidden/tb.sv" > "$B/build.log" 2>&1 \
  || { echo "GRADE FAIL: testbench build"; grep -E '^%Error' "$B/build.log" | head -5; exit 1; }
"$B/obj/Vtb" | grep RESULT
top=$(sed -n 's/^\s*\(\w*\) dut(.*/\1/p' "$E/$task/hidden/tb.sv" | head -1)
echo "uhdl check: $("$C/bin/uhdl" check "$P/out" --top "$top" "${CK[@]}" | tail -1)"
rm -rf "$B"
