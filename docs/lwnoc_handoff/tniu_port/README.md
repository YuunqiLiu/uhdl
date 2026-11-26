# TNIU write channel in UHDL

A port of the lwnoc_mnoc TNIU write channel (`de/rtl/tniu_sys_side`) to UHDL (`lwnoc_rewrite`).
Every level is cycle-equivalent to the RTL.

| File | Replaces (RTL) | Notes |
|---|---|---|
| `lwmnoc_types.py` | – | structs and parameters read from `lwmnoc_pack.sv` with `import_sv_package` |
| `rob_entry.py` | `lwmnoc_downstream_rob_entry.sv` | when-blocks for the entry state machine |
| `write_rob.py` | `lwmnoc_downstream_write_rob.sv` | 64 entries; fcip/lwnoc IP imported with `VComponent`; IP registry `IP` |
| `write_buffer.py` | `lwmnoc_downstream_write_buffer.sv` + `niu_base/lwmnoc_downstream_write_buffer_sender.sv` | sender rewritten in UHDL |
| `write_channel.py` | `lwmnoc_tniu_write_channel.sv` | top of the write channel |

## Equivalence checks
Each script generates the UHDL design, renames its modules (`*_uhdl`) and simulates it next to the
RTL with Verilator, comparing every output on every cycle. Set `TMPDIR` to a roomy directory.

| Script | Stimulus |
|---|---|
| `run_eq.sh` | random inputs, 200k cycles |
| `run_eq_write_rob.sh` | random inputs in two address-conflict phases, 200k cycles |
| `run_eq_write_buffer.sh` | closed-loop traffic: requests, data after DBID responses, data SRAM, B after W tail |
| `run_eq_write_channel.sh` | as above plus the request-FIFO SRAM and real AXI B → ring Comp |

## Generating
`PYTHONPATH=/workspace/lwnoc_dev/uhdl_work /workspace/lwnoc_dev/.venv/bin/python write_channel.py --out <dir>`
writes the UHDL modules and the packed-port shims for imported IP with unpacked-array ports. A
simulator also needs the IP sources (`write_rob.IP_FILES`, or `rtl_write_channel.f`).
