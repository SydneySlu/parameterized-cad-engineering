# APP-001-ADAPTER-R3：移除 Prompt 与 Retention 的公开绕过口

你是 CC 执行 Agent，任务 ID 为 `APP-001-ADAPTER-R3`。本轮只修复 R2 中枢复核确认的两个可绕过入口，并补齐直接对应的回归测试和交接记录。R2 的 transport 精确类型检查与 canonical path resolver 已经有效，不要重写或扩大范围。

## 启动检查与事实源

在 `/Users/syd/Desktop/参数化 cad 工程辅助设计` 确认 Git 根目录、工作树和最近提交。开始前阅读 `AGENTS.md`、项目状态/计划/日志/决策、handoff-review-protocol、`agent-work/reviews/APP-001-ADAPTER-R2-codex-review.md`、R2 修正 Prompt、基线契约、冻结 `prompt-v2.md`、adapter/prompt_loader/README 与当前 checkpoint/handoff。发现契约冲突或无法安全修正时，记录 `blocked`/`review` 并停止受影响部分。

## 边界

允许修改 `src/llm/`、`tests/llm/`、`src/llm/README.md`、本任务 checkpoint/handoff，以及只追加的 `docs/WORKLOG.md`。禁止读取真实密钥、访问 `.env`、调用 DeepSeek/Ollama、运行九条冻结样例或生成正式指标；禁止打开正式评测门、增加 live transport、修改冻结 Prompt/ADR/Schema/IR/CAD/RET；禁止复制成 v2/v3 大文件或在 CC outputs 目录放文件。完成后提交一个 commit，状态保持 `review`，不 push、不合并、不标 `done`。

## 已确认缺口

审查证据见 `agent-work/reviews/APP-001-ADAPTER-R2-codex-review.md`：

1. `Adapter.run(..., verify_frozen_prompt=False)` 可关闭核验，`_prompt_loader_path` 可替换验证目标；合成请求证明关闭核验后 FakeTransport 会被调用。
2. `RetentionPolicy._test_only` 是公开 dataclass 字段；调用者能直接设置为真并将合成 raw response 写入仓库外。

## 必须修正 A：正式 Adapter 强制核验冻结 Prompt

- 从 `Adapter.run()` 移除 `verify_frozen_prompt` 和 `_prompt_loader_path` 参数。正式入口必须无条件加载并核验冻结 Prompt；失败须在 `send()` 前 fail closed。
- 不得换成其他公开布尔值、环境变量、CLI 开关、任意 verifier、任意 artifact 路径或可伪造标记。
- Prompt artifact 路径固定为仓库冻结文件。不得只检查文件含有版本字符串或根据文件名认定有效。
- 为当前已审查的 `prompt-v2.md` 固定可审查的 SHA-256 锚点，明确 hash 的字节范围、UTF-8/换行处理及更新方式。文件缺失、不可读、hash 不符、版本元数据错误、系统 Prompt/用户模板变化都必须 fail closed；不得改冻结文件迁就实现。
- 保留实际 system prompt、user template 和渲染 payload 的 hash 记录。说明 fenced block 与 `{{placeholder}}` → `{placeholder}` 的规范化规则。
- 集成正例必须使用真实冻结 artifact 内容，通过默认 `Adapter.run()` + FakeTransport 成功到达 mock 请求；不得关闭校验。
- 负例通过正常 `Adapter.run()` 覆盖 system prompt 改动、user template 改动、保留版本字符串但改正文、artifact 缺失/不可读；每例断言异常不含 Prompt 原文且 `send_calls == 0`。
- Loader 纯函数可接受合成文本做单测，但不得提供可把合成 Prompt 送入 Adapter 的公开绕过。移除所有 `verify_frozen_prompt=False` 与 `_prompt_loader_path` 测试用法。

## 必须修正 B：Retention 测试路径不能由公开策略伪造

- 移除 `RetentionPolicy._test_only` dataclass 字段及普通调用方可设置的测试标志；移除 `Adapter.run()` 中据此开放临时目录的分支和 `_allow_test_path` 参数。
- Adapter 正式路径始终使用固定 canonical `work/app001-runs/`。公开策略只能关闭/开启 retention，不得指定任意目录；若允许子目录，必须经 canonical resolver 确认仍位于 ignored root 中。
- 保留 R2 路径检查：拒绝外部绝对路径、`..` 越界和逃逸 symlink。目录创建后再次保证实际写入位置位于 canonical root；说明并处理 resolve 与写入之间的 symlink 竞态，不能声称一次预检能防住任意并发替换。
- 测试不得通过公开 Adapter/RetentionPolicy 把响应写入任意临时目录。可对纯路径验证函数单测；若需测 writer，可拆成私有受控组件，由测试在临时 root 下调用，但生产 Adapter 永远只用 canonical root，测试注入不得成为 Adapter 参数或可伪造策略字段。
- 覆盖默认关闭不写文件、正式策略拒绝外部目录、canonical root 写入（仅合成内容且清理）、`..`/symlink 越界拒绝、写入失败明确记录。增加旧 `_test_only=True` 或同等公开构造形式的负例，证明仓库外不会产生响应文件。

## 回归、文档和交接

保留 R2 已有效的 transport 门：仅精确 `FakeTransport` 类型可在正式门关闭时通过；Fake 子类、MockTransport 子类及 duck-type transport 的 `send_calls` 均为 0。不得回退凭据隔离、费用、重试总耗时、parser 严格性和阶段记录。

至少运行并逐项记录以下命令及结果：

- `PYTHONPATH=src python3 -m unittest discover -s tests/llm -v`
- `PYTHONPATH=src python3 -m unittest tests.schema.test_set_screw_shaft_collar`
- `PYTHONPATH=src python3 -m py_compile src/llm/*.py tests/llm/*.py`
- `git diff --check`

准确列出实际覆盖，不得声称运行了未运行的 symlink、篡改或写入失败测试。记录 `git status --short`，确认没有临时/ignored 响应、越界文件、遗留锁或 outputs 文件。更新 README/checkpoint/handoff，追加 WORKLOG，不覆盖 R1/R2 历史。交接格式：

```text
handoff_self_check:
  changed=<文件与 commit>
  commands=<实际命令与逐项结果>
  confirmed=<Prompt 强制核验、Retention 路径限制、transport gate 的证据>
  unresolved=<未解决事项及是否超出范围>
  next_agent_focus=<Codex 中枢复核点>
```

明确声明：没有真实网络、密钥、模型、九条样例或正式指标；IR → Typed CAD IR 映射未冻结且不属本任务；`APP-001-ADAPTER=review`、`APP-001=planned`、正式评测门保持关闭。
