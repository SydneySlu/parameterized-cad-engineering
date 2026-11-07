# 架构与项目决策记录

决策记录采用追加方式。新决策不要修改旧记录；如果后续改变，增加新的 ADR 并注明替代关系。

## ADR-0001：Git 作为项目事实源，Profile Pack 作为可选上下文层

- 日期：2026-10-28
- 状态：accepted
- 决策人：项目负责人 + Codex

### 决策

使用本项目 Git 仓库保存代码、文档、任务、状态、决策和可审查实验记录。`profile-pack` 可以在本机为 Codex、CC 等 Agent 提供项目上下文、决策反馈和访问控制，但不得代替 Git 状态和提交历史。

### 原因

`profile-pack` 已实现 Project Profile、任务/里程碑/风险/决策记录和本地 MCP 接入，适合作为 Agent 的上下文辅助层；但它当前是 localhost 单机 MVP，没有远程认证或多用户协作，不适合作为跨设备同步的唯一事实源。Git 更适合版本、分支、差异、回滚和跨设备 clone/push。

### 影响

- 所有重要进展必须写入仓库并提交。
- 如果接入 Profile Pack，项目数据使用独立 Project Profile，个人 Profile 不混入项目资料。
- Profile Pack 记录可以辅助 Agent 获取上下文，但无法替代仓库中的状态页、工作日志和决策记录。

## ADR-0002：首期采用轻量版路线

- 日期：2026-10-28
- 状态：accepted
- 决策人：项目负责人 + 导师讨论结论

### 决策

首期聚焦 Typed CAD IR、确定性 CAD 构造/验证和小样本检索。监督微调、强化学习、通用视觉融合和跨零件族泛化不作为交付依赖。

### 原因

项目创新点在结构化 CAD 中间表示和少样本检索闭环；轻量版更符合两三个月内完成可运行、可检查、可复现系统的约束。

## ADR-0003：复杂任务采用 checkpoint，中枢负责编排和仓库体检

- 日期：2026-10-28
- 状态：accepted
- 决策人：项目负责人 + Codex

### 决策

复杂任务允许在中途通过 checkpoint 同步，并可以提交阶段性 WIP commit。Codex 中枢负责根据当前状态拆分任务、生成不同 Agent 的初始化 prompt、审查阶段结果、维护任务依赖，并在合并前运行仓库体检。

### 原因

复杂 CAD、数据和检索工作很难一次完成；等待最终结果会隐藏风险，也会让不同聊天框失去共同上下文。阶段性同步可以及时暴露依赖、范围和验证问题。

### 影响

- `in_progress` 不代表失败或未完成，而是允许持续同步的正式状态。
- `review` 表示阶段或最终结果等待中枢审查，`done` 只在合并到 `main` 后使用。
- 中枢生成的 prompt 必须包含任务 ID、允许范围、检查点、验收条件和交接格式。

## ADR-0004：私有审查台账与独立复核

- 日期：2026-10-28
- 状态：accepted
- 决策人：项目负责人 + Codex

### 决策

在仓库外建立本地中枢审查台账，记录任务分派、对话框/Agent、初始化 prompt 摘要、阶段检查点、审查结论、问题修正及对应 commit。项目事实、Agent 正式进度、范围决策和可交接结果仍必须写入 Git 仓库；私有台账不得作为唯一事实源，也不自动提供给其他 Agent。

重要架构选择、关键论文证据或高风险变更可交由另一个 Codex 对话框独立复核。第二对话框只提供审查意见，不与当前中枢并列维护项目状态或做最终范围决策；有争议时回到仓库证据和项目负责人裁决。

## ADR-0005：BenchCAD 数据集优先路线（待确认）

- 日期：2026-10-29
- 状态：proposed
- 决策人：用户转述导师建议；待用户/导师确认具体首期范围

### 建议决策

首期优先直接利用 BenchCAD 2.0 社区参数化零件族及其经过审核的构造器、参数规格、约束和生成/验证流程。垂直行业零件族不作为项目启动前置条件。建议先用两个结构有差异且状态、许可证、运行验证已确认的族完成端到端，再视 12 周进度扩展到当前可用的其他族。新增零件族仅作为补充工作。

### 边界

