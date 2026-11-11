# v5 集成基线核验与 final offline preflight

日期：2026-11-11。中枢：Codex。任务：APP-002-INTEGRATION-A1 准备 / APP-001-NEXT-REAL-MODEL-EVALUATION 离线关口收束。

## 结论与证据边界

final offline preflight **pass**；现有单族后端可复用，v5 作为首个整链集成基线（ADR-0020）。这不是新真实模型运行或自然语言到 STEP 的整链通过声明。12-run held-out 真实执行 deferred，不再作为 CAD 集成前置门。A1 尚未实现，当前主要缺口是严格构造门、正式参数→IR adapter、隔离统一入口和证据串联。

本轮开始 `main=993a5b1`，工作区干净，领先缓存 `origin/main` 12 个提交。未 fetch/push/merge。以下命令在该代码基线执行；本轮仅修改规划、审查、交接文档，不改生产代码。

## 1. Held-out final offline preflight（实际执行）

```bash
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 scripts/run_app001_heldout_v5.py --offline-preflight --batch-id review-only-final-offline-993a5b1 --json
```

Python 3.11.18，exit 0，status=pass；12 组合，retrieval_index_provided=true，冻结索引验证通过，batch_dir_exists=false，留存策略为 `work/app001-runs/<batch_id>/raw/`。

| 对象 | SHA-256 / 值 |
|---|---|
| model-inputs.json | c00ef6dce6b227368b3bfb63a91bbf7362316f64796834a045c5fea536dc83a6 |
| evaluator-labels.json | bfe94d89d2809634b9e52cb73c9f4733fee30a7b7130a65ef9e13c33545cc35a |
| RET-001 manifest | b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297 |
| plan hash | 82e83307906f2a1fba0e349c5eee5df529035f97e21fc6d600cb20205b143e18 |
| profile / sample set | app001-heldout-v5-retrieval.v1 / app001-heldout-v5-v1 |
| active versions | app001-extraction.v5 / app001-io.v1 |
| simultaneous caps | chat 36；identity 20；DeepSeek HTTP 18；Ollama HTTP 26；global HTTP 44 |
| budget feasibility | true，global_total=44，ollama_total=26 |

占位 ID `review-only-final-offline-993a5b1` 不作为正式批次分配，无批次目录创建、无真实模型/live preflight/HTTP 请求、无密钥或 .env 读取。未来恢复研究必须重验当时基线并单独批准具体 batch；本次离线 pass 不永久授权后续代码。

## 2. 本轮固定环境复验（实际执行）

CAD 环境：`work/benchcad-output/venv/bin/python`，Python 3.11.18，Darwin arm64，CadQuery 2.3.0，cadquery-ocp 7.9.3.0，NumPy 1.26.4，jsonschema 4.26.0。cadquery/OCP import 成功。

```bash
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q
# Ran 13 tests; OK（8.194s）
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.schema.test_set_screw_shaft_collar tests.typed_cad_ir.test_schema_contract tests.typed_cad_ir.test_axis_mapping -q
# Ran 22 tests; OK（Schema 17 + IR 5）
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_v5_activation tests.llm.test_decision_policy_v5_candidate tests.llm.test_prompt_v5_candidate -q
# Ran 161 tests; OK
```

13 项 CAD 测试包含正常/第二孔真实本地构造、STEP 导出回读和故障注入；输出在测试临时目录。它们验证模块，不是模型整链。本轮未重复完整 15 行构造；沿用 RET-001 已审查的目录覆盖证据。也未重复运行刚完成的全量 LLM 941 项；那是 R2 验收历史证据，详见原审查记录。

另实际执行 7 个合成 envelope 接口探针：使用 `parse_response(json.dumps(envelope))`→`project_to_cad003`→`validate_parameters`，并按 answer/无 missing/无 unsupported/校验通过计算构造资格（探针未生成 IR 或调用 CAD）。

| 合成输入 | 实际结果 |
|---|---|
| answer，bore_d=24 | parse/Schema 通过，可构造；规范参数 24/40/8/12/16/second_screw=0 |
| answer，bore_d={value:1.6,unit:cm} | 规范 bore_d=16，可构造 |
| answer，bore_d=70 | second_screw=0，可构造 |
| answer，bore_d=80 | second_screw=1，可构造 |
| ask，bore_d 缺失、missing_fields=[bore_d] | Schema 拒绝，不构造 |
| refuse，bore_d=20、outer_d=40 | 目录冲突，Schema 拒绝，不构造 |
| refuse，bore_d=24、unsupported=[anodizing] | Schema 可通过但构造资格=false |

