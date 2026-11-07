# APP-001-V3-ACTIVATION checkpoint

- 日期：2026-11-07
- Agent：Codex
- 状态：done（激活与历史 v2 审计兼容已合入 `main`）
- 合入提交：`7dc7a37`
- 前置：项目负责人接受 ADR-0016；本次仅激活生产协议并做离线验证，不含真实模型评测授权。

## 交付与版本身份

- 生产 `PROMPT_VERSION`、解析期望版本和冻结 prompt loader 已切到 `app001-extraction.v3`。
- 生产 prompt：`agent-work/llm/APP-001-v3-activation/prompt-v3.md`，SHA-256 `3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`。
- 候选源保留未修改：`agent-work/llm/APP-001-baseline-prep/prompt-v3-candidate.md`，SHA-256 `e90ad55ca20cf356c3c143a723da271f1874eb9fa902dd1379d4afba657a8b5b`。
- v2 回滚文件哈希保留在 manifest/ADR：`d95f853d325e05d9b045921da994256c7b8656336b5be02d75ced20d22755eac`。
- `app001-io.v1`、`acceptance-set-v0`（哈希 `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`）、CAD-003、授权上限不变；acceptance-set 的 `frozen_prompt_version` 是冻结文件的历史元数据，没有改动。
- `FORMAL_EVALUATION_ALLOWED=False`，本轮没有读取密钥、没有真实网络/模型调用、没有修改任何旧正式批次。

## 验证

Python：`/opt/homebrew/bin/python3.11`，Python 3.11.18。

```text
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_decision_policy_v3_candidate tests.llm.test_parser tests.llm.test_envelope_fix tests.llm.test_r2_regression -q
  Ran 153, OK
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q
  Ran 576, OK (skipped=8; existing FUSE file-lock limitation)
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q
  Ran 17, OK
/opt/homebrew/bin/python3.11 -m py_compile src/llm/contract.py src/llm/prompt_loader.py src/llm/parser.py src/llm/adapter.py tests/llm/test_parser.py tests/llm/test_decision_policy_v3_candidate.py
  OK
```

正常案例：完整 v3 envelope 通过 parser，生产冻结 prompt 加载版本/hash 与契约一致。失败案例：携带旧 `app001-extraction.v2` 的 envelope 被 `PROMPT_VERSION_MISMATCH` 拒绝。

## handoff_self_check

```text
handoff_self_check:
  changed=src/llm/contract.py, src/llm/prompt_loader.py, src/llm/README.md, src/llm/__init__.py, src/llm/adapter.py, tests/llm version fixtures/assertions, v3 activation manifest/checklist/README, docs/DECISIONS.md, docs/PROJECT_STATUS.md, docs/PROJECT_PLAN.md, docs/WORKLOG.md
  commands=Python 3.11.18 targeted 153 OK before compatibility closeout; parser 41 OK, LLM 576 OK/8 skipped, Schema 17 OK, py_compile OK, git diff --check OK
  confirmed=ADR-0016 accepted; active loader is v3 and file hash anchored; candidate source unchanged; acceptance-set hash unchanged; explicit v2 audit replay works without changing strict v3 production parsing; formal gate remains false
  unresolved=no real-model effectiveness evidence; no new formal batch authorization
  next_agent_focus=before any v3 model run, verify authorization scope, runtime identities, Ollama digest/version, budget ledger and output evidence retention
```
