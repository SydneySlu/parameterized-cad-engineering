# CC 工作 Prompt：APP-003-C1 最小本地 Web 演示

## 任务状态

本任务由 CC 认领实现，Codex 中枢负责独立验收。项目基线为 `main`（开始前重新检查 Git HEAD/工作区，不覆盖其他对话框的未提交更改）。本任务对应 ADR-0022；先阅读 `AGENTS.md`、PROJECT_STATUS、PROJECT_PLAN、WORKLOG、DECISIONS、A2 checkpoint 和 `agent-work/reviews/APP-002-A2-MILESTONE-B-ACCEPTANCE.md`。

## 目标

实现首个可本地运行的浏览器演示，让用户填写需求文本、确认结构化参数，调用现有 Schema→IR→CAD pipeline 生成真实 STEP，并查看本次参数/IR/验证状态，下载 STEP，修改参数后重新生成。

## 设计边界（必须遵守）

- 首切片仅监听 `127.0.0.1`，优先使用 Python 标准库，不新增依赖，不加登录/部署设施。
- 本次调用不接任何 LLM/provider/HTTP transport，不读取 `.env`、密钥或 A2 raw；不复用或修改 `app002-a2-smoke-20261112-01` 至 `-04` 历史批次。需求文本仅作为可追溯记录，结果明确标记“手动参数 / 离线 CAD 生成”，不能假称由模型从文本抽取。
- 用户提交的是受限的结构化参数对象；仅允许 CAD-003 已知字段。复用现有 projector/validator、Schema→IR adapter、`run_pipeline()` 和 compiler，不复制参数规则或编写任意 Python CAD。
- 每次生成必须用新 UUID run_id 和独立目录。仅成功 run 的 STEP 可下载；下载 handler 必须验证 run ID、文件路径 canonical containment、成功 summary/index/manifest/hash，拒绝路径穿越、symlink 逃逸及失败 run。
- 只有现有 pipeline 成功（包括 geometry/STEP readback 比较）才显示 success。缺少 bore 要明确提示/ask，目录冲突/无效字段明确阻断；任何失败不返回之前 run 的 STEP。
- UI 显示当前 run 的用户显式参数、目录/规则派生参数及来源、IR（可折叠原文/JSON）、验证摘要、状态/错误码。修改参数再次生成创建新 run。
- 保留单族、固定环境、螺纹近似和“STEP 通过不等于制造认证”说明。不做三维预览、跨族支持、部署或模型效果宣称。

## 实现建议

仓库没有既有 Web framework。用一个小型 `http.server` 本地应用配静态 HTML/JS 即可；不要把前端框架安装进 CAD venv。将业务逻辑与 HTTP handler 分离，以便单元测试直接测参数/结果和下载校验。为避免目录清单泄漏，UI 状态仅由本进程记录的 run ID 返回，不扫描旧批次。

## 验收条件

1. 使用固定 `work/benchcad-output/venv/bin/python` 可启动 server，首页可访问，绑定地址只能为 loopback。
2. 合法 bore 24 参数可通过实际 CAD compiler 生成 STEP；UI 返回 run ID、规范参数和来源、IR、native geometry/readback 验证摘要及下载链接。
3. 缺 bore 显示 ask/必填错误，不调用 CAD；无效/冲突参数显示确定性错误且无 STEP。
4. 下载只允许本进程中成功且 hash 校验通过的 run 文件；随机/恶意 run ID、`../`、符号链接逃逸均拒绝。
5. 成功后以另一个参数生成第二 run，参数对应新的 IR/STEP；之后触发失败，失败 run 不返回旧 STEP，前一个成功 run 的证据不被改写。
6. 测试保证无网络/LLM 调用，无 `.env`/key 读取，无写入 A2 historical batch。测试至少包含一个成功、一个 ask/拒绝和一个下载隔离案例。
7. 固定 CAD venv 运行新增测试、Integration/CAD/Schema 相关回归；`py_compile`、`git diff --check` 通过。提交前检查真实差异，仅提交本任务文件。

## 交付与交接

- 预计文件：`src/demo/`、`scripts/run_cad_demo.py`、`tests/demo/`、必要的说明文档，以及本任务 checkpoint/WORKLOG/状态更新。按实际架构调整，不改 A2 runner、冻结 prompt、ADR-0021、历史批次或全局 gate。
- 完成后提交独立 commit，并在 checkpoint 记录准确命令、解释器版本、测试结果、正常/失败案例、输出目录、限制和下一步。
- 报告任务状态为 `review`，等待 Codex 中枢独立审查；不能自行标记 `done`。
