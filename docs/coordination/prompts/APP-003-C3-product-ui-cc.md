# CC 工作单：APP-003-C3-PRODUCT-UI

## 任务与角色

- 任务 ID：`APP-003-C3-PRODUCT-UI`
- 负责人：CC 实现；Codex 中枢独立复核
- 建议：继续使用已经实现 C1/C2 的 CC 对话框，避免重复恢复接口上下文
- 基线：`main`，当前仓库交接 commit `b90a83c`（若你的 checkout 不同，先按下方恢复协议核对，不要重置或覆盖其他工作）
- 状态：`planned`；CC 开始工作并认领后更新为 `in_progress`

## 目标

在现有本地 demo 中增加独立的自然语言确认页面，复用 C2 离线产品 API，形成可操作的界面流程：

```text
输入需求 + 选择离线 envelope fixture
→ 查看抽取结果/参数来源/问题
→ 确认或补充用户显式参数
→ 查看构造、验证、STEP 状态
→ 只下载本次成功 run 的 STEP
```

页面必须显著标记当前使用 synthetic fixture；用户填写的需求文本会保存为 run 输入，但抽取内容来自所选 fixture。不得将其展示为真实模型抽取或产品 live extraction。

## 开始前必须恢复的事实

1. 确认仓库根目录、分支、HEAD、工作区；不得覆盖他人未提交内容。
2. 阅读根目录 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md`。
3. 阅读 `docs/coordination/handoff-review-protocol.md` 和 `docs/coordination/project-memory-and-delivery-playbook.md`。
4. 阅读 `agent-work/integration/APP-003-C2/checkpoint.md` 和 ADR-0023，并检查 C2 handler 与 HTTP 路由的实际签名/字段。
5. 先跑一条正常与一条阻断用例的现有核心测试，确认当前交接事实。发现状态或接口不一致时先记录并报告，不扩大实现范围。

## 实现范围

- 保留 C1 根页面 `/`、`/api/generate`、`/download/<run_id>` 的现有行为。
- 新增独立入口，例如 `GET /product`；以静态 allowlist 提供已登记 fixture 选项，不接受浏览器任意文件路径。
- 复用 C2 现有接口：
  - `POST /api/product/create`：`{request_text, fixture_id}`
  - `POST /api/product/confirm/<run_id>`：`{confirmation_revision, confirmed, patch}`
  - `GET /api/product/<run_id>`
  - `GET /product-download/<run_id>`
- 页面明确显示离线 synthetic fixture 模式及 fixture 标签；提供需求文本和固定 fixture 选择。对“需求文本仅作记录、fixture 提供抽取结果”的关系应清楚说明。
- 显示 `run_id`、`product_status`、`decision`、需求文本、fixture 来源、`extracted_parameters`、`user_explicit_parameters`、`catalog_derived_parameters`、`rule_derived_parameters`、`missing_fields`、`unsupported_requests`、`questions`、`conflicts`、`errors`。
- `catalog_derived_parameters` 与 `rule_derived_parameters` 只读展示。允许用户只补充/修改明确的用户参数；修改后通过 C2 confirm API 产生新的 child run，不覆盖 parent。至少覆盖 `bore_d` 缺参补充和合法值确认。
- 提供明确确认动作。`ask`、`refuse`、unsupported、conflict、invalid/blocked 状态不得误显示成可构造成功；遵循 C2 API 返回的状态和确认门。
- 只有当前 child run 的 `product_status == succeeded` 且有成功 STEP 证据时显示该 child 的下载链接。失败/阻断路径不显示可用下载按钮，不复用先前 run 的文件。
- 展示 schema/IR/几何验证结果（若响应中存在），以及 pipeline stage、失败原因和 STEP hash/bytes 等可用证据。
- 动态 UI 内容必须安全渲染：优先使用 `textContent` / DOM API；若使用 `innerHTML`，所有动态值须完整转义并有回归测试。
- 不增加真实模型调用，不读取 `.env`/API key，不创建 batch，不改变 prompt/contract/Schema/IR/CAD 语义、`FORMAL_EVALUATION_ALLOWED` 或既有 gate。

## 明确不做

- 不接真实 v5 adapter、provider、transport 或外网。
- 不启用产品 live extraction，不准备/执行真实模型批次。
- 不改 C2 状态机/API 的语义；若发现必需接口缺口，先记录最小缺口并交 Codex 中枢审查，不自行扩大范围。
- 不做部署、认证、多用户、持久化数据库或三维预览。
- 不把 synthetic 流程宣称为真实自然语言理解能力。

## 验收条件

1. `GET /product` 可用，页面醒目标明离线 fixture 模式；原 C1 `/` 页面和 API 回归保持通过。
2. 合法 bore24 fixture：创建后显示 `needs_confirmation`、bore_d 来源；确认后显示 child `succeeded`，可下载与该 child run 对应且 hash 匹配的 STEP。
3. bore80 fixture 显示规则派生的 `second_screw=1`，规则派生值只读；合法确认后可完成 CAD/STEP。
4. ask-missing-bore fixture：显示问题/缺参；补充 `bore_d=16` 后由新 child run 完成；parent 记录保持不变。
5. conflict、unsupported、refuse、Schema fail fixtures 显示阻断原因；不得提供成功下载，不得调用 CAD。
6. CAD/STEP 导出失败显示 `failed` 与原因，不误报成功、不出现旧 STEP 下载链接。
7. 参数确认/修改后是新 child run；切换或新建另一个需求不会复用前一个 run 的状态/文件。
8. 恶意字符串作为纯文本显示，不能触发 HTML/脚本执行。
9. 至少有可重复的 HTTP/UI 集成验证覆盖 create→confirm→get→download 及阻断路径；在固定 CAD venv（Python 3.11.18）执行 demo、C2、C1、integration、schema 和 CAD compilation 适用回归。所有测试注明是否使用真实本地 CAD；不得有模型/外网调用。
10. `py_compile` 和 `git diff --check` 通过；保留 C2/C1 接口与 gate，更新 checkpoint、状态/计划/任务表和追加式 WORKLOG。

## 交付与提交

- 修改限于 C3 UI/测试/文档及确有必要的 server 路由；冻结的 C2 产品状态机与后端不重写。
- 新建或更新 `agent-work/integration/APP-003-C3/checkpoint.md`，记录范围、正常/阻断验收、命令、运行环境、未运行项、限制和 `handoff_self_check`。
- 更新 `docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/TASKS.md` 与 `docs/WORKLOG.md`；状态在中枢独立验收和合入前为 `review`，不可自标 `done`。
- 只提交本任务文件；commit message：`feat: add offline product confirmation UI [APP-003-C3-PRODUCT-UI]`。
- 不 push、不合并 `main`；完成后提供分支、HEAD、父提交、工作区状态、文件清单、确切测试命令/结果和下一步复核重点。

## 首轮实现优先级

先完成独立 `/product` 页面和真实 C2 API 串接，再补齐本地 HTTP E2E 与 UI 安全回归。任何状态报告必须以实际 run response 为准；静态 HTML 检查不能替代 API/真实 STEP 烟测。