- BenchCAD GitHub 社区族源文件与其 Public/Core 任务评测集是不同资产，分别记录版本和许可证。
- Public/Core 数据卡当前限制训练、检索语料、RL 环境和再发布；不进入本项目训练或检索库。
- BenchCAD 的 `build/spec/check/refine` 可复用或经适配调用；项目仍需自有 Typed CAD IR、输入/追问任务集和端到端指标。
- 具体纳入哪些族、是否使用公开发布的数据制品，以及允许发布哪些派生实例，要在族级许可/状态审查后另行确认。

### 原因

该路线贴合导师关于提高对成熟开源数据集利用率和成果认可度的建议，也降低从零收集 CAD 形状与工程参数的负担。多族实验能展示系统对不同参数结构的适配，但不应夸大成开放域 CAD 泛化。

### 影响

DATA-002 应先做族级资产清单、许可/状态审查和两个族的 smoke test；随后形成项目 manifest/adapter、自然语言任务集、检索对照与逐族几何验证。只有用户/导师确认后，才将该路线标为 accepted 并冻结首期族数量。

### 原因与限制

仓库记录、可复现检查和独立复核可以降低单个对话框上下文丢失或判断错误造成的影响。私有台账减少审查过程和任务编排细节对普通 Agent 的暴露，但本地文件权限不是对同一用户账户下其他进程的强隔离，也不会跨设备同步。它只作为用户与中枢约定使用的辅助记录。

## ADR-0006：统一共享项目基座

- 日期：2026-10-29
- 状态：accepted
- 决策人：项目负责人 + Codex

### 决策

将当前 Git 仓库整体迁移到 `/Users/syd/Desktop/参数化 cad 工程辅助设计`，作为当前主机的共享项目基座。保留 Git 历史、现有目录和协作文档；新增 `agent-work/` 及其职责子目录，用于存放各 Agent 的中间工作和交接材料。所有后续 Agent prompt 都必须要求 Agent 先确认该 Git 根目录，再按职责写入对应位置。

### 原因与边界

统一根目录可以避免不同聊天框把文件写入各自默认目录，降低重复副本和遗漏同步的风险。源代码、测试、正式文档和正式数据仍使用 `src/`、`tests/`、`docs/` 和 `data/`；`agent-work/` 不是绕过 Git 或 `.gitignore` 的入口。其他设备的路径可能不同，Agent 应使用当地 clone 的 Git 根目录并在交接中记录实际路径。

## ADR-0007：冻结首期零件族为 `set_screw_shaft_collar`

- 日期：2026-11-02
- 状态：accepted
- 决策人：项目负责人 + Codex
- 替代：ADR-0005 中“首期族集合待确认”的范围状态；ADR-0005 的 BenchCAD 数据优先路线和许可边界继续有效

### 决策

首期只实现和评测 BenchCAD 社区族 `set_screw_shaft_collar`。数据来源固定为：

```text
repository: https://github.com/BenchCAD-org/benchcad-2
source_commit: 035f467142888edfd0bd7cd73906f9b155c8f43c
family_path: designs/set_screw_shaft_collar
family_id: set_screw_shaft_collar
```

首期支持该族当前参数目录、轴孔/外径/宽度、紧定螺钉及其已记录的参数耦合和约束。首期不承诺第二族、开放域零件泛化或任意自由 CAD 特征生成；扩展族必须另行建立来源、许可证、参数和运行证据并追加决策记录。

### 原因

DATA-003 已确认该族在固定 commit 中真实存在，具有 `part.py`、`spec.py`、`family.json`、可调用的 `build()`/`check()` 和明确的目录行耦合；合法、边界、非法输入以及 STEP 导出/回读均已有最小 smoke 证据。单族范围符合轻量版的两三个月交付约束，也能先验证 Typed CAD IR、确定性构造/验证和小样本检索主线。

### 约束与未决事项

- BenchCAD 族状态目前是 `MERGED`，不是 `release-qualified`；不得把它写成官方发布实例集。
- 源码和 designs 按固定仓库说明适用 MIT；生成 STEP/渲染图是否属于可再发布的授权范围仍需单独确认。
- 族目录引用的第三方标准图纸、图片和下载文件不自动受 BenchCAD LICENSE 覆盖，不复制进项目交付物。
- 当前源码快照仍标记 `reproducibility_partial`，直到 DATA-003 补充任务建立或证明无法建立干净归档。
- 几何数值容差仍需在 CAD-006 验证器前置测量中确定；本决策不冻结容差。

## ADR-0008：冻结首族 CAD-006 几何比较策略

