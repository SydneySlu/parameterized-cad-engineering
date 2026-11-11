# CC 工作 prompt：APP-002-INTEGRATION-A1

请把本文件作为完整任务指令执行。负责人：**CC（Schema/CAD 集成实现）**；独立验收：当前 Codex 中枢。建议交给已有 CAD/Schema 上下文的 CC 对话框；若交给原 held-out runner CC，也必须先恢复下面的后端交接事实，不沿用“继续模型实验”的任务目标。

## 目标和当前授权

项目负责人已确认 ADR-0020：优先完成单族自然语言到 STEP 最小闭环，v5 作为集成基线；12-run 检索对照独立 deferred。**本工作单元 A1 实现“需求文本+合成 v5 envelope→真实本地 CAD/STEP”**，补正式 Schema→IR adapter、严格构造门、统一离线入口和运行证据。

这是连接层实现，不是新 prompt 实验，不重写后端。你可以执行合成夹具与真实本地 CadQuery/STEP 测试；本次不授权真实模型/HTTP、live preflight、密钥/.env/历史 raw 正文读取。真实模型接线与运行属于 A2，后续单独明确输入/预算/batch/授权；本次不能永久停在离线层，但也不能越过授权直接发请求。

## 0. 启动与交接（先完成，再编码）

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git rev-parse --show-toplevel
git status --short --branch
git log -5 --oneline
```

读取 AGENTS.md、PROJECT_STATUS/PROJECT_PLAN/DECISIONS/WORKLOG、handoff-review-protocol、project-memory-and-delivery-playbook，以及：

- `agent-work/reviews/APP-001-V5-INTEGRATION-BASELINE-preflight.md`
- `agent-work/integration/APP-002-INTEGRATION-A1/checkpoint.md`
- `agent-work/typed-cad-ir/IR-001-v0/` 的 mapping/spec/schema/semantic-validation/checkpoint 与合法/失败示例；IR R3 后续修复审查
- `agent-work/schema-rules/CAD-003-schema-v0/checkpoint.md` 与真实 Schema 源码
- CAD-005/006 的最终 canonical-binding R2 checkpoint 与中枢审查后续 pass
- `src/llm/parser.py`、`projector.py`、`adapter.py`；`src/schema/set_screw_shaft_collar.py`；`src/cad_compilation/{__init__,compiler,ir}.py`
- RET-001 generator 中 `build_accepted_ir` 仅作参考，及 RET-001 中枢审查

不要按旧聊天猜当前提交。中枢核验代码基线为 `993a5b1`，其后的 ADR/任务文档是本次执行依据；记录你实际起点 HEAD。工作区有他人未提交改动时不要覆盖、reset、stash。干净时从当前已核实 main 建 `cc/APP-002-INTEGRATION-A1`，本轮不 push/merge。

Schema→IR→CAD 属高风险：在 checkpoint 填 `handoff_successor_check`，重跑至少一条核心命令，检查正常和拒绝案例。可跑下方现有 CAD 13 项，已有正常与故障注入；明确固定环境与限制。核验无冲突后把任务 planned 改 in_progress，不把旧 review 开头误认成模块未完成。

## 1. 最小实现与建议文件

建议新增以下文件，名称可作小幅合理调整并在交接中说明：

- `src/integration/__init__.py`
- `src/integration/schema_to_ir.py`：确定性正式映射
- `src/integration/pipeline.py`：纯本地组合与运行隔离
- `scripts/run_cad_pipeline.py`：离线统一 CLI
- `tests/integration/test_schema_to_ir.py`、`test_pipeline.py`，必要的少量 synthetic JSON 夹具
- 对应 README/用法、checkpoint、PROJECT_STATUS/PLAN、追加 WORKLOG

不要导入 agent-work 的临时 generator 作为生产实现。可以将审查过的固定 canonical 图/模板固化为 src 内数据或使用已有冻结规范资源，并注明来源、版本与一致性检查；不要把整个生成脚本搬来。不可改节点语义、Schema、IR schema、比较阈值或编译引擎迁就新 adapter。

### 1A. 输入与严格构造门

提供库入口，至少接受原始需求文本、raw envelope（str/bytes）、输出根；注入接口便于 A2 以后接真实提取。A1 的 extraction_source 必须明确为 `synthetic_fixture`，不能让输出报告称为真实模型请求或真实自然语言整链。需求文本是追溯信息，本轮不新增正则抽取器假装模型。

按真实调用顺序复用 `parse_response`→`project_to_cad003`→`validate_parameters`，保持原 envelope、显式参数和原单位。构造必须同时满足：

1. 当前 v5 严格解析通过；
2. `decision == answer`；
3. `missing_fields == []`；
4. `unsupported_requests == []`；
5. projection 和真实 Schema 校验通过。

ask/refuse 返回其 decision/questions/原因；解析、Schema/IR 拒绝返回 stage/code/fields。任何未通过都不生成可执行 IR、不调用编译器、不返回 STEP。不要仅依赖旧 adapter.construction_ready（它不检查 missing_fields），不要打开旧 runner 内 IR/CAD 的禁用标记，也不要修改生产 adapter 的历史评测语义。

### 1B. 正式 Schema→IR adapter

优先接受原始正式 Schema payload，内部重新执行规则；若接受 ValidationResult，也必须用对应原始 payload 重验并核对，不能相信外部构造的 ok=true。只有真通过生成 accepted IR，然后通过 `cad_compilation.validate_ir`。

必须遵守 mapping.md：

- 六参数固定顺序 bore_d/outer_d/screw_d/screw_len/second_screw/width，规范长度为 mm。
- 原始显式 `{value,unit}` 原样保存在 parameter.input；例如 1.6 cm→value=16 mm，但 input 仍1.6/cm。裸长度数字 input.unit=mm。
- user_explicit/catalog_derived/rule_derived 与 source_ref 正确；派生值不能伪造 user input；用户显式派生字段即使碰巧符合目录，也保持 user_explicit。
- 固定 source commit `035f467142888edfd0bd7cd73906f9b155c8f43c`、snapshot `reproducibility_partial`、IR v0.2.0 和比较策略 `CAD-006.geometry-comparison.v1`；记录实际 adapter_version。
- 七节点、canonical 公式、placement、约束均依现有规范；screw_len 不是孔深；不对模型内容/表达式 eval/exec。
- second_screw iff bore_d>70；70→0，80→1。75 是非目录值，不能用作边界成功样例。

### 1C. 编译、最终成功与输出隔离

复用 `compile_ir(serialized_ir, output_dir=本次独占目录)`，不重写编译器。每运行 UUID/等价唯一 ID，工作目录在被忽略的 `work/integration-runs/<run_id>/`，原子独占创建；拒绝已存在 run、逃逸或误用旧目录，不覆盖产物。对路径/符号链接按实际风险检查 canonical containment，不做无关权限平台。

最少保存输入/fixture标签、raw envelope、Schema payload/result（含 provenance）、输入 IR、编译返回 IR/manifest/验证、汇总索引；索引把 input/envelope/IR/STEP 的实际 hash 与当前 run 关联，区分输入 IR 和追加 validation_result 的结果 IR。

成功要求至少：compiler.ok=true、status=step_readback、验证及比较真实通过、当前 run 内 STEP 存在且非空，hash 与本次 manifest 一致。不能把 accepted IR/build/文件存在单项当成功。CAD、export、readback 或证据写入失败一律不发布 success；保存可定位失败，STEP 对用户的发布路径为空。失败目录残留仅作本次诊断，不搜寻/返回其他 run 的旧 STEP。重新生成必须新 run。

统一结果最少有 run_id、extraction_source、status（success/ask/refuse/blocked/failed 或等价明确枚举）、stage、errors/questions、参数/IR/验证索引和可选 STEP path；只有 success 暴露本次可获取 STEP。CLI 对错误采用非零退出码并输出结构化原因；ask/refuse 的退出约定写清楚。缺 CAD runtime 要清楚失败，不能 mock 成功。

CLI 示例目标（具体参数名可合理调整）：

```bash
PYTHONPATH=src:. work/benchcad-output/venv/bin/python scripts/run_cad_pipeline.py --request "请按 GN 705 做一个轴环，孔径 24 mm" --synthetic-envelope tests/integration/fixtures/answer-bore24.json --output-root work/integration-runs --json
```

要求README用同一真实命令可复现，明确 envelope 是 synthetic。不要把 arbitrary 文件当获准读取的历史 raw；测试只用新夹具，不读旧批次。

## 2. 验收：复用模块测试，补连接层真缺口

至少覆盖以下可判别路径，不以测试数量替代证据：

- 普通合法 bore24/20：合成 envelope 经真实 parser→Schema→正式adapter→真实编译→STEP回读，成功且索引hash正确。
- 1.6 cm：IR value16/mm，input1.6/cm、user_explicit正确，输出几何与16目录一致。
- 第二螺钉70/80：明确分支及几何验证，复用已有后端边界验证，避免只断言参数值而不确认连到正确IR。
- 缺bore、ask/refuse、missing_fields非空、unsupported非空、显式目录/second_screw冲突、解析错版本：断言 compiler 零调用、无可执行IR/STEP发布。至少有一个“Schema可通过但非answer或仍missing”的反向用例，防仅信Schema放行。
- CAD构造/导出失败：注入在真实组合调用处，断言 failed stage/code和空发布路径；保留至少一条真实本地成功测试，不能全mock。
- run隔离：先成功后失败不能返回前一STEP；相同需求两次不覆盖；已有run目录拒绝，非法路径不逃逸。
- 外部伪造ValidationResult.ok、字段/provenance不一致、损坏IR：不允许绕过规则。尽量测试真实公开入口，少写实现镜像断言。

建议运行：

```bash
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/integration -p 'test_*.py' -q
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.schema.test_set_screw_shaft_collar tests.typed_cad_ir.test_schema_contract tests.typed_cad_ir.test_axis_mapping -q
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -p 'test_*.py' -q
git diff --check
```

新Python文件py_compile，用JSON schema/语义检查验证生成IR。复用15行目录的Schema/映射参数化回归，不因已有15行证据强制重复全部昂贵几何构造；若修改后端边界确需重跑，先说明原因。固定CAD环境必须真实复验，VM仅Python通过不等于STEP可用；VM无环境可提交可审查实现并明确not_run，交中枢在Mac补验，不伪报。

## 3. 里程碑与交付

1. M1：交接复核、构造门与正式IR映射，记录正常/拒绝和单位来源。
2. M2：统一入口、隔离/证据、真实本地STEP成功及失败路径。
3. M3：实际验证、用法与handoff；状态review，不擅自done/push/merge。

每个可审查里程碑追加 WORKLOG，提供 commit/hash，不无关重构。任务状态写回 PROJECT_STATUS/PLAN，checkpoint含 handoff_self_check、handoff_successor_check、实际命令/解释器/结果、产物路径（ignored，不提交STEP）、未运行项和中枢关注点。

最终报告说明：当前分支/起点与HEAD、文件范围、至少一个成功STEP与一个阻断/故障、参数/IR/验证/STEP对应、哪些是fixture哪些是真实CAD；真实模型整链仍not_run。A1验收后由中枢立即准备A2受控真实模型整链，不回到无尽prompt/检索实验。

## 禁止项

不修改冻结v5 prompt/loader/parser策略、Schema或IR语义、编译器几何规则、provider/模型/重试/预算/旧授权；不发网络请求、不读密钥或.env/历史raw正文、不改旧批次、不生成任意Python执行、不开展v6/C2/新族/大界面重构。发现确实需要接口/策略变更时记录具体阻断与最小方案，交中枢按ADR处理，不能静默扩大范围。
