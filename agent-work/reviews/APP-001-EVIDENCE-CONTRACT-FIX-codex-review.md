# APP-001 evidence contract fix 中枢审查

- 任务：`APP-001-EVIDENCE-CONTRACT-FIX`
- 审查日期：2026-11-07
- 审查对象：CC commit `352ef8a`
- 状态：`review`

## 定向复核

CC 只修改了 `src/llm/parser.py` 的 evidence 字符串检查，并新增对应测试、checkpoint 和 WORKLOG。没有修改 `OLLAMA_FORMAT_SCHEMA`、Prompt、Ollama transport、adapter、runner、预算、授权、ADR-0015 或正式批次。

合法字符串 evidence 通过，空 evidence 数组通过。`field=null`、`quote=null`、`source=null` 均返回 `EVIDENCE_FIELD_TYPE_ERROR`，并分别定位到 `evidence[0].field`、`evidence[0].quote`、`evidence[0].source`。非枚举字符串 source 仍返回 `EVIDENCE_SOURCE_INVALID`。

## 独立验证

```text
/opt/homebrew/bin/python3.11 --version → Python 3.11.18
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_parser tests.llm.test_r1_regression tests.llm.test_providers -q → 119, OK
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q → 499, OK (skipped=8)
PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q → 17, OK
/opt/homebrew/bin/python3.11 -m py_compile src/llm/parser.py tests/llm/test_parser.py → OK
git diff --check → CLEAN
```

8 个 skip 仍是既有 FUSE lock 环境限制。未调用真实模型、未读取密钥、未修改正式批次。

## Git 同步阻塞

本地 `HEAD=352ef8a`，工作区干净。执行 `git fetch origin --prune` 后，`origin/cc/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX` 仍为 `2bb12ec`，本地分支 ahead 1；`origin/main` 仍为 `16f0d1f`。因此 push 尚未在当前远端事实中得到确认。

## 结论

实现和测试通过，可以进入同步阶段；任务不能标记 `done`，也不能启动新正式批次，直到 `352ef8a`（及本审查提交）推送并按项目流程合入 `main`。合入后再由项目负责人决定是否为新的唯一 APP-001 批次授权。