- 日期：2026-11-02
- 状态：accepted
- 决策人：Codex 中枢（基于项目负责人授权推进 CAD-005/006）
- 策略 ID：CAD-006.geometry-comparison.v1
- 证据：agent-work/cad-validation/CAD-005-006/tolerance-results.json、tolerance-preflight.md、checkpoint-tolerance.md；Codex 审查见 agent-work/reviews/CAD-005-006-tolerance-codex-review.md。

### 决策

硬性规则和拓扑门槛独立于浮点容差：preflight 参数目录与耦合规则必须通过；构造和 STEP 回读均须为有效的单 solid、单 shell；solid/shell/face/edge/vertex 计数及摘要数组长度必须精确相同；缺失、非有限、空形状、无效实体和多实体均失败。

同一进程、同一固定环境下重复 native 构造要求结构计数和规范排序后的体积、包围盒、面面积及边长摘要精确相等。该判据不代表跨进程或跨平台承诺。

同一次 native 几何与其 STEP 回读使用如下阈值：

| 指标 | abs 约束 | rel 约束 |
|---|---:|---:|
| 包围盒六坐标 | abs(a-b) <= 1e-5 mm | 不使用 |
| 体积 | <= 0.0682 mm³ | <= 3.941e-6 |
| 升序面面积列表逐项 | <= 0.00794 mm² | <= 1.440e-5 |
| 升序边长列表逐项 | <= 1e-5 mm | <= 2.956e-8 |

体积、面面积和边长的相对误差定义为 abs(a-b)/max(abs(a),abs(b))；同一比较项的 abs 和 rel 条件均须通过。面面积和边长列表数量必须精确相同，分别升序后逐项比较。bbox 使用 abs-only，避免零坐标附近相对误差失真。STEP 字节 hash 仅作产物标识，不参与几何通过判定。规范全文见 agent-work/typed-cad-ir/IR-001-v0/ir-v0-spec.md 第 9.2 节。

### 阈值依据与适用范围

45 个合法目录 build/readback 样本中，roundtrip 最大观测值为：体积 abs 0.0340786283195 mm³ / rel 1.97024648349e-6；bbox abs 3.5527136788e-15 mm；面面积 abs 0.003967669644 mm² / rel 7.19713167552e-6；边长 abs 2.79570571138e-7 mm / rel 1.47760136545e-8。体积、面积与边长相对阈值取各自最大观测值的向上取整 2 倍；bbox 和边长 abs 下限定为 1e-5 mm。该策略是几何摘要及 STEP 回读的工程验收规则，不是制造公差或计量标准。

测量基线为 Python 3.11.18、CadQuery 2.3.0、OCP/cadquery-ocp 7.9.3.0、NumPy 1.26.4、macOS arm64，固定 BenchCAD source commit 035f467142888edfd0bd7c73906f9b155c8f43c。测量来自 BenchCAD 原生 build()，不是项目 IR 编译器输出。

Windows/Linux、其他 CPU 架构、其他软件/STEP writer 版本、跨进程重复性及第二族均未验证。更改环境、构造算法、测量定义或族范围时须补充代表性测量并经 Codex 审查。CAD-005/006 实现必须对真实 IR 编译输出完成正常案例、hard boundary、STEP 回读和失败案例集成验证；若对照参考几何超出已冻结策略，暂停并报告，不得自行放宽阈值。

IR-001 R3 的 CAD-006.pending.v0 是早期未验证候选，由本 ADR 和 IR 规范中的 CAD-006.geometry-comparison.v1 取代；旧审查记录保留为历史。

## ADR-0009：APP-001 采用云端/本地双基线，先冻结口径再测端到端指标

- 日期：2026-11-04
- 状态：accepted（模型身份以运行时 API 返回值为准）
- 决策人：项目负责人 + Codex

### 决策

APP-001 使用 DeepSeek v4.1 Flash 1017 作为云端主效果基线，使用 Ollama `qwen3:8b`（digest/ID `500a1f067a9f`）作为本地部署、成本和延迟对照。首期本地基线设备为 MacBook Air M5、16 GB RAM、512 GB SSD。未来 Windows CPU 设备只作为单独迁移/成本探索环境。

云端正式结果必须保存 provider、API 返回的 `model` 字段、调用日期和解码参数；用户标签不替代 API 身份。APP-001 先冻结共同输入、结构化输出、Prompt、错误处理和指标口径，再运行模型。字段抽取与 Schema 指标在模型输出后测量，CAD/STEP 指标在同一输出接入现有确定性链后测量；APP-001 之前不产生端到端成绩。

