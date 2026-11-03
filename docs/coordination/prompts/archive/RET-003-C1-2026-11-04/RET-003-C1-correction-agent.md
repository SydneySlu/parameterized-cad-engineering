# RET-003 C1 诊断修正 Prompt（原 CC Agent 续作）

你是本项目的 CC 执行 Agent。本任务是修正你上一轮 RET-003 C1 诊断交付，不是重做评测或扩大范围。任务保持 review；完成后交 Codex 中枢独立验收，不得自行标记 done 或 push。

## 开始前

在项目根目录确认仓库位置、状态和最近提交：

- /Users/syd/Desktop/参数化 cad 工程辅助设计
- git rev-parse --show-toplevel
- git status --short --branch
- git log --oneline -8

阅读 AGENTS.md、docs/PROJECT_STATUS.md、docs/PROJECT_PLAN.md、docs/WORKLOG.md、docs/DECISIONS.md、docs/TASKS.md、docs/coordination/handoff-review-protocol.md、agent-work/reviews/RET-003-codex-review.md，以及 RET-003 脚本、JSON、报告、checkpoint、handoff、RET-002 README/config、src/retrieval 和 retrieval tests。

工作树已有 CC 未提交成果，必须原样保留并在 checkpoint 记录。不得 checkout、restore、reset 或覆盖其他工作。当前已观察到 .git/index.lock 存在；不得删除锁、不得强行绕过 Git。若锁仍存在，可以完成文件修改和测试，但停止在暂存/提交前，并在 handoff 说明。

## 中枢审查指出的必须修复项

1. RET-002 返回对象的候选字段是 results，现脚本读取 candidates，导致 top-1 显示 none、字段误差缺失。
2. query_status 读取了错误层级，JSON 顶层结果为 null。
3. 当前只对 bore-020、bore-080 做同进程重复；协议要求五个合法查询各自跨两个独立 OS 进程复跑。
4. 查询、失败诊断或确定性失败时，脚本仍可能返回成功；必须 fail closed。
5. 报告与机器结果不一致，包含 bore-012、bore-035 的 top-1/距离错误及报告内部的距离/误差矛盾。
6. 结果由 Python 3.10/Linux 生成，不符合冻结的 Python 3.11.18/macOS arm64 环境。

先以 RET-002 源码和真实对象确认接口，再实现；不得凭印象猜字段或把异常静默转成空列表/null。

## 范围和实验边界

只修改以下文件：

- agent-work/integration/RET-003-retrieval-evaluation/run_c1_diagnostic.py
- agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-results.json
- agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-report.md
- agent-work/integration/RET-003-retrieval-evaluation/checkpoint.md
- agent-work/integration/RET-003-retrieval-evaluation/handoff.md
- docs/WORKLOG.md（只追加）

只执行获准的 C1 检索级诊断：3 个主查询 heldout-bore-012/035/080；2 个分开报告的接口诊断；1 个删除 outer_d、预期 RETRIEVAL_MISSING_FIELD 的结构化失败诊断。

不得运行 C0、C2O 或公平 C2；不得调权重、修改 RET-002 策略/候选、manifest、query set、Schema、IR、CAD 或许可证判断；不得读取 STEP/渲染物/第三方图纸或下载 BenchCAD Public/Core；不得声称自然语言抽取、CAD/几何质量、制造安全、泛化或用户收益。

## 实现与验收契约

### 正确解析和完整结果

对每个合法查询，JSON 必须保存 query_id、sample_id、正确层级的 query_status、结构化错误（如有）及所有 top-k 候选。每个候选须含 sample_id、role、rank、总距离、连续距离、离散项和逐字段距离。候选只能来自 retrieval_source。

3 个主查询的每个候选都要相对该查询的 manifest parameters.normalized 真值计算六字段绝对误差。误差只作逐例诊断，不参与调权重、选策略或选候选。必需字段缺失、候选空或角色越界都必须失败。

### 独立进程复跑

五个合法查询（3 主查询 + 2 接口诊断）每个分别在至少两个独立 OS 进程运行。建议由父进程通过 subprocess 调用同一脚本的 worker 模式，使用同一 Python 解释器。worker 输出无时间戳、稳定排序的 canonical JSON；父进程记录两次退出码、canonical SHA-256 和相等性。

