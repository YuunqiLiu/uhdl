#!/bin/bash
# setup.sh <bundle dir> <work dir> <task> <label> : a fresh project that holds only the skill
# (in .claude/skills/uhdl) and the task's assets. The hidden testbench stays outside.
set -e
B=$(cd "$1" && pwd); W=$2; task=$3; label=$4; E=$(cd "$(dirname "$0")" && pwd)
P=$W/$label; rm -rf "$P"; mkdir -p "$P/.claude/skills"
cp -r "$B" "$P/.claude/skills/uhdl"
[ -d "$E/$task/assets" ] && cp -r "$E/$task/assets/." "$P/"
echo "$P"
