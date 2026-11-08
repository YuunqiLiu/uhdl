#!/bin/bash
# setup.sh <component dir> <work dir> <task> <label> : a fresh project holding only the component's
# Skill (in .claude/skills/uhdl) and the task's assets. The hidden testbench stays outside; the
# `uhdl` command comes from <component>/bin on PATH, as in a toolkit install.
set -e
C=$(cd "$1" && pwd); W=$2; task=$3; label=$4; E=$(cd "$(dirname "$0")" && pwd)
P=$W/$label; rm -rf "$P"; mkdir -p "$P/.claude/skills"
cp -r "$C/skills/uhdl/uhdl-design" "$P/.claude/skills/uhdl-design"
[ -d "$E/$task/assets" ] && cp -r "$E/$task/assets/." "$P/"
echo "$P"
