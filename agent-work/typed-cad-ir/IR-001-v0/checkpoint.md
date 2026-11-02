# IR-001-R3-FIX checkpoint

```text
task=IR-001-R3-FIX
status=review
changed=agent-work/typed-cad-ir/IR-001-v0/ir-v0.schema.json; agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md; agent-work/typed-cad-ir/IR-001-v0/mapping.md; agent-work/typed-cad-ir/IR-001-v0/semantic-validation.md; agent-work/typed-cad-ir/IR-001-v0/examples/legal-catalog-row.json; agent-work/typed-cad-ir/IR-001-v0/examples/legal-second-screw.json; agent-work/typed-cad-ir/IR-001-v0/examples/validation-failure.json; agent-work/typed-cad-ir/IR-001-v0/examples/build-failure.json; agent-work/typed-cad-ir/IR-001-v0/review-r3.md; agent-work/typed-cad-ir/IR-001-v0/checkpoint.md; tests/typed_cad_ir/test_schema_contract.py; tests/typed_cad_ir/test_axis_mapping.py; docs/WORKLOG.md
verified=python3 -m json.tool schema + six example JSON: PASS; /tmp/ir001r1-jsonschema-venv/bin/python /tmp/ir001_r3_fix_semantic.py: Draft202012Validator.check_schema, six schema+semantic examples, five stage-confusion counterexamples PASS; /tmp/ir001r1-jsonschema-venv/bin/python -m unittest tests.typed_cad_ir.test_schema_contract -v: 3 PASS; work/benchcad-output/venv/bin/python -m unittest tests.typed_cad_ir.test_axis_mapping -v: 2 PASS; python3 -m unittest discover -s tests/schema -p 'test_*.py' -v: 17 PASS; work/benchcad-output/venv/bin/python tests/cad_compilation/test_handoff.py: PASS; work/benchcad-output/venv/bin/python /tmp/ir001_r3_transform_probe.py: PASS; python3 CAD test import: blocked (system Python has no CadQuery); rerun in project Python 3.11.18/CadQuery 2.3.0/OCP 7.9.3.0: PASS; JSON syntax checks on schema+six examples: PASS; git diff --cached --check before implementation commit: PASS; allowed staged path audit: PASS
handoff_self_check:
  changed=IR v0 schema/spec/mapping/semantic validation/examples/checkpoint/review, two targeted regression tests, append-only worklog; no production src, CAD-003, DATA-003, or compiler/validator implementation changed
  commands=Draft 2020-12 schema+six examples and five stage-confusion rejects PASS; schema contract tests 3 PASS; fixed source Workplane mapping and bbox tests 2 PASS; CAD-003 tests 17 PASS; CAD handoff and placement probes PASS; final JSON syntax, git diff --check HEAD~2..HEAD, allowed staged path audit, and post-commit status audit: PASS
  confirmed=Workplane XZ local x/y/z maps world +X/+Z/-Y; local axis [0,1,0] maps world +Z; fixed source bbox 32.0000002 x 32.0000002 x 14.0 mm; cutter local +Z rotates around world +Y 90 degrees to +X, translates to (radial_offset,0,width/2), then rotates around world +Z; build failure persists as accepted validation_result stage=build with CAD_BUILD_* code and completed_stages=[]; post_geometry failure remains separate; step_export/readback require preceding successful stages
  unresolved=geometry_tolerance pending_measurement; family_scope awaiting_owner_confirmation; snapshot_status reproducibility_partial; generated asset/license scope uncertain; no CAD-005 compiler or CAD-006 validator; Codex central review pending
  next_agent_focus=independently inspect world/local axis Schema constants and coordinate/bbox evidence; validate build/post_geometry stage branches and completed_stages constraints/counterexamples; verify 0.2.0 compatibility note and limits; do not mark CAD-005/006 done
known_limits=geometry_tolerance:pending_measurement; family_scope:awaiting_owner_confirmation; snapshot_status:reproducibility_partial
next=Codex 中枢独立复审；不得写成 CAD-005/006 done
commit=fac9aaf
```

状态保持 `review`。系统 Python 没有 CadQuery，CAD 专项检查已在项目隔离的 Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0 环境运行。历史 R3 结果见本目录 `review-r3.md`，本任务修正追加段保留前序事实并标注被取代的坐标/结果契约结论。
