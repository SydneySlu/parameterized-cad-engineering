# APP-002 A2 独立复核与里程碑 B 定向验收

- 日期：2026-11-12
- 复核人：Codex 中枢
- 代码基线：`main` / `ee0fabe`
- 固定环境：`work/benchcad-output/venv/bin/python`，Python 3.11.18，CadQuery/OCP runtime
- 结论：`pass`（A2 获批批次在其授权范围内通过独立只读复核；里程碑 B 六类验收通过）

## A2 批次独立只读复核

对象为 `app002-a2-smoke-20261112-04`。只查看批次 summary、budget ledger、pipeline/IR/index/compiler manifest/STEP 元数据；未读取 raw 响应正文或 evaluator labels，未运行模型、网络请求或重放批次。

- 授权范围与记录一致：DeepSeek `deepseek-flash`、C0、`A2-24mm`/`A2-80mm`/`A2-ask-bore`、CAD pipeline 开启、最多 9 次 HTTP。
- `batch_summary.json` 为 `complete`，3/3 planned runs 存在；`budget_ledger.json` 记录 3 次请求 / 9 次上限。
- 三条 summary raw retention path 均定位到该批次 `raw/` 下的非空文件，summary 保留 raw SHA-256 字段；未从文件正文独立重算内容哈希。
- `A2-24mm`：answer；规范参数 `bore_d=24`、`second_screw=0`，来源分别为 `user_explicit` 与 `rule_derived`；IR 文件哈希匹配 pipeline index；STEP 148,393 bytes，SHA-256 `50c1c0626326eb828c8c0d0934d1913f0607300505cd96739ef3ad185f2184d6`，与 index 和 compiler manifest 一致。STEP 回读 comparison `pass=true`，实体有效、单 solid。
- `A2-80mm`：answer；规范参数 `bore_d=80`、`second_screw=1`，第二螺钉分支开启；IR 文件哈希匹配 index；STEP 364,404 bytes，SHA-256 `8f48075fc9cb651af165f3092d1375bb59613440c2587efbc4ee5e9400f4e9d9`，与 index 和 compiler manifest 一致。STEP 回读 comparison `pass=true`，实体有效、单 solid。
- `A2-ask-bore`：ask；pipeline run dir 和 STEP 路径均为 `null`，确认未进入 CAD 构造。
- 批次 `...-04` 及历史 `...-01` 至 `...-03` 均未修改、移动、覆盖或重跑。`FORMAL_EVALUATION_ALLOWED=False` 未改变。

## 里程碑 B 六类定向验收

固定环境验证命令及结果：

```text
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_a2_runner -q
Ran 98 tests; OK

PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/integration -p 'test_*.py' -q
Ran 179 tests; OK

PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q
Ran 13 tests; OK

PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/schema -p 'test_*.py' -q
Ran 17 tests; OK
```

另使用仓库现有代码和合成 fixture 在新忽略目录 `work/integration-runs/app002-milestone-b-20261112/` 保存定向链路证据：

1. **普通合法值**：A2 live 批次的 24 mm 输入通过 Schema/IR/CAD/STEP 与回读。
2. **单位换算**：synthetic envelope 输入 `{value: 1.6, unit: cm}`，经过真实本地 CAD pipeline 规范化为 `16 mm`，IR 保留用户原始 `{value: 1.6, unit: cm}`；真实 STEP 137,034 bytes，SHA-256 `a0d17f4cd1ff1c15449b19c36796a7f23244d97525593256e82bcc9991e5e6dd`。这是接口与单位链路证据，不计作真实模型语言样本。
3. **第二螺钉边界**：A2 live 批次 80 mm 目录值生成 `second_screw=1`，STEP 回读比较通过。
4. **缺少关键参数**：A2 live 批次缺 bore 得到 ask，未生成 pipeline 目录或 STEP。
5. **显式目录冲突**：在 synthetic envelope 中明确给出 bore 20 mm 与外径 33 mm；统一 `run_pipeline()` 返回 `status=blocked`、`stage=schema`、`CATALOG_MISMATCH`，无 STEP/index。冲突路径未触发编译器调用。
6. **CAD 构造/导出失败**：CAD compiler 的 13 项测试覆盖注入 build 与 export failure。另在真实统一 pipeline、IR 和本地几何构造/重复性验证链路中，仅注入 STEP export 异常；返回 `status=failed`、`stage=step_export`，summary 记录失败，无 STEP、无 index、无旧运行文件泄漏。

本次没有新增或修改测试代码；现有专项回归已经覆盖的路径采用原测试结果，确实缺少的端到端证据通过隔离脚本运行并保存于被 Git 忽略的输出目录，避免重复堆积测试。

## 边界与后续

- 里程碑 B 的链路行为验收已完成，但 live 语言证据仍只来自获批三条输入，其中两条构造成功、一条 ask；不能据此声称广泛语言覆盖、长期稳定或可制造性。
- 不自动扩大 live 样本。是否扩样待项目负责人结合明确语言风险假设决定；任何新模型请求必须使用新 scope、输入、预算、唯一 batch ID 和单独授权。
- 下一阶段为里程碑 C：最小可用演示。历史 A2 批次保持只读。

## handoff_successor_check

```text
predecessor=APP-002-INTEGRATION-A2-SCOPE checkpoint live result for app002-a2-smoke-20261112-04; baseline ee0fabe
files_format=batch_summary/budget_ledger/pipeline index/compiler manifest/STEP paths readable; frozen fixture and test interfaces intact
core_rerun=A2 98/98; Integration 179/179; CAD compilation 13/13; Schema 17/17 under Python 3.11.18 CAD venv
normal_case=A2 24 mm and 80 mm live results; synthetic 1.6 cm through real local CAD/STEP
failure_case=missing bore ask; explicit catalog conflict blocks before compiler; injected real compiler STEP export failure returns failed with no STEP/index
interface=A2 authorization/profile/input/model/condition/budget unchanged; Milestone B uses offline synthetic envelopes for deterministic cases
limits=no raw body or labels read; no network/model request; live sample size is not a generalization claim; history immutable
result=pass
blocking_issue=none
```