不能以同进程重复调用冒充独立进程复跑。任一 worker 非零退出、输出不可解析或摘要不一致，整体诊断必须非零退出。失败诊断应验证 code、stage、fields，且不能吞错。

### 环境门与 fail-closed

正式结果只能在项目固定 Python 3.11.18、macOS arm64 环境生成，并记录 Python、平台及关键依赖版本。环境不符时停止正式生成，报告 ENVIRONMENT_MISMATCH 并保持 review/blocked；不得通过改元数据伪装环境。

manifest hash、query id、split role、policy id、查询状态、候选角色、字段误差、确定性复跑或报告交叉核对任一不通过，都必须返回非零退出码。最好先写入系统临时目录，全部检查通过后再原子替换正式结果；禁止把部分结果当作通过交付。

### 机器结果驱动报告

Markdown 报告必须由同一份通过校验的 JSON 结构自动生成，分列 3 个主查询、2 个接口诊断、失败诊断、独立进程稳定性和限制。禁止手工转录排名、距离或误差。

增加轻量 cross-check/verify 模式，核对报告与 JSON 中的 query id、top-1 sample_id、距离、状态；任一不一致非零退出。报告只能逐例描述，不得将 3 个 held-out 汇总成准确率、泛化率、提升率或统计结论。

### 聚焦契约测试

通过脚本内 --contract-test 或等价的小型测试验证：

- 真实 results 字段产生非空 top-k，query_status 从正确层级写出；
- 缺字段、候选为空、错误候选 role 会拒绝；
- 同进程重复不能被标成独立进程通过；
- 独立进程结果不一致返回非零；
- JSON 和自动生成报告关键字段一致。

不要为此新增无关的生产模块或大批文件。

## 分阶段执行门

按以下顺序完成；每一阶段通过后可以继续，不需要等待额外授权。任一门失败就停止扩大修改，在 checkpoint 标记 blocked/review 并写明证据。

1. **M0 环境与接口确认**：先记录实际 Python/OS/架构；从 RET-002 源码确认候选字段、query_status 路径、canonical 序列化和错误对象结构。环境不符即停止，不生成正式 JSON/报告。
2. **M1 契约测试先行**：先写/运行小型契约检查，证明 results 与 query.query_status 的读取、缺字段/空候选/角色错误拒绝，以及独立进程比较的失败路径有效。此阶段先不覆盖正式结果文件。
3. **M2 单查询校准**：只用已授权主查询中的一个样本验证 JSON 结构、字段误差和距离；逐项对照 RET-002 原始结果，确认没有手抄值后再运行全量诊断。
4. **M3 全量运行**：运行全部 3 个主查询、2 个接口诊断、1 个失败诊断；五个合法查询分别完成两次独立进程复跑。任何一例失败都不得继续产出“通过”的完整报告。
5. **M4 生成与交叉核对**：从通过校验的机器 JSON 自动生成 Markdown；运行 JSON/report cross-check 和全部回归检查。
6. **M5 交接**：汇总命令、退出码、摘要、环境、限制与下一步，更新 checkpoint/handoff 和 WORKLOG。不得只凭脚本退出 0 或报告文字宣布成功。

## 验证与交接

固定环境中记录实际运行命令和结果：

- RET-001 tracked-only：15 rows / 660 checks / 0 failures；
- RET-002 tests：30 passed；smoke 按既有预期通过；
- 3 个主查询和 2 个接口诊断均成功，候选全部为 retrieval_source；
- 失败诊断为 RETRIEVAL_MISSING_FIELD，stage/fields 正确；
- 五个合法查询分别完成至少两次独立进程复跑且 canonical SHA 一致；
- contract test、JSON/report cross-check、py_compile、git diff --check 全通过。

RET-001 时间戳验证报告先备份到系统临时目录，复跑后精确恢复；不要留下运行噪声。不要提交 STEP、渲染物、虚拟环境、大型缓存或 outputs 目录。

更新 checkpoint/handoff，记录修改、真实命令和输出、环境、独立进程证据、限制、未解决项及下一步；WORKLOG 只追加。若 Git 锁仍存在，不删除锁，不暂存或提交，报告阻塞。锁消失后也要先检查没有 Git 写进程，再按项目规则提交：

fix: correct RET-003 C1 diagnostic [RET-003]

无论提交状态如何，交付状态保持 review，不得 push。完成后将具体文件、验证证据和任何阻塞交给 Codex 中枢独立审查。
