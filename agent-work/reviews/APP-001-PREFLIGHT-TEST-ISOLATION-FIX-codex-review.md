# APP-001-PREFLIGHT-TEST-ISOLATION-FIX — Codex 独立审查

- 日期：2026-11-08
- 任务：`APP-001-PREFLIGHT-TEST-ISOLATION-FIX`
- 被审查提交：`e47af64`
- 基线：`bf8117d`（`origin/main`）
- 分支：`cc/APP-001-PREFLIGHT-TEST-ISOLATION-FIX`
- 审查状态：`review`（可交付，待项目负责人 push 后再合入）

## 交接复核

```text
handoff_successor_check:
  predecessor=APP-001-PREFLIGHT-TEST-ISOLATION-FIX / checkpoint.md / e47af64
  files_format=pass; 12 个时间戳取模 batch_id 已替换为 uuid.uuid4().hex[:8]，checkpoint 和 WORKLOG 存在
  core_rerun=pass; Python 3.11.18 下 LLM 全量测试连续两次均 685 passed、8 skipped
  normal_case=pass; TestR4OllamaTagsChatIntegration 5 项正常/预算边界路径通过
  failure_case=pass; TestR3Fix2OllamaTagsFailChatBlocked 2 项 tags 失败阻塞 chat 路径通过
  interface=pass; 仅改变测试 batch_id 生成方式，生产接口、预算、授权和模型配置未变
  limits=pass; 8 个既有 FUSE skip、未运行真实模型、未读取密钥、未启动正式 runner 均保留
  result=pass
  blocking_issue=none
```

## 独立核验

实际运行环境为项目固定基线 Python 3.11.18：

```text
/opt/homebrew/bin/python3.11 --version
  Python 3.11.18

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q
  Ran 685 tests in 0.589s
  OK (skipped=8)

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q
  Ran 685 tests in 0.572s
  OK (skipped=8)

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest \
  tests.llm.test_r3_fixes.TestR4OllamaTagsChatIntegration \
  tests.llm.test_r3_fixes.TestR3Fix2OllamaTagsFailChatBlocked -v
  Ran 7 tests
  OK
```

另外核对：

- `git diff --name-status bf8117d..HEAD` 仅显示 `tests/llm/test_r3_fixes.py`、checkpoint 和 `docs/WORKLOG.md`；
- `git status --short --branch` 显示工作区干净，当前分支相对 `origin/main` ahead 1；
- 测试文件中不再存在 `int(time.time() * 1000) % N` batch_id 生成模式，12 处均使用 UUID 片段；
- 未发现 `src/llm`、prompt、schema、预算、授权或正式批次目录的改动。

## 结论与边界

本修复解决了 preflight 全量测试中由毫秒时间戳取模造成的批次目录碰撞风险，且在 Python 3.11.18 下连续全量运行已复现稳定通过。它是测试隔离修复，不构成生产安全逻辑、模型效果或正式评测证据。

可以进入 `review` 后的 Git 交付步骤：项目负责人先 push 分支并核对远端哈希，随后再由中枢在目标合并提交上复核；在合入 `main` 前不得把 APP-001 preflight 标记为 `done`，也不得启动新的正式模型批次。