### 原因

双基线同时覆盖效果上限的实际可用云端条件和本地部署的成本/延迟约束。先冻结协议可以避免模型、输入集或后处理变化导致不可比结果，也能把 RET-003 的检索级诊断与真正的端到端 CAD 收益分开。

### 边界

本 ADR 不冻结公平 C2、监督微调、强化学习或第二族扩展。Windows CPU 结果不得与 Mac 结果合并成一个性能结论；模型身份不一致、环境变化或接口变化时必须新建运行批次并进入 review。

## ADR-0010：APP-001 的抽取责任、置信度、重试和资源记录策略

- 日期：2026-11-05
- 状态：accepted（APP-001 首轮实验契约）
- 决策人：项目负责人 + Codex
- 关联：ADR-0009；`docs/coordination/APP-001-baseline-contract.md`

### 决策

1. LLM 只抽取用户明确表达的参数并保留证据；目录值和阈值值由确定性 Schema/规则层补齐。关键字段 `bore_d` 缺失时追问或拒绝，不得猜测。
2. `confidence` 默认 `null`；若模型返回数值，仅作为未校准诊断信息记录，不参与追问/拒绝路由、模型输出放行、验收评分或模型比较。
3. 云端和本地共同解码默认值为 `temperature=0`、`top_p=1`、`max_output_tokens=512`。seed 若运行时支持则固定并记录；不支持则明确记 `unsupported`。每次调用保存实际生效配置。
4. 每个样本最多重试两次（加初始请求最多三次），只针对连接/读取超时、连接中断、HTTP 429 和 HTTP 5xx；退避依次为 1 秒、2 秒。认证/权限、错误请求、上下文超限、无效 JSON、输出契约/Schema/规则拒绝和 CAD 失败不重试。失败样本保留在冻结分母中。
5. 分开记录配置的 provider/model 名与运行时返回的 provider/model 字段。云端逐请求记录 input/output/total token 及费用/币种；费用只接受 API 实报或注明日期/版本的价目表计算，来源不明时写 `not_available`。本地记录每样本推理墙钟耗时、尝试次数和总耗时，不将云端 token/费用口径套用到本地。

### 边界

此 ADR 冻结首轮运行策略，不代表云端 API 的真实 model ID、provider、seed 能力或费用已经验证。验收集与 Prompt 在通过最终复核前仍为草案；不得据此生成正式测量结果。若 provider 不接受某项共同解码参数，必须记录实际生效值并暂停公平对照复核，不能静默移除或替换。

## ADR-0011：DeepSeek Flash API 配置、价格记录与密钥注入

- 日期：2026-11-05
- 状态：accepted（配置资料；不代表已完成运行时探测或放行正式评测）
- 决策人：项目负责人 + Codex
- 关联：ADR-0009/0010；`docs/coordination/APP-001-baseline-contract.md`

### 决策

1. 云端请求配置使用 provider `DeepSeek`、模型 ID `deepseek-flash`、OpenAI 兼容 Base URL `https://api.deepseek.com`。官方文档将该请求模型标为 `DeepSeek-V4.1-Flash-1017`；每次运行仍保存 API 响应中的 `model` 字段。官方 Chat Completions 示例没有返回 provider 字段，未实际观测前记录 `runtime_returned_provider=not_exposed`。
2. 云端记录响应中的 prompt/completion/total tokens 及缓存命中/未命中 token；费用依据官方价格快照和请求时段计算并记录快照日期、来源、币种和公式。2026-11-05 核对的费率为 CNY/百万 token：空闲输入缓存命中/未命中/输出分别 ¥0.02/¥1/¥4，高峰分别 ¥0.04/¥2/¥8。高峰为北京时间工作日（法定节假日除外）09:00–12:00、14:00–18:00；其余为闲时。费率变化时必须更新快照，不能把费率当作永久常量。
3. API 密钥由本机仓库根目录 `.env` 中的 `DEEPSEEK_API_KEY` 提供，或通过同名 shell 环境变量提供。`.env` 已由 Git 忽略；跟踪的 `.env.example` 只含占位文本。密钥不得出现在 Git、命令输出、运行日志或聊天内容。

### 尚待运行时确认

