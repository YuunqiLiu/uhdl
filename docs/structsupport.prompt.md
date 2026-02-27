## Plan: UHDL Struct 全链路支持（DRAFT）

本方案将把 `struct` 从“部分可用”升级到 UHDL 的一等公民：可原生定义、可从 Verilog/SV 导入、可整包互联、可字段拆解、可组合表达式构造，并保持严格类型安全。核心思路是：先建立统一的 `StructType` 类型系统与字段引用模型，再让 `VComponent` 导入和连接/代码生成都复用同一套语义，最后补齐 lint、异常、回归测试和文档。你要求“一步到位全覆盖”，因此解析层将从当前 best-effort 升级为 AST 驱动的完整类型还原，避免 regex 方案在 nested/array/enum/union 上失真。

**Steps**
1. 在 [uhdl/core/Variable.py](uhdl/core/Variable.py) 建立统一 Struct 类型内核（如 `StructType`/`StructFieldRef` 语义），并让 `StructIO` 真正暴露字段成员（支持 `s.sig1` 点访问），同时保留父子命名链路与字段顺序。
2. 在 [uhdl/core/Variable.py](uhdl/core/Variable.py) 重构 `__iadd__` 的类型判定为“严格同类型”策略：struct 互联必须同 typedef 身份（或同 canonical type id），禁止仅凭总位宽通过。
3. 在 [uhdl/core/Operator.py](uhdl/core/Operator.py) 与 [uhdl/core/Function.py](uhdl/core/Function.py) 增加 struct 组合表达式与分解连接语义，覆盖 `a += s.f`、`s.f += b`、`s1 += s2`、`s += Combine(...)`、字段位切片混用。
4. 在 [uhdl/core/Component.py](uhdl/core/Component.py) 修正端口/左值收集逻辑，让 struct IO 进入 `input_list`、`output_list`、`lvalue_list`、`outer_lvalue_list` 全路径，确保生成 assign/实例连接/层级连接不漏 struct。
5. 在 [uhdl/core/VComponent.py](uhdl/core/VComponent.py) 将 struct 导入从当前浅解析升级为 AST 完整还原：支持 typedef/inline、nested struct、enum/union、packed/unpacked array、多维声明及别名链解析；保留 `struct_mode='packed'` 作为兼容回退。
6. 在 [uhdl/core/VComponent.py](uhdl/core/VComponent.py) 和相关类型层补齐“严格同类型”导入映射（typedef identity），让外部 SV 类型与 UHDL 内部类型身份一致，保证跨模块互联判等稳定。
7. 在 [uhdl/core/Exception.py](uhdl/core/Exception.py) 与 [uhdl/core/UHDLException.py](uhdl/core/UHDLException.py) 增加 struct 专用错误：类型不匹配、字段不存在、非法拆解、不可组合表达式等，报错信息带字段路径与期望类型。
8. 在 [uhdl/core/Lint.py](uhdl/core/Lint.py)、[uhdl/core/Component.py](uhdl/core/Component.py)、[uhdl/core/VComponent.py](uhdl/core/VComponent.py) 补齐 struct lint 规则：未连接字段、部分连接、方向错误、非法隐式转换。
9. 在 [uhdl/extension/PerfectAssign.py](uhdl/extension/PerfectAssign.py) 对齐 core 语义，避免 `SmartAssign` 与扩展 helper 在 struct 上行为分叉。
10. 新增/扩展测试：  
   - [test/test_StructIO.py](test/test_StructIO.py)：原生定义、字段访问、整包连接、组合表达式、位切片混用、负例（类型不匹配）。  
   - 新增 `test/test_StructTypeSystem.py`：严格同类型判等、typedef identity、schema相同但类型不同的拒绝。  
   - 新增 `test/test_VComponent_struct_full.py`：SV 全覆盖导入（nested/enum/union/arrays/alias chain）。  
   - 扩展 [test/test_inout_integration.py](test/test_inout_integration.py) 与 [test/test_slang_compile.py](test/test_slang_compile.py)：生成与编译链验证。
11. 文档补齐：在 [README.md](README.md)、[docs/import_verilog.rst](docs/import_verilog.rst)、[docs/basic_syntax.rst](docs/basic_syntax.rst) 增加 struct 设计原则、支持矩阵、示例与限制说明（明确 InOut 计划到下一期）。
12. 回归与兼容性守护：保证非 struct 现有测试全绿；保留 `struct_mode='packed'` 旧行为；新增迁移说明，避免旧项目因“位宽等价可连”被新严格规则破坏（给出显式转换路径）。

**Verification**
- 运行结构化测试集：`test/test_StructIO.py`、新增 struct 类型系统与导入全覆盖测试、`test/test_slang_compile.py`。  
- 运行全量回归，确认非 struct 用例无退化。  
- 对生成的 Verilog 做编译验证（slang 流程），确认 dot-field、组合表达式展开和 package import 均正确。  
- 增加负例断言：同宽不同 struct 类型必须失败且错误信息可定位到字段路径。

**Decisions**
- 严格类型安全：选择“严格同类型”而非“同 schema”或“同位宽”。  
- 作用域控制：`struct InOut` 明确拆到下一期，先把 Input/Output 全链路做到稳定完整。  
- 兼容策略：保留 `struct_mode='packed'`，作为历史工程与复杂场景回退路径。  
- 解析策略：放弃仅 regex 的 best-effort，改为 AST 驱动完整还原以满足“一步到位全覆盖”。
