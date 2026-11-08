#!/bin/bash
# setup.sh <extracted component> <work dir> <task> <label> : a fresh project holding only the component's
# Skill (in .claude/skills/uhdl) and the task's assets. The hidden testbench stays outside; the
# `uhdl` command comes from the component root on PATH (a toolkit install puts it in bin/).
set -e
C=$(cd "$1" && pwd); W=$2; task=$3; label=$4; E=$(cd "$(dirname "$0")" && pwd)
P=$W/$label; rm -rf "$P"; mkdir -p "$P/.claude/skills"
cp -r "$C/skill/uhdl-design" "$P/.claude/skills/uhdl-design"
[ -d "$E/$task/assets" ] && cp -r "$E/$task/assets/." "$P/"
echo "$P"
