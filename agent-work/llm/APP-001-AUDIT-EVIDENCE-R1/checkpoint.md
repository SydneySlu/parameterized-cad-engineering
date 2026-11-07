# APP-001-AUDIT-EVIDENCE-R1 checkpoint

- 日期：2026-11-07
- 状态：review
- 分支：`codex/APP-001-AUDIT-C1-R1`
- 仓库：`/Users/syd/Desktop/参数化 cad 工程辅助设计`

## 范围

补强请求前 C1 阻塞审计字段，以及 HTTP 2xx transport 包装解析失败和 Adapter 模型内容解析失败的有界响应证据留存。未运行真实模型请求，未读取密钥，未修改旧批次。未改变 Prompt、输出契约、RET-002 查询/距离语义、CAD-003 Schema、provider、重试策略或授权范围。

## 改动

- `src/llm/conditions.py`：为 C1 阻塞提供稳定 stage/code/fields。
- `src/llm/runner.py`：阻塞 JSONL 记录加入批次/运行/样例/provider/model、冻结版本/hash、软件版本、prompt hash 可用性、阻塞码及安全检索摘要；不记录自然语言输入或 evaluator 标签。
- `src/llm/adapter.py`：响应留存按 UTF-8 字节最多 64 KiB 确定性截断，记录完整正文长度/hash/保存长度/截断状态；输出路径使用仓库相对路径。
- `src/llm/real_transport.py`、`transport.py`、`retry.py`、`runrecord.py`：HTTP 2xx 包装 JSON/结构错误沿用 `invalid_json` 分类并传递安全留存元数据；HTTPError 正文不读取；留存异常不覆盖 transport 错误。
- `tests/llm/test_audit_evidence_r1.py`：新增专项无网络测试。

## 验证

- Python：`3.15.2`（当前环境；与历史 APP-001 主机 Python 3.11.18 不同）。
- `PYTHONPATH=src:. python3 -m unittest tests.llm.test_audit_evidence_r1 -v`：11 项通过。
- `PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q`：513 项通过，8 项因既有 FUSE 文件锁限制跳过。
- `PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q`：17 项通过。
- 对本任务涉及的 8 个 Python 文件运行 `python3 -m py_compile`：通过。
- `git diff --check`：通过。

## 已确认

- 请求前阻塞对象包含稳定 `error_code`/`error_fields`；没有模型输入、完整 reference context 或 evaluator-only 内容。
- prompt artifact 可用时写入实际 system/user template hash；不可用时显式写 `null` 和 `request_not_constructed`。
- transport 包装失败留存仅在 HTTP 成功读取并解析响应包装失败后触发；合法包装仍返回原有模型 `message.content`。
- JSON 结构类型异常（例如 `choices[0]` 不是对象、`message.content` 不是字符串、`usage` 不是对象）归为现有 `invalid_json`，重试分类不变。
- 留存最多 65,536 字节，元数据无正文片段；500/503 等 HTTPError 分支不读取错误正文。
- 失败的模型 content JSON 仍由 Adapter 现有 parse stage 处理，body 仅在 Git 忽略的 `work/app001-runs/` 下留存。

## 未解决/限制

- 只在 Python 3.15.2 验证；应在项目正式 Python 3.11 环境复核。
- LLM 全量有 8 项既有 FUSE skip；不得把 skip 视为通过。
- 本次无真实网络请求；没有检查供应商线上响应行为。
- A04/A07 冻结样例级 C1 回归由 Codex 中枢另行维护，不包含在本提交。
- 不重写第四批次，也不据此声称 APP-001 放行。

## handoff_self_check

```text
changed=
  src/llm/adapter.py, conditions.py, real_transport.py, retry.py, runner.py,
  runrecord.py, transport.py, tests/llm/test_audit_evidence_r1.py,
  本 checkpoint, docs/WORKLOG.md
commands=
  PYTHONPATH=src:. python3 -m unittest tests.llm.test_audit_evidence_r1 -v -> 11 passed
  PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q -> 513 passed, 8 skipped
  PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q -> 17 passed
  py_compile 相关 8 个 Python 文件 -> passed
  git diff --check -> passed
confirmed=
  HTTP 2xx wrapper failure metadata is bounded and does not replace invalid_json;
  5xx handler does not read body; adapter parse failure retains bounded raw content;
  blocked audit contains stable metadata and no natural-language/evaluator fields
unresolved=
  Python 3.11.18 host rerun pending; 8 FUSE skips remain; no live provider calls
next_agent_focus=
  Codex independently inspect diff and rerun focused/full tests; separately validate A04/A07 C1 regression;
  keep APP-001 in review and require separate authorization for any new model batch
```

## Git

原始 R1 实现 commit：`0a49fb2`。未 push、未合并。原始运行材料仍位于 Git 忽略目录，不纳入提交。

## APP-001-AUDIT-EVIDENCE-R1-TRANSPORT-SHAPE 增补

- 日期：2026-11-07
- 状态：review
- 基线：`0a49fb2`；仅修正 2xx response wrapper 的键存在性和 usage details 类型检查。
- 变更：DeepSeek 与 Ollama parser 要求 `message` 是对象、实际包含 `content` 且其值为字符串；DeepSeek `prompt_tokens_details` 存在时要求对象（显式 null 也拒绝）。异常形状归为既有 `invalid_json`，进入已有受控 2xx diagnostic retention。顶层 usage 缺失/null、details 缺失保持兼容。
- 验证环境：Python 3.15.2。
- 专项：`PYTHONPATH=src:. python3 -m unittest tests.llm.test_audit_evidence_r1 -v`：14 项通过。
- 全量：`PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q`：516 项通过，8 项因既有 FUSE 限制跳过；`tests/schema`：17 项通过。
- 其他：相关 `py_compile`、`git diff --check` 通过。未调用真实网络、未读取密钥、未修改旧批次。Python 3.11.18 复核仍待执行。

```text
handoff_self_check:
  changed=src/llm/real_transport.py; tests/llm/test_audit_evidence_r1.py; 本 checkpoint; docs/WORKLOG.md
  commands=专项 14/14；LLM 516 passed, 8 skipped；Schema 17/17；py_compile OK；git diff --check OK
  confirmed=缺失 message/content、非对象（包括 null）prompt_tokens_details 都抛 invalid_json 且由真实解析路径调用 retainer；异常 message/repr 不含 body；顶层 usage absent/null 及 details absent 兼容；5xx body 仍不读取
  unresolved=仅 Python 3.15.2 验证；8 项 FUSE skip；无真实 provider 行为验证
  next_agent_focus=独立检查变更范围与错误分类；APP-001 保持 review，不启动新批次
```

Commit：`2581a10`。仅提交上述任务文件；未纳入未跟踪的 Codex C1 回归测试。
