# APP-001 v3 决策偏差修正候选 checkpoint

- Task ID：`APP-001-V3-DECISION-FIX-DRAFT`
- 日期：2026-11-07
- 状态：review
- 分支：`codex/APP-001-V3-DECISION-FIX-DRAFT`

## 范围

根据 v3 正式批次中 Ollama 的 A03 两次误拒绝、A08 C1 多问一次及 A07 `anodized` 标签变体，形成未激活的 extraction v4 prompt/spec 候选和离线检查。无模型请求、无密钥读取。

## 产物

- `agent-work/llm/APP-001-baseline-prep/prompt-v4-candidate.md`
- `agent-work/llm/APP-001-baseline-prep/decision-policy-v4-candidate.md`
- `tests/llm/test_decision_policy_v4_candidate.py`
- `docs/DECISIONS.md`：新增 proposed ADR-0017
- `docs/WORKLOG.md`、`docs/PROJECT_STATUS.md`

## 自检与验收

`handoff_self_check`：

```text
changed=<见上列候选和记录文件；生产 v3 文件、contract/parser/adapter/runner 未改>
commands=PYTHONPATH=src:. python3 -m unittest tests.llm.test_decision_policy_v4_candidate -v → 8/8 OK；v3 candidate 55/55 OK；parser 41/41 OK；LLM discover 584 OK (skipped=8)；Schema discover 17/17 OK；py_compile 与 git diff --check OK
confirmed=<v3 批次观测到 A03 2 次 refuse、A08 C1 1 次 ask、A07 unsupported 标签 anodized；候选规则要求单位归一、用户输入优先于检索参考、稳定规范标签>
unresolved=<ADR-0017 proposed；候选文案不证明模型依从；是否激活/重测待项目负责人决定>
next_agent_focus=<审查候选措辞是否仅覆盖三项已观测偏差、是否保持 v3 gate、离线测试不越界为效果结论>
```

## 禁止范围

不更新激活 manifest，不变更生产 `PROMPT_VERSION`，不修改冻结 acceptance-set，不运行任何模型，不改旧批次，不运行 C2/IR/CAD/geometry/STEP。真实模型复测必须另行授权。
