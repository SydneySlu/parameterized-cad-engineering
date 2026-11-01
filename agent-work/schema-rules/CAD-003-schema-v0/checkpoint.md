# CAD-003 checkpoint

```text
task=CAD-003
status=review
changed=agent-work/schema-rules/CAD-003-schema-v0/README.md; agent-work/schema-rules/CAD-003-schema-v0/checkpoint.md; src/schema/__init__.py; src/schema/set_screw_shaft_collar.py; tests/schema/__init__.py; tests/schema/test_set_screw_shaft_collar.py
verified=python3 -m unittest discover -s tests/schema -p 'test_*.py' -v; python3 -m py_compile src/schema/set_screw_shaft_collar.py
schema_version=set_screw_shaft_collar.v0
known_limits=Schema 只覆盖 set_screw_shaft_collar；不判断 CadQuery/OCP 实体有效性、单实体/拓扑、真实螺纹布尔、STEP 回读、跨族字段、许可证或发布状态
next=IR-001 需要审查字段来源/provenance、规则错误码与 Schema→IR 的只读输入接口；构造前必须消费 validate_parameters(...).ok
```

该 checkpoint 等待 Codex 中枢审查后再决定是否进入 IR-001。