最小 runtime probe 已确认响应 `model=deepseek-flash`，实际返回 token/cache usage 字段且没有 provider 字段；seed 支持、正式运行时版本仍未观测。官方文档说明默认开启思考模式；首轮 APP-001 是否显式关闭仍需负责人确认，且必须在云端配置与本地对照协议中清楚记录。此 ADR 不改变 ADR-0010 的共同解码设置，不授权正式模型评测。该待确认项由后续 ADR-0012 解决。

## ADR-0012：APP-001 首轮 DeepSeek 基线显式关闭思考模式

- 日期：2026-11-05
- 状态：accepted（首轮云端配置）
- 决策人：项目负责人 + Codex
- 关联：ADR-0010、ADR-0011；`docs/coordination/APP-001-baseline-contract.md`

### 决策

首轮 DeepSeek `deepseek-flash` 基线显式设置 `thinking: {"type":"disabled"}`。API 默认开启思考模式，因此每个请求必须发送该参数并将有效值写入运行记录，禁止依赖默认值。此选择固定云端基线配置；不把 DeepSeek 专属请求字段直接套用于 Ollama。本地 `qwen3:8b` 的运行模式应根据 Ollama 模板/运行配置核验并记录；若无法建立行为等价设置，清楚标注两模型的差别，不声称解码配置完全等价。seed 能力仍待探测，temperature/top_p/max token 等既有设置不变。

### 边界

本决策仅确定首轮思考模式，不冻结最终 Prompt/验收集，不构成 APP-001 正式运行放行，也不产生模型效果结论。

## ADR-0013：分离 LLM 显式参数抽取与 CAD-003 构造输入

- 日期：2026-11-05
- 状态：accepted
- 决策人：项目负责人 + Codex
- 关联：ADR-0009/0010/0012；`docs/coordination/APP-001-baseline-contract.md`

### 决策

模型输出只保存用户显式参数主张、证据、缺失字段、问题和不支持请求，不包含 `cad_parameters`。显式主张即使缺少必填字段、超出目录或与目录/阈值冲突，也必须保留在 `extracted_parameters` 中供抽取评分与审计；用户明确提出的 `second_screw` 主张同样保留，由确定性规则验证，未明确提供时再按规则派生。

适配器将模型原始响应独立保存，再将 `extracted_parameters` 投影为 CAD-003 严格输入并记录校验结果。只有 `decision=answer`、没有不支持请求且 CAD-003 校验通过时，才允许将结果传入 Typed CAD IR/CAD。追问/拒绝、unsupported 或校验失败都不进入几何构造。抽取指标、对话决策/安全指标、CAD-003 指标分层评分，不把目录派生字段记作模型抽取能力。

采用 `app001-io.v1`、`app001-extraction.v2` 和九条 evaluator-only `acceptance-set-v0`。Prompt 与验收标签经 Codex 中枢审查及项目负责人确认后冻结；正式评测仍需 adapter/logger 实现并审查，以及项目负责人另行授权。

### 原因

若用同一个 `cad_parameters` 字段同时表达模型抽取和可构造输入，缺少 `bore_d` 或存在显式冲突时只能置为 `null`，会丢失用户实际给出的字段，无法在失败/追问案例中独立评估抽取质量。分层后，原始主张可审计和评分，CAD-003 仍是构造前的确定性安全门。

### 影响与边界

- 旧 `prompt-v1.md` 与 `prompt-output-contract-v0.md` 仅作为未运行的历史候选保留；APP-001 使用 v2/v1 冻结协议。
- A01 只将用户明示的 `bore_d`、`outer_d`、`width` 作为模型抽取真值；目录/规则值在后处理阶段评估。
- 九条验收标签已冻结，但不得在正式评测门打开前调用模型或宣称测得任何性能结果。
- DeepSeek disabled thinking 与 Ollama `think=false` 是不同运行时控制；比较报告不得宣称二者完全等价。


## ADR-0014：APP-001 第一阶段正式运行授权路径

- 日期：2026-11-06
- 状态：accepted
- 决策人：项目负责人 + Codex（基于 APP-001-RUNNER-001 任务授权）
- 关联：ADR-0009、ADR-0010、ADR-0011、ADR-0012、ADR-0013

### 背景

APP-001-ADAPTER 已完成并通过中枢验收（`APP-001-ADAPTER-R3-FIX`）。适配器内的正式评测门 `FORMAL_EVALUATION_ALLOWED = False` 是一个模块级别的 `Final[bool]` 常量，在没有 ADR 的情况下不应更改。项目负责人授权了 APP-001 第一阶段评测，范围严格限定如下：

