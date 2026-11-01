# IR-001-R1 checkpoint

```text
task=IR-001-R1
status=review
changed=agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md; agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json; agent-work/typed-cad-ir/IR-001-v0/mapping.md; agent-work/typed-cad-ir/IR-001-v0/examples/*.json; agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md; agent-work/typed-cad-ir/IR-001-v0/checkpoint.md
verified=Draft 2020-12 jsonschema validator in /tmp/ir001r1-jsonschema-venv（schema self-check + 4 examples PASS）；python3 -m json.tool（Schema + 4 examples PASS）；/tmp/ir001r1_validate.py（4 examples schema+semantic PASS；10 counterexamples rejected）；git diff --check
contract_fixes=accepted/rejected 状态互斥；首族 snapshot_status 仅 reproducibility_partial；主孔/第二孔补齐 wall/hole_len/z_in/z_out/radial_offset/axial 和结构化 placement；限制自由字符串和 eval/exec；收紧参数类型、白名单、首族常量；增加反序列化唯一性/拓扑/引用语义检查
known_limits=未实现 CAD-005 编译器和 CAD-006 几何/STEP 验证器；公式参数名/单位传播/容差、几何摘要容差、环形线程近似是否可接受仍待下游冻结；STEP 字节 hash 仍不稳定；source snapshot、外部图纸和生成资产仍 reproducibility_partial/license_scope_uncertain
next=Codex 中枢复核后再交给 CAD-005/006
```

## 本轮修正

1. Draft 2020-12 条件约束现在保证：`status=rejected` 必须有 `errors`、`nodes=[]` 且没有 `validation_result`；`status=accepted` 不得有顶层 `errors`，可以带后置 `validation_result`。几何/STEP 失败保持 accepted 并用 `validation_result.ok=false`。
2. 当前 BenchCAD 首族 Schema 将 `source.snapshot_status` 收紧为 `reproducibility_partial`；`reproducible` 示例被 Schema 拒绝。STEP 字节哈希不稳定、外部图纸/生成资产和许可边界仍保留。
3. 两个 `feature.tapped_hole_cutter` 节点现在使用同一组结构化输入：`wall`、`over`、`hole_len`、`z_in`、`z_out`、`radial_offset`、`axial`、`angle_deg` 和 ISO pitch lookup；placement 元数据明确 +Z→绕 Y 90°→+X、平移、绕 Z 旋转。`screw_len` 未进入孔深。
4. `constraint.expression`、node `properties` 和 placement 被明确限定为展示/登记元数据；执行只能通过参数/输出引用、literal、lookup 和登记 formula，禁止 eval/exec/任意代码。
5. JSON Schema 收紧了六个参数的 ID/type/unit/value、首族 family/source 常量、公式/节点/约束白名单和注册的 placement 结构；数组内部唯一性、ordinal 连续性、依赖拓扑、引用存在性和条件类型匹配由 `semantic-validation.md` 规定稳定错误码。

## 验证边界

使用临时隔离环境 `/tmp/ir001r1-jsonschema-venv` 安装 `jsonschema>=4,<5`，未写入仓库。完整 Draft 2020-12 验证确认现有四个示例通过；临时反例确认 accepted+errors、rejected+validation_result、未登记公式、任意 properties 字符串、`snapshot_status=reproducible` 被 Schema 拒绝。语义脚本额外确认重复参数/节点/输出 ID、ordinal 间隙和未来依赖分别产生稳定语义错误。`python3 -m json.tool` 仅证明 JSON 语法，不能替代上述完整 Schema 验证。
