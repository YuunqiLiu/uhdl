#!/bin/bash
# run_headless.sh <component dir> <work dir> <task> <label> [model]
# A real end-to-end run: a new Claude Code session in a fresh project, with nothing but the task
# prompt; it has to find the skill by itself. Runs without permission prompts, so only use it in
# a sandbox you are happy to let an agent work in. Afterwards: grade.sh <work>/<label> <task> <component dir>.
set -e
E=$(cd "$(dirname "$0")" && pwd); C=$(cd "$1" && pwd); task=$3; label=$4; model=${5:-}
P=$(bash "$E/setup.sh" "$1" "$2" "$task" "$label")
cd "$P"
env -u PYTHONPATH PATH="$C/bin:$PATH" claude -p "$(cat "$E/$task/prompt.txt")" ${model:+--model "$model"} \
  --output-format stream-json --verbose --dangerously-skip-permissions > "$P/../$label.jsonl"
echo "transcript: $P/../$label.jsonl"
grep -c '"name":"Skill"' "$P/../$label.jsonl" | sed 's/^/Skill tool calls: /'
