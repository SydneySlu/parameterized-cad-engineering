# RET-003 checkpoint：里程碑 1 协议草案

状态：`review`  
任务：RET-003  
日期：2026-11-03  
工作根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`

## 本 checkpoint 完成内容

- 新增 `protocol-draft.md`：问题、假设、角色隔离、C0 无检索、C1 RET-002 参数检索、
  C2 人工模板/规则、指标分母、失败处理、权重边界和里程碑 2 运行门槛。
- 新增 `query-set-draft.json`：3 个 held-out 主查询、2 个接口诊断和 1 个结构化失败
  诊断；只引用现有 manifest `sample_id`/role，不复制参数值或扩写样本。
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

## 未决事项和放行请求

1. Codex 中枢是否接受 C2 使用现有 CAD-003 目录映射和 `second_screw_threshold` 的
   固定规则先验，以及 C0/C2 与 C1 的公平输入契约；若不接受，应标记不可比并暂停。
2. 是否批准仅运行 C1 的检索级诊断，还是等待 APP-001 后再进入任何对照。
3. 是否接受 `{0.0, 0.5, 1.0}` 作为未来敏感性分析的预注册候选集合；当前未运行、未改
   RET-002 配置。
4. split 仍未冻结，结果不得写成正式 benchmark 或统计泛化结论。

## handoff_self_check

```text
task=RET-003 milestone=1
status=review
changed=agent-work/integration/RET-003-retrieval-evaluation/protocol-draft.md,
        query-set-draft.json, checkpoint.md, handoff.md; docs/WORKLOG.md (append-only)
commands=verify_manifest.py --tracked-only (660/660); retrieval unittest (30/30);
         run_smoke.py (3 normal/boundary PASS, 13/13 failure, determinism PASS);
         replay_query.py (catalog-bore-020 canonical sha stable)
confirmed=manifest hash/15 rows/9-3-3; candidate role boundary; normal/heldout/failed
         query behavior; RET-002 policy and weight facts; report timestamp diffs restored
unresolved=APP-001 absent; no endpoint-level comparison; C2 rule prior/fairness awaits
          Codex review; split provisional; no sensitivity run
next_agent_focus=审阅三条件公平性、主查询清单和指标分母；未书面放行前不得运行里程碑 2
```
