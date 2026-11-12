# APP-003-C2：自然语言产品闭环离线接入（CC 工作 Prompt）

## 任务状态

- 任务 ID：`APP-003-C2-NL-PRODUCT-FLOW`
- 执行角色：CC
- 建议执行位置：**已有负责 APP-003-C1 的 CC 对话框**。这是 C1 的后续增量，必须先读取 C1 checkpoint、独立复核报告和当前 `main`；不需要新建 CC 对话框。
- 基线：当前 `main`（以执行时 `git rev-parse HEAD` 为准）
- 设计依据：`docs/DECISIONS.md` 的 ADR-0023
- 状态：`planned`

## 开始前必须做的事

1. 在仓库根目录执行 `git rev-parse --show-toplevel`、`git status --short --branch`。
2. 阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md`、`docs/coordination/handoff-review-protocol.md`、`agent-work/integration/APP-003-C1/checkpoint.md` 和 `agent-work/reviews/APP-003-C1-codex-review.md`。
3. 阅读现有 `src/demo/handler.py`、`src/demo/server.py`、`src/integration/pipeline.py`、`src/integration/schema_to_ir.py` 及相关测试，确认 C1 下载隔离和现有 `/api/generate` 语义。
4. 先在 checkpoint 中记录认领、基线 commit、实现边界和未解决问题。发现当前工作树有其他未提交修改时停止扩大范围，不覆盖它们。

## 目标

在现有 C1 localhost 演示旁增加一个离线自然语言产品流程：

```text
自然语言需求
  → synthetic v5 envelope fixture
  → 产品状态/参数来源展示
  → 用户确认或补充
  → 既有 Schema → Typed CAD IR → CadQuery → 验证/STEP
```

这是流程与失败保护实现，不是模型评测。fixture 必须显式标记 `synthetic_fixture`，不能被报告为真实模型理解。C1 的手动参数入口继续工作。

## 必须遵守的设计边界

- 产品状态使用 ADR-0023 的 `request_received`、`extraction_pending`、`needs_confirmation`、`blocked`、`constructing`、`succeeded`、`failed`；同时保留现有 `pipeline_status`/`pipeline_stage`，不要改写 `run_pipeline` 的历史状态词汇。
- `ask`、缺关键参数、unsupported、`refuse`、解析/契约失败、不可修复冲突在 CAD 前停止；可补充的缺参进入 `needs_confirmation`，拒绝/不可继续进入 `blocked`。
- 用户确认前只允许读取 fixture、解析 envelope、做投影和 Schema/规则预检；不得调用 IR 编译器、CadQuery 或 STEP 导出。
- 用户确认或修改后必须从原始 envelope 重新校验。用户修改的字段标记为 `user_explicit`，但仍经过 Schema/目录规则；不能静默覆盖 catalog/rule-derived 值。冲突返回 `blocked`。
- 每次确认/修改创建新的 UUID run；保留 `parent_run_id` 和 `confirmation_revision`；不覆盖旧 run，不从其他 run 取 STEP。
- 失败 run 绝不能报告成功、发布 STEP 或返回之前 run 的下载文件。下载复用 C1 的 UUID、内存注册表、canonical containment、symlink 拒绝和 SHA-256 检查。
- 浏览器不接触 API key、Authorization header、`.env` 或 provider transport；本工作单元不调用 LLM、不发网络、不创建 batch，不改变 `FORMAL_EVALUATION_ALLOWED=False`。
- 不修改 v5 prompt/contract、Schema、IR 语义、CadQuery 编译器、A2 历史批次或 held-out 检索状态。

## 建议实现形态

可以在 `src/demo/` 内新增产品流程模块，或以最小方式扩展现有 handler/server，但必须保持 C1 `/api/generate` 和 `/download/<run_id>` 兼容。提供与 ADR-0023 等价的服务端操作：

- `create_product_run(request_text, fixture_id)`：返回 `run_id`、产品状态、`decision`、抽取参数、用户显式/目录派生/规则派生参数、`missing_fields`、`unsupported_requests`、`questions`、`conflicts`、`confirmation_revision`。
- `confirm_product_run(run_id, confirmation_revision, confirmed, patch)`：revision 不匹配必须拒绝；`confirmed=false` 或 patch 无效不得进入 CAD；合法确认/修改创建 child run，进入 `constructing` 后调用现有离线 pipeline。
- `get_product_run(run_id)` 与产品 STEP 下载：只读取该 run 的登记证据，不能扫描旧 run 目录；响应包含相对路径和 SHA-256，不暴露秘密。

路径名称可按现有 server 风格确定，但测试必须覆盖并记录实际 JSON 映射。不要把真实模型 transport 接入本任务。

## Fixture 与验收矩阵

在 `tests/demo/fixtures/` 或任务专属 fixture 目录增加固定、无秘密的 v5 envelope：

1. 合法 `answer`：确认后生成真实 STEP；
2. 缺少 `bore_d`：返回问题/`needs_confirmation`，确认前无 CAD；补齐后新 run 才能继续；
3. 目录/规则冲突：展示冲突并 `blocked`，无 CAD；
4. `unsupported_requests`：`blocked`，无 CAD；
5. `decision=ask`：`needs_confirmation`，无 CAD；
6. `decision=refuse`：`blocked`，无 CAD；
7. Schema/IR 失败：`blocked` 或 `failed`，无成功/无 STEP；
8. CadQuery/STEP 导出失败：`failed`，无 STEP、无旧文件泄漏；
9. 用户修改参数：新 `run_id`、正确 parent/revision、旧 run 仍只读；
10. stale revision、未知 run、symlink/hash 篡改、路径穿越：明确失败且零泄漏。

每个需要阻断的 fixture 用 spy 断言 compiler/CAD 入口为零调用；至少一个正常案例和一个失败案例在固定 CAD venv 下实际运行。测试应同时断言输入、envelope、参数来源、confirmation patch、Schema、IR、验证、STEP 的关联字段。

## 产物与提交要求

- 代码：仅改 `src/demo/`、必要的 `scripts/` 和新增/更新 demo 测试；不得改底层 Schema/IR/CAD 语义。
- 文档：更新任务 checkpoint，追加 `docs/WORKLOG.md`；若发现 ADR-0023 与实现冲突先停下并记录，不静默改 ADR。
- 验证（固定 CAD venv 优先）：demo 专项、相关 integration/schema/CAD 回归、`py_compile`、`git diff --check`；测试中明确无网络/无 `.env`/无 LLM。
- 提交一个可审查 commit，提交信息格式：`feat: add offline natural-language product flow [APP-003-C2-NL-PRODUCT-FLOW]`；状态保持 `review`，不要 push 或合并 `main`。
- checkpoint 必须包含：修改文件、状态转换、fixture 清单、实际命令与结果、正常/失败案例、未运行项、风险、`handoff_self_check` 和 `successor_check`。

## 明确禁止

- 不执行真实 DeepSeek/Ollama 请求，不读取密钥或 `.env`，不创建/修改任何正式 batch。
- 不复用 A2 批次授权或历史 raw 响应，不把 synthetic fixture 计为语言效果样本。
- 不为方便 UI 而绕过 Schema、IR、构造门、确认门、run 隔离或下载完整性检查。
- 不把 C1 手动参数演示改写成模型理解证明，不启动 v6 或恢复 RET-003 held-out 实验。