- 9 条冻结样例；条件 C0/C1；
- DeepSeek `deepseek-flash` 与 Ollama `qwen3:8b`；
- 36 个逻辑运行（9 × 2 条件 × 2 模型）；
- 每个逻辑运行最多 3 次实际尝试，全批次最多 108 次尝试，每 provider 最多 54 次；
- IR/CAD/geometry/STEP 明确禁用（`not_run`/`blocked`）。

### 决策

保留 `FORMAL_EVALUATION_ALLOWED = False` 不变。增加独立的窄范围 `FormalRunAuthorization` 数据类（`src/llm/authorization.py`），其构造时验证请求 scope 必须严格等于冻结的第一阶段 scope。只有当适配器的 `Adapter.run()` 接收到有效的 `FormalRunAuthorization` 实例时，才允许非 FakeTransport 执行；未持有有效授权时仍 fail-closed。

这种方式满足"提供显式、窄范围、可审查的授权路径"的要求，保持现有测试默认 fail-closed 行为不变，且不需要把全局 gate 改为 `True`。

### 授权范围（精确值，不可单独更改）

```
protocol_versions: {app001-io.v1, app001-extraction.v2}
sample_set: acceptance-set-v0
conditions: {C0, C1}
providers: {DeepSeek, Ollama}
models: {deepseek-flash, qwen3:8b}
max_logical_runs: 36
max_attempts_per_run: 3
max_batch_attempts: 108
max_provider_attempts: 54
ir_cad_geometry_step_disabled: True
```

### 实现文件

- `src/llm/authorization.py` — `FormalRunAuthorization`、`authorize_phase1_run()`
- `src/llm/budget.py` — 原子预算账本，每次调用前预留
- `src/llm/combinations.py` — 固定 36 组合生成器
- `src/llm/conditions.py` — C0/C1 输入组装（评估器标签隔离）
- `src/llm/real_transport.py` — DeepSeek/Ollama 真实 HTTP transport
- `src/llm/input_projection.py` — 验收集 allowlist 投影
- `src/llm/runner.py` — 受控批次 runner 入口
- `src/llm/adapter.py` — 修改：新增可选 `formal_authorization` 参数

### 边界

- `FORMAL_EVALUATION_ALLOWED = False` 未改变；gate 对未持有有效授权的调用仍 fail-closed。
- `FormalRunAuthorization` 不接受 C2、未冻结模型或额外条件——任何 scope 偏差引发 `AuthorizationScopeError`。
- 预算账本持久化到 `work/app001-runs/<batch-id>/budget_ledger.json`（git-ignored）；进程重启从账本恢复计数。
- 同批次并发运行通过排他锁文件拒绝。
- 真实 transport 在 `send()` 内才读取 `DEEPSEEK_API_KEY`，读后立即清除局部变量，不存储、不日志。
- 正式九样例评测在本 ADR 生效时尚未运行；本 ADR 只建立合法授权路径。

## ADR-0015：APP-001 本地 Ollama 运行时升级与冻结

- 日期：2026-11-07
- 状态：accepted
- 决策人：项目负责人 + Codex
- 关联：ADR-0010、ADR-0012、ADR-0014；`APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX`

### 决策

APP-001 后续本地基线使用 Homebrew formula 提供的 Ollama，不再使用旧的 Ollama.app 服务：

```text
distribution: Homebrew formula ollama
formula_version: 0.40.14
service: sh.brew.ollama
api_base: http://127.0.0.1:11434
api_version: 0.40.14
model: qwen3:8b
model_digest_prefix: 500a1f067a9f
model_digest_full: 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41
format_schema_version: ollama-app001-io-v1.0
format_schema_sha256: d82e53ad7de7676b5a63ac8cdbf276846a78201bec964d25d9771d9e775bb043
```

旧 Ollama.app 0.33.2 保留为历史环境证据，不再作为 APP-001 active local baseline。模型名称必须是唯一精确的 `qwen3:8b`，digest 必须匹配冻结前缀；更换发行来源、Ollama 版本、模型 digest、硬件或量化方式都必须重新建立环境记录并进入 review。

### 兼容性证据

