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

## 离线补强 checkpoint（2026-11-08）

- 状态：review；ADR-0017 仍保持 proposed，生产继续使用 `app001-extraction.v3`。
- 变更：新增未激活的 `src/llm/decision_policy_v4_candidate.py` 纯函数 checker；补充 v4 测试；明确 `75 mm` 虽在 5–80 mm 数值边界内但不是 15 个离散 selector，必须 `refuse`。
- checker 覆盖：`1.6 cm -> 16 mm` 且保留 evidence quote；用户 `bore_d=24` 优先于不可信 retrieval `20`；unsupported alias 统一为 `anodizing`；缺失/目录冲突/规则冲突不得 `answer`。
- handoff_successor_check：
  - predecessor=`d8961ac` + Codex review `479561a`
  - files_format=`prompt-v4-candidate.md`、策略稿、checker 和测试可读；checker 未被生产 adapter/parser/runner 导入
  - core_rerun=`tests.llm.test_decision_policy_v4_candidate` 18/18 OK
  - normal_case=`1.6 cm` 归一为 16 并允许 answer；`bore_d=24` 在 retrieval=20 时仍允许 answer
  - failure_case=`75 mm` 返回 refuse；缺失 bore_d、目录冲突和规则冲突均不允许 answer
  - interface=`app001-io.v1`、v3 生产版本、acceptance-set 和旧批次未改
  - limits=`LLM discover` 594/8 skip、Schema 17/17、v3 candidate 55/55、parser 41/41、py_compile 和 diff check 通过；未调用真实模型
  - result=pass_with_review_gate
- 下一步：对 checker 和文案做 Codex 中枢独立审查；通过后再决定是否建立 v4 activation 实现任务。任何真实模型批次仍需新 ID 和单独授权。
