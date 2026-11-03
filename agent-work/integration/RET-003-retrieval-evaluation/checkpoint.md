# RET-003 checkpoint：里程碑 1 协议草案

状态：`review`  
任务：RET-003  
日期：2026-11-03  
工作根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`

## 本 checkpoint 完成内容

- 修订 `protocol-draft.md` 为 `RET-003.protocol.v0.1-draft`：将原 C2 降级为
  `C2O=catalog_rule_oracle_v0`，明确完整 `CATALOG_ROWS` 可间接包含 held-out 真值，
  不再把它当公平人工模板；补充共同输入 payload、条件额外上下文和公平性边界。
- 新增 `query-set-draft.json`：3 个 held-out 主查询、2 个接口诊断和 1 个结构化失败
  诊断；只引用现有 manifest `sample_id`/role，不复制参数值或扩写样本。
- 保持 `query-set-draft.json` 不变：3 个 held-out 主查询、2 个接口诊断和 1 个结构化失败
  诊断仍只引用现有 manifest `sample_id`/role，不复制参数值或扩写样本。
- 追加 `docs/WORKLOG.md` 认领记录；未修改 `src/**`、`tests/**`、RET-001/RET-002
  冻结产物、正式状态看板或决策记录。
- 未创建评测脚本、正式配置、结果或收益报告；没有运行未经批准的三条件正式对照。

## 启动与交接定向复核

启动命令确认 Git 根目录为要求的共享基座；开始时工作树只有既有提交，当前变更仅为本
任务的文档和 WORKLOG。已阅读 AGENTS、项目状态/计划/任务/决策、交接协议、RET-001/002
审查与交接文件，以及 RET-002 配置和检索测试入口。

实际复核命令与结果：

```text
PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
work/benchcad-output/venv/bin/python \
agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py --tracked-only
=> records=15, checks_passed=660, failures=0, manifest_sha256=b7b6c737..., RESULT: PASS

PYTHONPATH=src work/benchcad-output/venv/bin/python \
-m unittest discover -s tests/retrieval -v
=> Ran 30 tests, OK

PYTHONPATH=src work/benchcad-output/venv/bin/python \
agent-work/integration/RET-002-retrieval-baseline/run_smoke.py
=> 3 cases PASS; failure cases 13/13; determinism in/cross process PASS;
   canonical sha256=0fcf84b7..., RESULT: PASS

PYTHONPATH=src work/benchcad-output/venv/bin/python \
agent-work/integration/RET-002-retrieval-baseline/replay_query.py \
--config agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json \
--case agent-work/integration/RET-002-retrieval-baseline/examples/query-in-catalog.json
=> query_status=catalog_validated; top1=catalog-bore-020; results=3;
   sha256=0fcf84b7...
```

抽查结果：

- 正常 `bore_d=20` envelope：`catalog_validated`，top-1 为
  `set_screw_shaft_collar/catalog-bore-020`，total distance 为 0，候选数量 3。
- held-out `bore_d=80` flat：`catalog_validated`，top-1 为 `catalog-bore-050`，
  total distance `0.7844444444444445`；3 行候选角色全部为 `retrieval_source`，
  `catalog-bore-080` 不在结果中。
- 结构化失败：缺少 `outer_d` 等五个 flat 字段返回
  `RETRIEVAL_MISSING_FIELD`（stage `query`），没有静默补全或产生结果。

复核脚本会改写带时间戳的 RET-001 verification 和 RET-002 smoke 报告；本次结束前已用
`git checkout --` 恢复它们，避免把复跑噪声提交。未读取 STEP、渲染图、IR 文件或第三方
图纸，未下载 BenchCAD Public/Core。

## 已确认事实

- 当前唯一族为 `set_screw_shaft_collar`；manifest 15 行、角色 9/3/3、
  `split_status=provisional_small_n`。
- RET-002 固定 policy 为 `RET-002.parametric_distance.v1`，连续字段等权 0.2，
  `second_screw` 权重 0.5，候选仅 `retrieval_source` 3 行。
- held-out 行可作为查询真值，但不能作为候选、范围拟合、权重选择或 Prompt 示例。
- 当前可复跑的证据只有检索级排序/距离/泄漏/确定性和结构化失败；没有 APP-001 固定
  模型、Prompt、自然语言输入集或统一下游求解器，所以端到端字段/Schema/CAD/STEP
  收益全部是 `not_measured`。
- 完整 `CATALOG_ROWS` 包含 held-out 对应的 `bore_d=12/35/80`，所以原 C2 能间接
  读取评测真值；修订后它只作为 C2O oracle/上界诊断。当前没有公平 C2，RET-003 仅保留
  C1 检索级诊断，公平 C0/C1 端到端比较待 APP-001 和中枢放行。

## 未决事项和放行请求

1. Codex 中枢是否接受 C2O `catalog_rule_oracle_v0` 的降级身份，以及未来公平 C2 暂
   为空缺；C2O 不得进入公平主表、调权重或 Prompt 示例。
2. 是否批准仅运行 C1 的检索级诊断，还是等待 APP-001 后再进入公平 C0/C1 对照。
3. 是否接受 `{0.0, 0.5, 1.0}` 作为未来敏感性分析的预注册候选集合；当前未运行、未改
   RET-002 配置。
4. split 仍未冻结，结果不得写成正式 benchmark 或统计泛化结论。

## handoff_self_check

```text
task=RET-003 milestone=1
status=review
changed=protocol-draft.md (v0.1 C2O downgrade + common input contract), checkpoint.md,
        handoff.md; query-set-draft.json unchanged; docs/WORKLOG.md (append-only)
commands=PYTHONPATH=src work/benchcad-output/venv/bin/python -m unittest discover -s tests/retrieval
         (30/30); python3 -m json.tool query-set-draft.json; git diff --check
confirmed=manifest hash/15 rows/9-3-3; candidate role boundary; normal/heldout/failed
         query behavior; RET-002 policy and weight facts; query set unchanged; no timestamp
         report noise from the test rerun
unresolved=APP-001 absent; no endpoint-level comparison; no fair C2 defined; C2O oracle identity
          awaits Codex review; split provisional; no sensitivity run
next_agent_focus=复核 C2O 身份、共同输入 payload、信息边界和公平主表排除规则；未书面放行前
                  不得运行里程碑 2
```