2026-11-07 在本机对 `http://127.0.0.1:11434/api/chat` 完成一次无密钥、无正式批次、无 raw 落盘的 smoke：使用冻结 `prompt-v2.md`、`OLLAMA_FORMAT_SCHEMA`、`think=false`、固定解码参数和 `qwen3:8b`。HTTP 200，响应 `done=true`，返回完整九个 envelope 顶层键，`contract_version=app001-io.v1`、`prompt_version=app001-extraction.v2`，显式 `bore_d` 为 JSON integer 24。该证据证明 0.40.14 接受本项目的 Schema 对象 `format`；不构成模型质量指标或正式评测授权。

### 边界

- 三个既有正式批次保持只读，不回填、不重算、不混合统计。
- 本 ADR 不改变 `FormalRunAuthorization`、36 个逻辑运行、108 个物理 HTTP 上限或 C2/IR/CAD/STEP 禁用范围。
- 在 evidence `null` 契约偏差得到单独决策并完成中枢复核前，不启动新的正式批次。
- 旧 0.33.2 probe 只作历史对照；新的正式运行必须在本 ADR 冻结的服务、版本、模型和 Schema hash 下重新取得唯一批次授权。

## ADR-0016：APP-001 extraction v3 版本化激活（accepted / implementation review）

- 日期：2026-11-07
- 状态：accepted；允许执行生产 prompt 版本切换和离线验证，不包含真实模型评测授权
- 决策人：项目负责人 + Codex
- 关联：ADR-0013、ADR-0014、ADR-0015；`APP-001-DECISION-POLICY-V3-DRAFT`

### 背景

第四批次的只读分析发现，模型在缺失 `bore_d`、目录耦合冲突、目录外值和 `second_screw` 规则冲突时经常输出 `answer`。候选 v3 已在离线层补充冻结目录表、阈值规则、主张保留和不支持请求证据要求，并通过候选专项测试。该结果尚未证明真实模型效果，因此本 ADR 激活新版本以便后续受控评测，但不授权模型调用。

### 决策

将 `app001-extraction.v3` 激活为当前生产 prompt 版本，保持 `app001-io.v1`、九条 `acceptance-set-v0` 和 CAD-003 Schema 不变。激活包位于 `agent-work/llm/APP-001-v3-activation/`，包含 prompt 副本、哈希 manifest、激活检查清单和回滚说明。候选源文件保留原样；生产激活副本使用正式冻结措辞并单独锚定哈希。

候选包当前固定的可审查身份为：

```text
prompt_version: app001-extraction.v3
contract_version: app001-io.v1
acceptance_set: acceptance-set-v0 (9 cases)
cad_schema: set_screw_shaft_collar.v0
cad_source_commit: 035f467142888edfd0bd7cd73906f9b155c8f43c
status: activation implemented on feature branch; pending Codex review and merge
```

### 实施与验证条件

生产激活提交必须把 `contract.py` 的版本常量、`parser.py` 的版本检查、`prompt_loader.py` 的正式路径/版本/文件级 SHA-256 锚点和对应测试作为一个可回滚单元更新；不得修改旧批次或覆盖 v2 的历史哈希证据。必须在 Python 3.11.18 下重跑候选专项、LLM 全量和 Schema 全量测试，并由 Codex 独立复核。由于 `acceptance-set-v0` 的文件哈希被冻结且其 `frozen_prompt_version` 是创建时的历史元数据，本次不改该文件；运行记录仍由生产 `PROMPT_VERSION` 标识为 v3。

### 正式运行边界

本 ADR 不打开 `FORMAL_EVALUATION_ALLOWED`，不授权任何 DeepSeek/Ollama 请求，不改变 36 个逻辑运行、108 次物理 HTTP 上限、C2/IR/CAD/geometry/STEP 禁用范围。若激活后要测模型效果，必须使用新的唯一批次 ID，并取得与 ADR-0014 相同粒度的单独正式运行授权；旧 v2 批次只读保留，不混合统计。

### 回滚

若激活后发现协议、解析或运行记录不一致，回滚目标为 `app001-extraction.v2` 及其既有 `prompt-v2.md` 文件哈希锚点 `d95f853d325e05d9b045921da994256c7b8656336b5be02d75ced20d22755eac`。回滚不删除、不重写任何 v3 或旧批次证据。

### 当前结论

本 ADR 已被接受。激活提交只切换生产 prompt 版本和离线运行契约；真实模型效果仍未知，新的正式批次授权必须单独取得。
