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

## APP-001-V4-CHECKER-FIX checkpoint（2026-11-08）

- 状态：review；ADR-0017 仍保持 proposed，生产继续使用 `app001-extraction.v3`。
- 分支：`codex/APP-001-V3-DECISION-FIX-DRAFT`；HEAD `3665293`（本任务前）。
- 范围：只修复 v4 候选 checker 的两项 P1/P2 问题及对应测试；不改生产 v3、contract/parser/prompt_loader/adapter/runner、冻结 acceptance-set、prompt-v3、ADR-0017 状态、旧批次或正式评测结果。

### P1：retrieval 优先级 checker

- 新增纯函数 `resolve_bore_precedence(user_bore, retrieval_bore_value)`：用户 bore 存在时返回用户值，忽略 retrieval；用户 bore 缺失时返回 `None`，retrieval 不被提升为用户主张。
- `evaluate_fixture()` 现在显式调用该函数：user bore=24 + retrieval=20 → normalized_bore=24，answer 允许；user bore=None + retrieval=20 → normalized_bore=None，answer 不允许，ask 允许。
- retrieval 值仅用于审计追踪（`retrieval_bore_raw`、`retrieval_acknowledged`），不作为 user_input evidence，不填入 extracted user claims。
- 新增 `TestV4RetrievalIsolation`（10 项），包含正向和反向测试：
  - `test_user_bore_24_wins_over_retrieval_20`：用户 24 优先。
  - `test_retrieval_noncatalog_does_not_override_user_catalog`：retrieval=75 不会把用户 24 变成 refuse。
  - `test_user_missing_retrieval_present_no_answer`：用户缺失时 retrieval=20 不允许 answer。
  - `test_retrieval_catalog_value_not_promoted_to_user_claim`：retrieval=24（catalog 值）不被提升为用户主张。
  - `test_resolve_bore_precedence_returns_*`：纯函数级断言。

### P2：unsupported evidence quote 保留

- 新增 `UnsupportedEvidence` dataclass：`canonical_label`、`original_quote`、`source="user_input"`。
- `V4FixtureResult` 新增 `unsupported_evidence` tuple 字段。
- `evaluate_fixture()` 现在为每个 unsupported term 构建 evidence 条目：`阳极氧化` → canonical_label=`anodizing`，quote=`阳极氧化`，source=`user_input`。
- 不凭空增加用户没有提到的 unsupported 项：无 unsupported_terms 时 evidence 为空。
- 新增 `TestV4UnsupportedEvidenceQuote`（7 项）：
  - `test_chinese_anodizing_maps_to_canonical_label`：阳极氧化 → anodizing。
  - `test_original_quote_preserves_chinese_not_canonical`：quote 仍为阳极氧化。
  - `test_evidence_source_is_user_input`：source=user_input。
  - `test_anodized_variant_preserves_original_quote`：anodized → anodizing，quote=anodized。
  - `test_no_fabricated_unsupported_items_when_none_requested`：无 unsupported 时不凭空造。
  - `test_canonical_labels_match_evidence_labels`：labels 与 evidence 一致。
  - `test_multiple_unsupported_items_each_have_evidence`：多项各自有独立 evidence。

### handoff_self_check

```text
changed=src/llm/decision_policy_v4_candidate.py, tests/llm/test_decision_policy_v4_candidate.py, agent-work/llm/APP-001-V3-DECISION-FIX-DRAFT/checkpoint.md, docs/WORKLOG.md
commands=PYTHONPATH=src python3 -m unittest tests.llm.test_decision_policy_v4_candidate -v → 34/34 OK；v3 candidate 55/55 OK；parser 41/41 OK；LLM discover 610 OK (skipped=8)；Schema discover 17/17 OK；py_compile OK；git diff --check CLEAN
confirmed=<checker 未被 adapter/parser/runner 导入；active v3 prompt SHA-256=3dd8bd55… 未变；acceptance-set SHA-256=ed59e2b6… 未变；只改了 v4 候选 checker 和测试>
unresolved=<.git/index.lock 阻塞 commit（FUSE 环境 git status 创建后无法删除）；Python 3.10.12 非 3.11.18 固定基线，用户须在 Mac 复核；离线测试不证明模型依从>
next_agent_focus=<Codex 中枢独立复审 P1/P2 checker 修正；验证 resolve_bore_precedence 和 UnsupportedEvidence 纯函数行为；确认生产隔离不变>
```

### 禁止范围

不更新激活 manifest，不变更生产 `PROMPT_VERSION`，不修改冻结 acceptance-set，不运行任何模型，不改旧批次，不运行 C2/IR/CAD/geometry/STEP，不调整 provider/预算/授权/重试。真实模型复测必须另行授权。

## Codex 主机复核与锁处理 checkpoint（2026-11-08）

- 锁处理：确认 `.git/index.lock` 为 0 字节且未发现运行中的 Git 进程；根据项目负责人明确授权删除。删除后 Git 状态可读，工作区改动仍完整。
- 固定环境：本机 `/opt/homebrew/bin/python3.11` 为 Python 3.11.18；v4 34/34、v3 candidate 55/55、parser 41/41、LLM 610 passed/8 skipped、Schema 17/17、py_compile 和 diff-check 全部通过。
- 结论：P1/P2 checker 工作区复核通过；单一任务交付尚待提交。生产 v3 与 acceptance-set hash 保持原值。ADR-0017 仍 proposed，模型效果仍未验证。
- 流程沉淀：新增 `docs/coordination/project-memory-and-delivery-playbook.md`，覆盖启动事实恢复、角色分工、架构/计划防漂移、验证证据、交接复核、压缩恢复、Git 锁及完成状态门；`AGENTS.md` 已增加入口链接。
- 提交：`6d1f90a`（checker 修正、独立复核记录及项目工作手册）；当前工作区干净，尚未 push。
- 下一步：由项目负责人 push 当前候选分支后，Codex 对远端提交对象做最终核对；再决定是否进入 v4 激活实现，不能跳过后续激活包审查与独立模型授权。
