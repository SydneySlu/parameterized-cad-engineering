# IR-001 checkpoint

```text
task=IR-001
status=review
changed=agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md; agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json; agent-work/typed-cad-ir/IR-001-v0/mapping.md; agent-work/typed-cad-ir/IR-001-v0/examples/; agent-work/typed-cad-ir/IR-001-v0/checkpoint.md
verified=python3 -m json.tool ir-v0.schema.json；python3 -m json.tool examples/*.json；/tmp/validate_ir_examples.py（4 个示例通过）；git diff --check
ir_version=typed-cad-ir.v0
known_limits=仅 set_screw_shaft_collar；未实现 CadQuery/OCP 编译器、实体/STEP 验证器、真实螺旋线程、第二族扩展；STEP 字节 hash 不稳定；CAD-006 容差/摘要算法待冻结
next=Codex 审查后交给 CAD-005/006
```

## 完成比例

约 90%。v0 的字段、版本、节点白名单、依赖/引用、参数来源、前置规则、错误分层、序列化定义、合法/缺失/规则拒绝/验证失败示例和复现边界已完成。剩余工作属于审查与下游契约冻结，不在本任务中实现。

## 已覆盖的审查要点

- `check()`/Schema 规则在 `build()` 前执行；规则拒绝不会生成可执行节点。
- `outer_d`、`width`、`screw_d`、`screw_len` 的目录派生和 `second_screw` 的规则派生均保留来源和 `source_ref`。
- `screw_len` 明确是目录/任务字段，v0 几何孔节点不把它误作孔深。
- 构造失败、实体有效性/多实体失败和 STEP 导出/回读失败使用不同阶段和错误码。
- `revolved_ring_approximation`、M3–M8 可能 no-op、`reproducibility_partial` 和 STEP 字节 hash 不稳定均被写入接口语义。
- 第二族只获得公共包络和 `family_data` 命名空间；没有声明已支持跨族构造。

## 待 Codex 中枢确认

1. 是否冻结 `CAD-006.pending.v0` 的容差 profile、体积/包围盒量化以及面/边签名算法。
2. 是否接受环形线程近似作为首期输出，或要求构造器将其报告为降级结果。
3. 是否把 `directory_id` 提升为所有族的公共来源字段。
4. `family_data` 扩展的独立 JSON Schema URI、注册表和兼容检查责任人。
5. 生成 STEP/渲染图的发布许可仍为 `license_scope_uncertain`。

## 不在本任务范围

不修改 `src/` 生产代码，不实现 IR 编译器、CadQuery/OCP 构造器、STEP 验证器、Prompt、检索库或大规模数据处理。
