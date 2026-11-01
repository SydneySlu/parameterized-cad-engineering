# CAD-005/006-R2 续任 Agent 定向复核

日期：2026-11-02
前序：`CAD-005/006-R1`，参考提交 `e3f88f7`
结果：`review`

```text
handoff_successor_check:
  predecessor=CAD-005/006-R1, commit=e3f88f7
  files_format=R1 checkpoint、handoff_successor_check、IR-001 v0 schema/spec/examples 和 CAD-003 checkpoint 均存在；5 个 IR 示例均为合法 JSON；历史 /mnt/outputs/test_handoff.py 不存在
  core_rerun=Draft 2020-12 validator（/tmp/cad005006-r2-jsonschema-venv，Draft202012Validator.check_schema + 5 examples）PASS；tests/schema 17 passed；work/benchcad-output/venv/bin/python work/benchcad-output/smoke_set_screw.py exit 0；仓库 test_handoff 在项目 venv 下 PASS
  normal_case=bore_d=20, second_screw=0：spec.check()=[]，build 1 solid；bore_d=80, second_screw=1：smoke build 1 solid
  failure_case=bore_d=20, second_screw=1：spec.check() 拒绝；outer_d=19, bore_d=20：壁厚规则拒绝，绕过规则时实际 build/STEP 回读为 3 solids
  interface=IR-001/CAD-003 输入输出边界与前序记录一致；本轮只保留可导入 cad_compilation 包边界和复核脚本，未启动编译器/验证器
  limits=保留 STEP 字节 hash 不稳定、reproducibility_partial、螺纹环形近似、多实体风险；实际环境为 Python 3.11.18/CadQuery 2.3.0/OCP 7.9.3.0/NumPy 1.26.4，未验证 Python 3.10
  result=review
  blocking_issue=无硬阻塞；但前序记录把未提交的外部脚本写成已保存且把 Python 3.10 写成已验证事实，需要 R2 纠正后再交中枢审查
```

## 复核说明

- `work/benchcad-source/api-snapshot-035f467/` 是仓库已有的固定 commit 快照目录；脚本只读取 `part.py`/`spec.py`，不复制、修改或提交 BenchCAD 源码。
- `python3 tests/cad_compilation/test_handoff.py` 在系统 Python 3.9.6 中因缺少 CadQuery 输出 `status=blocked`；使用项目隔离环境运行同一脚本通过。该环境差异必须保留在交接记录中。
- 兼容性 shim 是脚本中的显式 `OCP.TopoDS.HashCode` 回退，不依赖 Agent 私有目录修改。
