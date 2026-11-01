# CAD-003 checkpoint

```text
task=CAD-003-R1
status=review
changed=agent-work/schema-rules/CAD-003-schema-v0/README.md; agent-work/schema-rules/CAD-003-schema-v0/schema-v0.json; agent-work/schema-rules/CAD-003-schema-v0/checkpoint.md; src/schema/set_screw_shaft_collar.py; tests/schema/test_set_screw_shaft_collar.py
verified=python3 -m unittest discover -s tests/schema -p 'test_*.py' -v（17 passed）; python3 -m py_compile src/schema/set_screw_shaft_collar.py; python3 -m json.tool agent-work/schema-rules/CAD-003-schema-v0/schema-v0.json >/dev/null; git diff --check
schema_version=set_screw_shaft_collar.v0
canonical_input=正式 envelope：{schema_version, family_id, parameters{六个参数；bore_d 必填}}；长度参数为裸数字或 {value, unit}，second_screw 为无量纲整数 0/1
compatibility=Python validate_parameters/validate_json 继续接受扁平参数对象和省略 envelope metadata 的过渡输入；normalized_json_schema 明确标注为内部兼容描述
cross_field_rules=目录行耦合、second_screw 阈值、outer_d > bore_d、壁厚 0.65*screw_d 和 width 1.45*screw_d 仍由 Python 规则负责，JSON Schema 不声称覆盖
known_limits=未执行第三方 JSON Schema validator（仓库无 jsonschema 依赖）；仍不判断 CadQuery/OCP 实体有效性、单实体/拓扑、真实螺纹布尔、STEP 回读、跨族字段、许可证或发布状态
next=Codex 审查后决定是否启动 IR-001
```

该 checkpoint 等待 Codex 中枢审查后再决定是否进入 IR-001；不将 CAD-003 标记为 done。
