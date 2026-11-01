# IR-001-R2 checkpoint

```text
task=IR-001-R2
status=review
changed=agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md; agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json; agent-work/typed-cad-ir/IR-001-v0/mapping.md; agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md; agent-work/typed-cad-ir/IR-001-v0/examples/*.json; agent-work/typed-cad-ir/IR-001-v0/checkpoint.md
verified=Draft 2020-12 jsonschema validator in /tmp/ir001r1-jsonschema-venv（Draft202012Validator.check_schema + 5 examples PASS）；python3 -m json.tool（Schema + 5 examples PASS）；/tmp/ir001r2_validate.py（5 examples schema+semantic PASS；12 counterexamples rejected）；git diff --check
contract_fixes=固定 source commit；五种 node_type 的输入/输出/properties 契约；validation_result ok/errors/stage/status 一致性；accepted 参数字典序；新增 second_screw=1 结构合法案例
known_limits=未实现 CAD-005 编译器和 CAD-006 几何/STEP 验证器；公式参数名/单位传播/容差与几何摘要容差仍待下游冻结；second_screw=1 示例仅 IR 结构合法、未做 CadQuery/STEP 运行；STEP 字节 hash 不稳定；source snapshot、外部图纸和生成资产仍 reproducibility_partial/license_scope_uncertain
next=Codex 中枢最终复核后再启动 CAD-005/006
```

## 本轮修正

1. `source.source_commit` 在 Schema 中固定为 `035f467142888edfd0bd7cd73906f9b155c8f43c`；语义检查保留 `IR_SOURCE_COMMIT_MISMATCH`，正文和 mapping 明确其他 commit 不能冒充同一 v0 数据契约。
2. 五种首族 node type 现在都有按类型分派的最小输入、输出和 properties 契约。核心字段不能由 `family_extension` 替代；缺失/类型/输出/属性问题使用 `IR_NODE_INPUT_MISSING`、`IR_NODE_INPUT_KIND_MISMATCH`、`IR_NODE_OUTPUT_CONTRACT_MISMATCH`、`IR_NODE_PROPERTIES_CONTRACT_MISMATCH`。
3. `validation_result` 由 Schema 和语义检查共同约束：`ok=true` 必须 errors 为空，`ok=false` 必须至少一条错误，错误 stage 必须等于 result stage，且只能出现在 accepted IR。
4. accepted 参数数组统一为 `bore_d, outer_d, screw_d, screw_len, second_screw, width`；新增 `legal-second-screw.json`，包含 `bore_d=80`、条件第二孔、135°、相同孔节点输入契约和 secondary result 选择。

## 验证边界

使用临时隔离环境 `/tmp/ir001r1-jsonschema-venv` 安装 `jsonschema>=4,<5`，未写入仓库。`Draft202012Validator.check_schema(schema)` 通过，五个示例均通过 Draft 2020-12 验证；`python3 -m json.tool` 只证明 JSON 语法。临时反例脚本确认错误 source commit、缺失 thread_d、缺失 boolean base/tool、缺失 result selector、validation_result cardinality、参数顺序被 Schema 拒绝，且 second_screw 规则、未来依赖和缺失 output 引用被语义检查拒绝。没有运行或声称完成 CadQuery/STEP 几何验证。

R1 保留的边界仍有效：当前 snapshot 只能是 `reproducibility_partial`；真实螺旋布尔 M3–M8 可能 no-op；STEP 字节 hash 不稳定；外部图纸和生成资产许可范围仍不确定。
