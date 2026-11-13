# CC 工作 Prompt：APP-003 产品 Live Extraction 受控入口

## 任务与角色

- 任务 ID：`APP-003-LIVE-PRODUCT`
- 执行者：CC 实现；Codex 中枢独立复核；项目负责人最终批准真实执行
- **对话框：请新建一个 CC 对话框执行本任务**。这是 C3 之后的新产品 live gate，与已有 C1/C2/C3 对话框的离线 fixture 工作边界不同；不要在旧对话框中继续实现，也不要继承旧的 mock/fixture 假设。
- 建议分支：`cc/APP-003-LIVE-PRODUCT`
- 基线：当前 `main`；开始前必须核对实际 HEAD、远端和工作区，不要重置或覆盖其他工作。
- 当前状态：scope 已由项目负责人批准；本工作单只授权实现和离线验证，不授权真实 provider 请求。

## 已批准 scope（必须精确遵守）

范围文件：`agent-work/integration/APP-003-LIVE-SCOPE/scope-draft.md`。

- Provider：DeepSeek
- Model：`deepseek-flash`
- Condition：`C0`，不带检索上下文
- 冻结输入：4 条，ID 为 `P1-24mm`、`P2-ask-bore`、`P3-catalog-conflict`、`P4-unsupported`
- 最大逻辑运行：4
- 每个逻辑运行最多 3 次 HTTP
- 全批最多 12 次 HTTP
- P1 只有在用户确认后允许进入 CAD；P2/P3/P4 必须 fail-closed，不得生成 STEP
- 这是产品独立 scope；不得复用 A2 authorization、A2 batch、A2 approval、A2 raw 或 A2 summary

不得自行增加输入、模型、provider、检索条件、预算、重试次数、CAD 权限或 batch ID。发现 scope/接口不足时停在 `review`，写入 checkpoint，交 Codex 中枢判断。

## 目标

实现一个产品专用的服务端受控入口：

```text
browser request
  → server-side v5 DeepSeek adapter
  → product-specific authorization / budget gate
  → envelope parse + contract/schema preflight
  → C3 confirmation UI/API
  → explicit user confirmation
  → existing Schema → Typed CAD IR → CadQuery → geometry/STEP pipeline
```

真实执行前，代码必须能够在离线 mock/spy 模式完整证明上述时序；本任务结束时不发送真实 HTTP。

## 开始前恢复事实

