# CAD-005/006 实现中枢审查

- 日期：2026-11-02
- 审查提交：`5f05e59`（实现）、`fea112c`（checkpoint/worklog）
- 当前结论：`review`，暂不验收，不交给下游 RET 任务
- 审查范围：白名单 IR 编译、几何/STEP 验证、冻结比较策略、错误协议、交接证据

## 已验证通过

在固定环境 Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、NumPy 1.26.4 / macOS arm64 下，独立重跑：

| 检查 | 结果 |
|---|---|
| `PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -v` | 10 项通过 |
| `python3 -m unittest discover -s tests/schema -p 'test_*.py' -v` | 17 项通过 |
| `work/benchcad-output/venv/bin/python -m unittest tests.typed_cad_ir.test_schema_contract tests.typed_cad_ir.test_axis_mapping -v` | 5 项通过 |
| 实现提交的原生对照报告 | 两个标准 IR 案例的几何指标与 BenchCAD 原生输出逐项相同；native→STEP 按冻结策略通过 |
| `git status` | 工作树干净；当前 `main` 比 `origin/main` ahead 2，未 push |

已确认编译链支持真实 JSON IR、单族固定图、前置参数校验、白名单 CadQuery 构造、单实体/有效性检查、native 重复摘要比较、STEP 导出回读及版本化 manifest。标准目录、第二孔边界、规则拒绝、多实体拒绝和导出/回读故障注入均有测试。

## 阻塞验收的问题

### P1：接受的 IR 可篡改核心几何输入而仍成功编译

复核对 `legal-catalog-row.json` 只做内存突变：将 `nodes[2].inputs.radial_offset` 替换成 `{"kind":"literal","value":100,"unit":"mm"}`。结果：

- Draft 2020-12 Schema 校验：通过；
- `validate_ir(...)`：无错误；
- `compile_ir(...)`：`ok=true`、`status=step_readback`；
- 输出仍是有效单实体且 STEP 往返检查通过；
- 体积从规范样例的约 `6712.631936 mm³` 变为 `6851.028179 mm³`，说明 cutter 已不能按 IR 映射切入套环，但验证器仍接受。

原因是 `src/cad_compilation/compiler.py` 的 `_require_contract()` 只校验节点 ID、输入字段名、输出 ID 及 placement 元数据签名，没有校验每个输入绑定是否符合冻结的公式/引用树。`src/cad_compilation/ir.py` 的语义验证也只确认表达式类别和引用/公式注册，没有约束 `radial_offset`、`hole_len`、角度等输入必须符合 `mapping.md` 的固定映射。当前拓扑/STEP 检查无法发现缺孔或孔位错误。

修正要求：对冻结首族图的关键输入执行结构化 canonical binding 校验（包括两孔角度、`wall`、`over`、`hole_len`、`z_in`、`z_out`、`radial_offset`、`axial` 及螺纹/目录引用），不执行字符串表达式；对不符合契约的 accepted IR 在 build 前拒绝。新增上述 `radial_offset=100 mm` 反例，并至少覆盖一个错误 hole length/角度反例，证明不会成功构造或导出错误零件。若这些字段本应允许自由变化，需先经 Codex 更新 IR/族规则契约，不能静默放宽。

### P2：运行时错误的 `node_ids` 恒为空

`src/cad_compilation/compiler.py` 的 `_failed_result()` 无条件写入 `"node_ids": []`。例如错误字段为 `nodes.n1.collar.revolve` 时，结构化错误没有对应 node ID，和 IR 错误协议要求的节点定位信息不符。需从稳定节点路径提取或在 `CadError` 中显式携带 `node_ids`，并增加 build/boolean 错误断言。

## 文档和范围备注

- `agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md` 第 11 节仍称合法第二孔示例尚未执行 CAD 构造/STEP 验证；当前 CAD-005/006 已有相反证据。应追加审查后状态，保留历史事实并明确本轮验证覆盖范围。
- `_cq_runtime()` 会对 OCP 的多个全局 `TopoDS_*` 类型注入基于 Python `id(self)` 的 `HashCode` 方法。这是进程级兼容性补丁，当前测试环境通过；建议实现 Agent说明其依赖原因，并确认它不会改变拓扑等价/去重语义。此项先记为风险观察，不单独阻塞本轮。
- 阶段 1 测量、ADR-0008 和 CAD-006 数值阈值均未发现被改写；跨平台/跨进程与其他零件族仍不在本轮验证范围。

## 审查决定与下一步

CAD-005/006 当前实现状态改为 `review`。P1 修复并通过中枢复核前不标记完成、不交给 RET-001/003 等下游任务。修正后至少重跑完整 CAD 编译测试、Schema 测试和 IR 契约测试，并补充被拒绝变异的测试结果；中枢再确认后决定验收。
