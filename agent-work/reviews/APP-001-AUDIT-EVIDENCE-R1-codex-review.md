# APP-001-AUDIT-EVIDENCE-R1 中枢独立审查

- 日期：2026-11-07
- 状态：review（当前分支已验收；尚未合入 `main`）
- 分支：`codex/APP-001-AUDIT-C1-R1`
- 代码提交：`0a49fb2`、`2581a10`
- 文档提交：`a6c058f`（历史 WORKLOG 行已在本 Codex 审查提交中恢复为原值）

## 范围与结论

本审查覆盖请求前 C1 阻塞审计、有界诊断响应留存、2xx transport wrapper 解析分类，以及冻结样例 A02/A04/A07 的 C1 行为。未发起真实模型或网络请求；未读取密钥；未修改 `work/app001-runs/` 中的旧批次内容。

代码修正符合本工作单范围：留存最多 65,536 UTF-8 字节并记录完整正文 SHA-256、原始/保存长度和截断状态；HTTP 2xx wrapper 缺少 `message`/`content` 或 DeepSeek `prompt_tokens_details` 形状无效时统一归类为 `invalid_json`，安全 metadata 沿现有错误链传递；HTTPError 分支不读取错误正文。请求前阻塞记录增加稳定字段，未包含自然语言输入、evaluator 标签或 reference context 正文。

## C1 定向复核

- 正常案例 A02：冻结用户输入可提取 `bore_d=24`，C1 返回 3 个候选并生成 reference context。
- 失败案例 A04：输入未提供 `bore_d`，C1 以 `C1_NO_SAFE_QUERY_PARAMETER` 阻塞；未从 evaluator-only 标签补值。
- 失败案例 A07：输入提供 `bore_d=75`，envelope 查询因 `RETRIEVAL_SCHEMA_REJECTED` 被 CAD-003 拒绝；候选为空。flat 查询需要其余字段，不能猜值。若要支持目录外近邻检索，需另行决策冻结查询契约。

上述行为与 RET-002/CAD-003 冻结边界一致；A04/A07 不属于当前需放宽的代码缺陷。

## 验证

Python 3.11.18：

- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_audit_evidence_r1 tests.llm.test_c1_acceptance_regression_r1 -v`：17 项通过。
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q`：516 项通过，8 项因既有 FUSE 文件锁限制跳过；skip 不计为通过。
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q`：17 项通过。

Python 3.15.2 下也有 14 项专项、516 项 LLM（8 skip）及 17 项 Schema 通过。CC 曾在 Python 3.11 全量运行中观察到 `test_r3_fixes` 的账本计数不稳定；Codex 随后从当前干净工作状态重跑 LLM 全量成功。该模块单独 51 项通过。既有测试的批次/账本隔离仍值得后续单独清理，但不扩大当前 R1 范围。

## 交接检查

```text
handoff_successor_check:
  predecessor=APP-001-AUDIT-EVIDENCE-R1；checkpoint agent-work/llm/APP-001-AUDIT-EVIDENCE-R1/checkpoint.md；commits 0a49fb2/2581a10/a6c058f
  files_format=专项测试、checkpoint、审查报告和 WORKLOG 存在；旧批次位于 Git 忽略的 work/；WORKLOG 历史误改已恢复
  core_rerun=Python 3.11.18 专项+C1 回归 17/17；LLM 全量 516 passed, 8 skipped；Schema 17/17
  normal_case=A02 C1 bore_d=24、3 候选、reference context 非空
  failure_case=A04 缺 bore_d 安全阻塞；A07 bore_d=75 被 CAD-003 Schema 拒绝
  interface=AssembledInput 阻塞码/字段与 runner JSONL 审计读取一致；TransportError 只传留存 metadata，不传正文
  limits=8 项 FUSE skip；未运行真实模型；Python 3.11 本次全量复跑通过，但曾出现可复现性待观察的历史预算测试波动；当前未合入 main
  result=review
  blocking_issue=无代码阻断；需按项目流程审查并合入 main 后才可将任务标记 done
```

## 后续

先审查并合入当前代码/测试/审计记录。合入前不启动新批次。之后如分析 8 个 Schema 拒绝样本的决策质量，涉及 Prompt、Schema 或输出策略变化时必须新版本化并另行取得正式批次授权。