7/7 断言通过，全部使用合成证据字符串，只验证结构和规则接口，不证明主张符合任意原始语言语义，也不证明模型遵守策略。

## 3. 资产、接口与实际缺口

| 阶段 | 已核实资产/接口 | A1 需要补的连接 |
|---|---|---|
| 抽取契约 | `src/llm/parser.py::parse_response(str/bytes)` → ParseResult/九键 ParsedEnvelope | 接收标明 synthetic 的注入式结果；将原需求与 envelope 分别留存；不发网络请求 |
| 显式投影 | `src/llm/projector.py::project_to_cad003` → 原抽取+正式 Schema envelope | 不补模型未明确提供值；记录投影和错误 |
| 规则与单位 | `src/schema/set_screw_shaft_collar.py::validate_parameters` → ValidationResult(normalized/provenance/errors) | 以真实原始 payload 再校验，不信任外部伪造 ok 或规范结果 |
| 构造门 | 现有 `src/llm/adapter.py` 仅检查 answer/unsupported/Schema，并主动阻断 IR | 新组合层显式要求 parse成功、answer、missing_fields空、unsupported空、projection/Schema成功；旧标记不能替代安全门 |
| Schema→IR | `agent-work/typed-cad-ir/IR-001-v0/mapping.md` 已冻结；RET-001 generator 有目录批量辅助 | 缺 src 正式 adapter；按 mapping 复用七节点 canonical 图及来源，保留原单位 input，不能直接搬只保留 normalized 的批量 helper |
| IR/CAD/STEP | `cad_compilation.compile_ir(raw, output_dir=...)` → CompilationResult | 每 run 显式独占目录，阶段状态/错误+hash 关联；必须 step_readback 成功才发布本次 STEP |
| 证据/交互 | 编译器已有 manifest、input_ir_sha256、geometry、step hash/readback 比较 | 缺需求→抽取→Schema→IR→manifest→STEP 统一索引；最小 UI 后置 |

IR 实现在 `src/cad_compilation/ir.py`，不是不存在的 `src/typed_cad_ir/`。正式 source commit 固定 `035f467142888edfd0bd7cd73906f9b155c8f43c`；snapshot `reproducibility_partial`；comparison policy `CAD-006.geometry-comparison.v1`。`screw_len` 不是孔深，second_screw 必须 iff bore_d>70，75 不是合法目录边界。

## 4. 历史证据核对与冻结判断

- `agent-work/reviews/APP-001-V5-FORMAL-EFFECT-EVALUATION-codex-review.md`：v5 已有 36 逻辑记录、32 真实响应、4 C1 前阻塞、48 物理尝试；决策 answer20/ask2/refuse10，Schema20/32。缺参、冲突、越界/规则拒绝的 Schema 失败不应被算作应成功构造的案例。无 IR/CAD/STEP 真模型整链证据。本轮只读报告，不读 raw 正文。
- `agent-work/reviews/RET-001-codex-review.md`：15 个目录行已有构造与验证记录（825 checks；tracked-only 660 checks），不能称为语言样本覆盖。本轮不改 manifest、不重建历史产物。
- `agent-work/reviews/IR-001-R3-codex-review.md` 和 CAD-005/006 审查的后续修复记录说明单族基座可用；开头的历史 review 不能被当作当前从零开始。
- v5 prompt SHA `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9`；acceptance SHA `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`。本轮不改锚点；161 项测试包含激活/hash 校验。

冻结判断：代表性合法、缺参/冲突/不支持已有证据；输出契约、单位与来源接口清晰，可以开始集成。构造门是否正确落实于整链仍须 A1 交付，不提前宣称完成。错误几何/丢关键参数/错误放行/假成功阻断；措辞、语言扩展、新对照和小波动进后续清单。

## 5. 交接

```text
handoff_self_check:
  changed=ADR-0020、当前计划/状态、资产与preflight报告、A1工作prompt/checkpoint、分工同步；无生产代码修改
  commands=本报告列出的离线preflight、13 CAD、22 Schema/IR、161 v5及7合成探针均实际通过
  confirmed=单族后端已有实现及固定环境能力；heldout离线门通过；主要缺语言→IR正式连接与隔离入口
  unresolved=A1尚未实现；真实模型整链not_run；语言泛化/稳定性/跨族不在当前证据范围
  next_agent_focus=严格gate、原始单位/provenance、canonical IR、STEP最终成功语义、run隔离与故障路径
```

CC 负责 A1 实现，中枢独立复核；具体任务见 `docs/coordination/prompts/APP-002-INTEGRATION-A1-cc.md`。完成 A1 后准备真实模型整链的新 scope/授权，不用 held-out 研究替代集成验收。
