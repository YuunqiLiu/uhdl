# UHDL agent skill

`skill/uhdl/` is a Claude Code skill that teaches an agent to write UHDL designs and brings
everything needed to run them: UHDL and pyslang wheels, installed offline into a virtual
environment made from whatever Python 3.8+ the machine has.

## Build

```bash
python skill/build.py                          # -> dist/skill/uhdl/ and dist/skill/uhdl-skill-<version>.tar.gz
python skill/build.py --platform linux-x86_64 --platform linux-aarch64   # more platforms
```
Building needs network access to PyPI. The result does not. `references/guide.md` is copied
from `docs/LLM_GUIDE.md` and `references/example_gen.py` from `docs/llm_example/gen.py`, so
edit those, not the copies. `VERSION` is the UHDL version plus the git revision.

| Bundled | For |
|---|---|
| `uhdl-<ver>-py3-none-any.whl` | all Pythons ≥3.8 |
| `pyslang-8.1.0-cp38/39/310` | Python 3.8–3.10 |
| `pyslang-12.1.0-cp311-abi3` + `nanobind_backend-cp311…cp315` | Python 3.11–3.15 |
| `pip-24.3.1` | replaces old system pips that cannot install manylinux_2_27 wheels |

About 20 MB per platform.

## Install

Copy (or untar) `uhdl/` to one of:
- `~/.claude/skills/uhdl` (all projects; use `$CLAUDE_CONFIG_DIR/skills` if that is set)
- `<project>/.claude/skills/uhdl` (one project)

The first use creates `~/.cache/uhdl-skill/<version>-py<X.Y>-<machine>/` (about 40 MB).
`UHDL_VENV` and `UHDL_PYTHON` override where it goes and which Python it uses.

## What the agent gets

- `SKILL.md`: when to use the skill, setup, workflow (read the guide, generate, check,
  simulate), and the mistakes seen most often.
- `scripts/uhdl_env.sh`: prints a python with UHDL. It handles a missing ensurepip or venv
  module and old pips, and lets parallel agents share one environment (a lock). Without a
  matching pyslang wheel it installs UHDL without SV import and says so.
- `scripts/uhdl_check.py`: Verilator `-Wall` lint and a Yosys synth/`check -assert`. Each
  message is mapped back to the Python line via the `// file.py:line` comments in the
  generated Verilog. A missing tool is reported as SKIPPED, never as a pass.
