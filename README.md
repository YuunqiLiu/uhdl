# uhdl

[Wiki](../../wiki)

## Struct Support

UHDL supports SystemVerilog `typedef struct packed` as first-class IO types:

- **Import**: `VComponent` automatically recognizes struct typedef ports from slang AST and creates `InputStructIO`/`OutputStructIO` with field metadata.
- **Field access**: `vc.s_in.a` returns a `StructFieldRef` with correct width and signedness.
- **Type safety**: Struct connections enforce strict typedef identity — same bit width with different typedef names is rejected.
- **Backward compatible**: Use `struct_mode='packed'` to fall back to flat bit vectors.

See [docs/import_verilog.rst](docs/import_verilog.rst) for detailed documentation.