1. 在仓库根目录执行 `git rev-parse --show-toplevel`、`git status --short --branch`、`git log -3 --oneline`。
2. 阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md`、`docs/coordination/handoff-review-protocol.md`、`docs/coordination/project-memory-and-delivery-playbook.md`。
3. 阅读 C3 checkpoint、C2 checkpoint、ADR-0023、`agent-work/integration/APP-003-LIVE-SCOPE/scope-draft.md`。
4. 先重跑一条正常和一条阻断的现有核心测试，确认 `main` 上 C3 事实；发现不一致立即记录 `review`，不要扩大范围。
5. 核对当前冻结 prompt/contract/schema/model identity 的实际版本和 hash。需要在实现中引用时从当前代码读取，不要复制旧 A2 常量。

## 实现边界

### 1. 产品独立授权与预算

新增产品专用授权/配置模块，建议放在 `src/llm/` 或 `src/integration/` 的最小新文件中。它必须：

- 绑定明确的 `profile_id`、4 个 input ID、provider/model/condition、prompt/contract hash、最多 12 HTTP 和 `enable_cad_pipeline`；
- 绑定具体 batch ID 的批准对象，但在本任务中只实现校验和 dry-run，不分配正式 batch ID；
- 拒绝 A2 authorization、A2 approval、test-only approval、错 provider/model/condition、错 inputs hash、错预算和错 batch binding；
- 在任何目录创建、账本初始化、transport 创建、读取密钥或网络调用前完成验证；
- 保持全局 `FORMAL_EVALUATION_ALLOWED=False`。不得修改全局 gate 让产品入口绕过它。

### 2. 产品 runner / server 连接层

新增最小 runner，复用现有 `load_frozen_prompt`、`build_deepseek_request`、`send_with_retry`、`parse_response`、Schema/IR adapter、`run_pipeline`、`BudgetLedger`/`BudgetAwareTransport` 和 raw retention 机制；不要复制后端业务。

产品入口应至少支持：

- dry-run/offline preflight：验证输入清单、当前 prompt/contract hash、预算可行性、唯一 batch 目录规则，零网络、零密钥读取、零 CAD；
- offline mock：注入 `FakeTransport` 或等价测试 transport，证明正常/ask/conflict/unsupported/parse/schema/pipeline 失败路径；
- formal wiring：只构造服务端 DeepSeek transport 的代码路径，但本任务禁止实际调用。正式路径必须要求独立 product approval 和匹配 batch ID。

如果产品 UI 需要新增 HTTP route，保持 C1/C2/C3 路由兼容，并让浏览器只提交请求文本、run ID 和显式确认 patch。浏览器不能获得 API key、Authorization header、raw 正文或 evaluator labels。

### 3. 确认门和状态

- 模型返回 `answer` 也只能进入 `needs_confirmation`，不能在同一请求中直接调用 CAD。
- 用户确认前 `compile_ir`/`run_pipeline` 必须为 0 次。
- `ask` 且有未回答问题、`missing_fields`、unsupported、目录/规则冲突、refuse、解析错误、Schema 错误均停止构造。
- P1 合法 answer 只有收到服务端严格校验的显式确认后才允许构造；确认必须产生新的 child run，parent 不可变。
- Pipeline、STEP 导出或回读失败返回 `failed`，不得显示 succeeded，不得暴露其他 run 的 STEP。
- 每次运行记录原始需求、模型身份、prompt/contract hash、decision、参数来源、questions/missing/unsupported/conflicts、confirmation、pipeline/STEP 状态和相对路径/hash。

### 4. 证据与隐私

- formal/mock 证据按 scope 目录隔离；summary 只存 repo-relative 路径和 SHA-256。
- raw 响应正文只按现有 retention policy 留存，不进入 UI 或 summary；summary 不包含 API key、Authorization header 或 evaluator-only labels。
- 不读取 `.env`/密钥进行离线测试。测试使用假的 transport/响应；禁止把真实 token 写入 fixture、日志、测试输出或提交。

## 必须新增的离线 fixtures / 测试

模型请求和 evaluator-only 标签物理分离。可新增测试用 envelope/transport response，但不能把预期答案注入生产 prompt 或浏览器请求。

至少覆盖：

1. P1 answer：未确认时零 CAD；显式确认后 mock pipeline 成功，child 隔离、STEP hash 证据正确。
2. P2 ask/missing：问题显示；空确认、错误 patch 和直接 HTTP confirm 均阻断，零 CAD。
3. P3 conflict：Schema/规则阻断，零 CAD，无 STEP。
4. P4 unsupported：unsupported 阻断，零 CAD，无 STEP。
5. parse/contract/schema failure：fail-closed，记录错误码。
6. pipeline/STEP failure：failed，不误报成功，不暴露旧 run。
7. product approval 缺失、test-only、错 batch、错 input hash、错 prompt hash、错模型身份：请求前拒绝，目录/账本/transport/HTTP 均为零调用。
8. 预算：第 13 个 HTTP 尝试不能触网；每次尝试先占账本额度。
9. raw/summary：hash 匹配、相对路径、正文/secret/labels 不进入 summary。
10. C3 回归：页面仍显示 offline fixture 模式，既有 C1/C2/C3 离线测试不回归。

## 验证命令与环境

实现阶段必须使用固定环境：

```bash
PYTHONPATH=src:. work/benchcad-output/venv/bin/python --version
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m py_compile <modified-files>
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest <new-product-tests> -q
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.demo.test_product_flow tests.demo.test_product_ui tests.demo.test_demo_handler -q
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_pipeline tests.integration.test_schema_to_ir -q
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/schema -p 'test_*.py' -q
PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q
git diff --check
```

不得运行真实 provider 请求、live preflight 或读取密钥作为本任务的“验证”。这些动作需要 Codex 中枢复核实现、项目负责人再次批准具体 batch ID 和独立执行授权。

## 交付物

- 产品专用授权/配置与受控 runner/route 的最小实现；
- 离线 fixtures、mock transport 和回归测试；
- `agent-work/integration/APP-003-LIVE-PRODUCT/checkpoint.md`，包含 `handoff_self_check`：修改文件、精确命令、正常/失败案例、未运行项、边界和下一 Agent 关注点；
- 更新 `docs/WORKLOG.md`；若改变状态/计划/范围，更新 `docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md`，不得悄悄扩大 ADR-0023；
- 一个可审查 commit，建议：`feat: add controlled product live extraction entry [APP-003-LIVE-PRODUCT]`；
- 状态保持 `review`，不要 push、不要合并 `main`，不要创建正式 batch。

## 明确禁止

- 不修改 `FORMAL_EVALUATION_ALLOWED` 为 True；
- 不复用或修改 A2 authorization/profile/approval/batch/raw/summary；
- 不调用 DeepSeek/Ollama 或任何外网；
- 不读取或打印 `.env`、API key、Authorization header；
- 不把 evaluator labels 放入 prompt、transport、summary、日志或测试输入；
- 不让模型生成或执行 Python；
- 不把 offline mock、fixture 或本地 CAD 结果描述为真实模型效果；
- 不在没有 Codex 中枢复核和负责人具体执行批准前创建 live batch 或发送 HTTP。
