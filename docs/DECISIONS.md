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

## ADR-0016：APP-001 extraction v3 版本化激活（accepted / implemented）

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
status: activation merged to main and independently reviewed (`7dc7a37`)
```

### 实施与验证条件

生产激活提交必须把 `contract.py` 的版本常量、`parser.py` 的版本检查、`prompt_loader.py` 的正式路径/版本/文件级 SHA-256 锚点和对应测试作为一个可回滚单元更新；不得修改旧批次或覆盖 v2 的历史哈希证据。必须在 Python 3.11.18 下重跑候选专项、LLM 全量和 Schema 全量测试，并由 Codex 独立复核。由于 `acceptance-set-v0` 的文件哈希被冻结且其 `frozen_prompt_version` 是创建时的历史元数据，本次不改该文件；运行记录仍由生产 `PROMPT_VERSION` 标识为 v3。

### 正式运行边界

本 ADR 不打开 `FORMAL_EVALUATION_ALLOWED`，不授权任何 DeepSeek/Ollama 请求，不改变 36 个逻辑运行、108 次物理 HTTP 上限、C2/IR/CAD/geometry/STEP 禁用范围。若激活后要测模型效果，必须使用新的唯一批次 ID，并取得与 ADR-0014 相同粒度的单独正式运行授权；旧 v2 批次只读保留，不混合统计。

### 回滚

若激活后发现协议、解析或运行记录不一致，回滚目标为 `app001-extraction.v2` 及其既有 `prompt-v2.md` 文件哈希锚点 `d95f853d325e05d9b045921da994256c7b8656336b5be02d75ced20d22755eac`。回滚不删除、不重写任何 v3 或旧批次证据。

### 当前结论

本 ADR 已被接受。激活提交只切换生产 prompt 版本和离线运行契约；真实模型效果仍未知，新的正式批次授权必须单独取得。

## ADR-0017：APP-001 extraction v4 决策修正候选（accepted）

- 日期：2026-11-07
- 接受日期：2026-11-08
- 状态：accepted；项目负责人已批准策略方向；允许执行 v4 版本化激活实现和离线验证，不包含真实模型评测授权
- 决策人：Codex 中枢提出，项目负责人批准策略方向；激活实现由 CC 完成，Codex 中枢独立审查后已合并到 `main`（`c18fd35`）
- 关联：ADR-0013、ADR-0016；`APP-001-PHASE1-V3-20261107-01`

### 背景

v3 正式批次的字段抽取与解析契约通过，但 Ollama 在 A03 单位换算样例两次误拒绝，在 A08 C1 对明确用户值多问一次，且 A07 将 `anodizing` 输出为词形变体 `anodized`。独立审查见 `agent-work/reviews/APP-001-phase1-v3-20261107-01-codex-review.md`。

### 提议

建立 `app001-extraction.v4` 候选，只修正三类策略说明：可精确换算的 1.6 cm→16 mm 不应误拒绝；不可信 retrieval example 不应覆盖用户明确的 bore_d=24；unsupported 项使用稳定规范标签 `anodizing`，但证据 quote 保留原文。v4 候选保留 v3 的目录、安全 decision gate、字段抽取、Schema、接口和构造边界。

冻结的 `acceptance-set-v0`、生产 v3 prompt、prompt hash、parser、adapter、runner、授权和预算均不修改。离线测试只验证候选文本与规格，不证明真实模型依从性。

### 提议边界

- 本 ADR 被接受前，v4 不得成为生产版本；正式路径继续使用 `app001-extraction.v3`。
- 激活需独立实现/审查单元，完整更新版本常量、解析器、prompt loader 哈希与路径、manifest 和兼容性测试。
- 真实模型效果验证必须使用新的唯一正式批次，并由项目负责人另行明确授权。
- 不修改或回填历史 v2/v3 批次，不运行 C2、IR、CAD、geometry 或 STEP。

### 当前结论

本 ADR 已被项目负责人批准（策略方向）。CC 已完成激活实现单元，Codex 中枢已完成独立审查并将其合入 `main`（`c18fd35`）；版本常量、parser 版本校验、prompt loader 路径/哈希锚点和兼容性测试作为原子单元保留；v2/v3 历史只读审计路径保留；`FORMAL_EVALUATION_ALLOWED` 仍为 `False`。本 ADR 不包含真实模型评测授权，v4 效果仍需新的唯一批次和单独授权。

## ADR-0015-CLOSEOUT：evidence `null` 契约门关闭记录

- 日期：2026-11-08
- 状态：closed；仅关闭 ADR-0015 的前置决策门，不授权新的正式批次
- 依据：`APP-001-EVIDENCE-CONTRACT-FIX`，commit `352ef8a`；中枢独立审查 `agent-work/reviews/APP-001-EVIDENCE-CONTRACT-FIX-codex-review.md`
- 关联：ADR-0015、ADR-0017；`APP-001-EVIDENCE-CONTRACT-FIX`

### 结论

`app001-io.v1` 的 evidence 契约要求 `field`、`quote`、`source` 为字符串。此前 parser 对显式 JSON `null` 使用了可选值守护，导致实现行为比已冻结 Ollama Schema 更宽松。`src/llm/parser.py` 已在 `352ef8a` 中移除该守护；三个字段的显式 `null` 现在统一返回 `EVIDENCE_FIELD_TYPE_ERROR`，合法字符串和空 evidence 数组保持通过，非枚举字符串 `source` 仍返回 `EVIDENCE_SOURCE_INVALID`。

中枢已在 Python 3.11.18 下复核定向 parser/R1/provider 测试（119 项）、LLM 全量（499 项，通过，8 项既有 FUSE skip）、Schema 全量（17 项）、编译检查和空白检查。该修复未改变 prompt、Ollama Schema、adapter、runner、预算、授权 scope 或任何正式批次。

### 边界

本记录只关闭“evidence `null` 行为与 Schema 不一致”的文档决策门。它不等同于正式运行授权，不打开 `FORMAL_EVALUATION_ALLOWED`，不改变 36 个逻辑运行、108 次物理请求、provider 上限、C2/IR/CAD/geometry/STEP 禁用范围，也不允许修改或混合旧批次。

## ADR-0014-AMENDMENT：当前 v4 运行继承 scope 同步记录

- 日期：2026-11-08
- 状态：synchronized；不是新的正式运行授权
- 依据：当前 `main` 的 `src/llm/authorization.py`、`src/llm/contract.py`、v4 激活包和 `APP-001-V4-FORMAL-RUN-READINESS`
- 关联：ADR-0014、ADR-0016、ADR-0017、ADR-0015

### 目的

ADR-0014 原始授权表保留 `app001-extraction.v2`，作为当时授权和历史批次的不可改写证据。v3、v4 激活均要求新批次和单独授权，因此不修改该历史表。当前授权工厂从生产 `PROMPT_VERSION` 动态读取协议版本；在 v4 已合入 `main` 后，任何新的授权申请实际继承以下同一窄范围边界：

```text
protocol_versions: {app001-io.v1, app001-extraction.v4}
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

### 边界

这是一条当前代码与冻结激活版本的事实同步，不构成 batch_id 批准、模型调用批准或任何旧批次重跑批准。新的正式运行仍必须使用新的唯一 `batch_id`，由项目负责人填写并明确批准授权模板；执行前仍需通过 Codex final preflight。旧 v2/v3 批次继续只读，统计不得与 v4 混合。

## ADR-0018：APP-001 extraction v5 策略与激活（accepted）

- 日期：2026-11-11
- 状态：accepted；项目负责人于 2026-11-11 接受策略方向。激活实现仍需独立审查并合入 main；未授权真实模型评测
- 决策人：项目负责人（Wang sikai）
- 关联：ADR-0013、ADR-0014、ADR-0017；`APP-001-V5-PROMPT-CANDIDATE`；`APP-001-V5-ACTIVATION-PREP`
- 候选材料：`agent-work/llm/APP-001-v5-prompt-candidate/`；激活准备副本：`agent-work/llm/APP-001-v5-activation-prep/`

### 背景

v4 唯一正式效果批次 `app001-phase1-v4-20261109-01` 的独立审查发现 3 条完整、无冲突输入被 Ollama 误拒绝（A02 C1、A03 C0、A08 C1），以及 DeepSeek A05 C0/C1 将 `outer_d` 同时列入 `extracted_parameters` 和 `missing_fields`。离线 v5 checker/prompt 候选已针对这些行为准备并通过独立离线审查；这不构成模型效果结论。

### 决策

项目负责人接受将 `app001-extraction.v5` 作为新的生产 prompt 策略版本。策略仅明确：完整、目录有效、无缺失/unsupported/显式目录或规则冲突时，C0/C1 均应 `answer`，retrieval 不能创建或覆盖用户意图；并强化 envelope 字段互斥、缺失字段去重及 answer 自洽规则。保留 v4 的九键 `app001-io.v1` 契约、显式主张/证据规则、目录边界、不支持请求拒绝、冲突保留和 CAD-003 最终校验。

### 边界

- 项目负责人已接受策略方向；生产切换仍须由独立工作单元原子更新 `contract.py`、parser 版本检查、prompt-loader 路径/版本/hash 锚点、激活 manifest 和兼容测试，并经 Codex 中枢独立复核后合入 `main`。
- 接受策略方向或完成离线激活均不等于真实效果已验证；`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
- 不修改冻结 `acceptance-set-v0`、CAD-003 Schema、预算、授权逻辑、旧批次或历史 prompt。C2、IR/CAD/geometry/STEP 保持禁用。
- 本 ADR 不授权任何模型请求。若激活后需验证效果，必须使用新的唯一 `batch_id`、单独明确授权并通过 Codex final preflight；旧批次只读且不得与 v5 结果混合。

### 实施状态

项目负责人已接受策略方向。v5 激活实现作为独立工作单元进行，尚待 Codex 中枢审查并合入 `main`。不授权模型调用或正式批次；模型效果评测须使用新的唯一 `batch_id`、另行明确授权并通过 Codex final preflight。候选、激活 prompt、验收集和 v4 回滚哈希记录于版本化 manifest。

## ADR-0019：APP-001 held-out v5 检索对照的输入与授权 scope

- 日期：2026-11-11
- 状态：accepted（方案、预算口径与实现边界；不授权模型请求）
- 决策人：项目负责人 + Codex
- 关联任务：APP-001-NEXT-REAL-MODEL-EVALUATION；RET-003

### 决策

1. 本轮仅评估 RET-003 的三个 held-out 查询（`catalog-bore-012/035/080`），比较同一模型可见自然语言输入下 C0 与 C1 的 APP-001 v5 输出及确定性 CAD-003 Schema 结果；逐例描述，保留 `provisional_small_n` 限制。
2. 模型输入使用固定模板“请按 GN 705 做一个轴环，轴孔 bore_d=<值> mm。”只显式提供该 held-out 查询的 `bore_d`。本轮输入是受控合成评测刺激，不宣称为历史真实用户原话。模型可见 query ID 使用不含数值的 `APP001-HO-01/02/03`。输入文件与 evaluator-only 标签分离：`model-inputs.json` SHA-256 `c00ef6dce6b227368b3bfb63a91bbf7362316f64796834a045c5fea536dc83a6`；`evaluator-labels.json` SHA-256 `bfe94d89d2809634b9e52cb73c9f4733fee30a7b7130a65ef9e13c33545cc35a`。标签含 held-out 样本映射、显式主张和完整 CAD-003 预期参数；标签不得进入 prompt、检索 query、请求日志或模型可见对象。
3. 唯一计划 scope 为 3 查询 × C0/C1 × DeepSeek `deepseek-flash` / Ollama `qwen3:8b` = 12 逻辑运行；每运行最多 3 次尝试，全批最多 36 次、每 provider 最多 18 次。C1 只允许冻结 RET-002 `retrieval_source` 候选。C2/C2O、IR/CAD/geometry/STEP 禁用。旧批次只读且不混合。
4. 不修改 ADR-0014 所定义的现有 9-case/36-run 授权。新增 scope 必须使用单独、显式、fail-closed 的授权 profile/factory 和受控入口；授权必须绑定新 batch ID、输入/labels hash、v5 prompt/契约版本和上述精确预算。未匹配时在任何模型请求前拒绝。`FORMAL_EVALUATION_ALLOWED` 保持 `False`。
5. 本 ADR 接受实验协议与实现边界，不等于批准真实请求。实现、Python 3.11.18 验证、独立审查和 Codex final preflight 全部通过后，仍须由项目负责人审阅新 batch ID 与完整授权模板并单独批准，随后才可运行。

### 原因

RET-003 held-out 清单只提供结构化真值引用，并未提供冻结自然语言请求；将真值直接改写成 query 会让输入生成过程不透明。显式、固定、可审计的模板使本轮仅测试已声明 bore selector 的抽取以及 retrieval-context 的影响，同时通过中性 ID 和物理分离标签降低评测者真值泄漏。现有 `FormalRunAuthorization` 和组合生成器固定于 acceptance-set-v0/36-run scope，不能安全复用或绕过；新增独立 profile 保持旧授权语义不变。

### 限制

本轮只有三个受控合成输入，且输入只包含 bore_d。结论仅描述这三例在固定 provider/model、prompt 和检索配置下的输出差异，不代表自然用户语言分布、统计泛化、跨族能力或广泛模型质量；更不表示 CAD 构造、几何、STEP 或用户效用通过。完整 held-out 参数只供 evaluator 评分使用。

### 实施预算口径补充（2026-11-11）

项目负责人接受以下按物理 HTTP 请求审计、按请求用途分别设硬上限的预算。授权计数不得排除 Ollama 身份请求：

- chat 请求：最多 36 次，全局；DeepSeek 最多 18 次、Ollama 最多 18 次；每个逻辑运行最多 3 次 chat 尝试（保留现有重试策略）。
- 身份请求：最多 20 次，全局，全部归属 Ollama；其中批次 preflight 的 `/api/version` 与 `/api/tags` 各最多 1 次，运行时 `/api/tags` 最多 18 次（6 个 Ollama logical run × 最多 3 次 transport attempt；跨所有运行累计）。失败的身份请求和对身份端点的重试也计入额度；不能通过重试或换 logical_run_id 重置上限。
- 因此所有物理 HTTP 请求总上限为 44；DeepSeek provider 总上限为 18，Ollama provider 总上限为 26。任何 category、provider 或全局上限先耗尽时均须 fail closed。
- 每一物理请求都必须先取得授权绑定的持久账本 reservation，再执行网络 I/O；账本记录 endpoint、provider、请求类别、logical_run_id（preflight 使用固定 batch-level ID）和结果。Preflight 请求属于获批批次预算，但只有用户批准该 batch 的完整授权模板后才可发送。

该预算精确覆盖本 ADR 的 12-run 矩阵与既有每运行最多 3 次 transport attempt。Ollama 运行时身份检查在首个 chat 前执行；若 tags 失败，现有 retry loop 会在后续 attempt 再试 tags，因此 identity category cap 需允许最多 18 次 runtime tags。每个 Ollama run 的物理请求数仍最多 4（最多 3 次 tags attempt，其中成功的 tags 可与该次 attempt 的一次 chat 同时发生，或一次 tags 成功加最多 3 次 chat）；所以 6 个 Ollama run 最多 24 次，另加两次 batch preflight 为 26。全局最多 44 次（DeepSeek 最多 18 + Ollama 最多 26）。identity 20 与 chat 36 是分类上限，provider 和全局上限共同约束，不能把分类上限简单相加当作可用总额。该设计不增加逻辑运行、chat 次数或重试次数。实现必须使用独立、fail-closed 的 v5 held-out 授权 profile/入口，保持 ADR-0014 的 9-case/36-run 授权逻辑不变。实现和离线审查通过前不分配正式 `batch_id`；用户批准具体 batch 授权前不发送任何网络请求。

## ADR-0020：冻结 v5 集成基线，优先交付单族自然语言到 STEP 闭环

- 日期：2026-11-11
- 状态：accepted
- 决策人：项目负责人（本轮明确确认推进方向）+ Codex 中枢
- 关联：ADR-0007/0008/0013/0018/0019；APP-002-INTEGRATION-A1

### 决策与推进顺序

1. 下一阶段优先交付自然语言→v5 抽取/决策→CAD-003 Schema→确定性 Typed CAD IR→白名单 CadQuery→几何验证→STEP，再做最小产品包装。复用已审查的单族 Schema、IR v0.2.0、CAD-005/006 和 RET-001 的 15 行构造证据，不重新建设后端。
2. 当前 `app001-extraction.v5`、`app001-io.v1` 和冻结 prompt/hash 作为首个整链集成基线。已有代表性合法/单位/边界及缺失/冲突/不支持路径证据足以开始集成，不要求先证明某配置在所有实验中最佳；一般优化意见不自动启动 v6。真实整链优先沿用已审查 DeepSeek `deepseek-flash` 配置及解码设置，Qwen 保留为后续兼容路径，不擅自换模型。
3. 里程碑 A：先交付离线合成 envelope 到真实本地 CAD/STEP 的统一入口、严格构造门与正式参数→IR adapter（A1），再接受控真实模型输入（A2）。A1 保存需求、抽取、原始主张、规范参数及来源、IR、验证与产物对应关系；合成提取明确标记为 fixture，不能称为真实自然语言理解。模型不生成或执行任意 Python。
4. 里程碑 B：最小整链验收覆盖合法目录、单位换算、第二螺钉边界、缺参、显式冲突和 CAD/导出失败；只有完成本次运行 STEP 导出、回读和几何比较才报告成功。ask/refuse、missing_fields、unsupported、解析/Schema/IR 失败均停止构造；失败不返回其他运行的旧文件。复用已有模块测试与 15 行后端回归，只补缺失的连接层验证。
5. 里程碑 C：最小演示提供需求输入、参数及必要确认、构造状态与失败原因、结果文件获取、修改后重新生成；先保证真实生成和运行隔离，再完善三维预览和界面。下周导师汇报以合法/边界成功和非法/不完整阻断、参数/IR/验证可查为目标，未完成前明确区分模块与整链演示。
6. ADR-0019 的 12-run 检索对照保留为独立研究，真实执行设为 `deferred`，不再是 CAD 集成前置门。final offline preflight 已在 `993a5b1` 通过；恢复条件是主闭环完成或出现明确研究假设，由中枢重验当前基线并取得具体 batch 的单独授权。研究回答额外上下文是否有收益，整链回答能否完成任务；分别报告，不预设检索正收益。

### 冻结、证据和授权边界

- 错误几何、关键参数丢失、错误放行、错误报告成功属于交付阻断，须复现并修复。非关键措辞、额外语言覆盖、指标小幅波动和新对照设想进入后续清单，不自动阻断主闭环。确需改变冻结策略或接口时另走版本化和 ADR，不静默修改。
- 当前 15 行是冻结单族全部合法目录配置，不是 15 条语言训练样本；九案例的条件/模型重复运行也不是同等数量的独立需求。语言覆盖、运行稳定性与跨族扩展分别验证，均不得由目录覆盖推断。
- 本轮只授权规划、离线集成实现与本地模块验证；真实模型 CAD 整链须单独冻结输入、预算、batch ID、受控入口及授权。既有仅到 Schema 的授权及 ADR-0019 不扩展到 IR/CAD；旧 runner 边界和 `FORMAL_EVALUATION_ALLOWED=False` 保持原样。A2 必须建立自己的受控执行范围。
- 历史批次只读，未经另行许可不读取 raw 正文；不得移动、改写、重跑或混合统计。本轮使用合成夹具，不复用历史响应冒充新执行。
- 保留单族、固定环境、来源/许可证及螺纹环形近似限制；几何和 STEP 通过不等于制造认证。新族、稳定性与语言泛化是独立后续验证，不作为当前已完成事实。

### 责任与验收

CC 负责 A1 连接层实现，中枢负责接口核对与独立验收。Schema→IR→编译器为高风险交接，执行三层协议和正常/失败 double check。首个工作包见 `docs/coordination/prompts/APP-002-INTEGRATION-A1-cc.md`，本轮资产与离线关口证据见 `agent-work/reviews/APP-001-V5-INTEGRATION-BASELINE-preflight.md`。

## ADR-0021：A2 真实模型整链测试的专用授权门与批次状态

- 日期：2026-11-12
- 状态：accepted
- 决策人：项目负责人 + Codex 中枢（负责人明确要求打开测试所需权限和 gate）
- 关联：ADR-0014、ADR-0020、APP-002-INTEGRATION-A2-SCOPE

### 决策

1. 为 A2 保持独立且窄范围的真实模型整链授权：只能使用 `A2IntegrationAuthorization` 与同 batch 的、非 test-only `A2FormalApproval`；固定输入、prompt/contract、DeepSeek `deepseek-flash`、C0、3 条输入、最多 3 次每输入尝试、全批次最多 9 次 HTTP，并仅在 `answer` 且确定性校验通过时进入既有 CAD pipeline。
2. Adapter 继续使用现有 `FormalRunAuthorization` 类型检查和 runner-bound `BudgetAwareTransport` 校验。A2 子类凭证是 A2 的显式窄门；不改变、不 monkey-patch、不以环境变量覆盖 `FORMAL_EVALUATION_ALLOWED=False`。APP-001 与 held-out 入口不因此获得新的权限。
3. 每个 A2 Adapter run ID 必须与同一 transport 的 `adapter_run_id` 一致，transport 的 logical run、query、condition、provider、model 仍由账本与 A2 scope 绑定；所有真实 HTTP 继续先 reserve 预算。
4. 批次摘要的 `batch_status=complete` 仅用于全部计划运行均到达非错误终态（包括预期 ask/refuse/blocked）；若所有结果均为 `error`/`failed`，状态为 `failed`；部分混合错误为 `partial`；未完成计划即中止时为 `aborted`。摘要写失败仍通过既有错误字段报告，不伪称完成。
5. 此 ADR 打开的是受控 A2 授权机制，不是对旧批次或新 batch 的执行批准。已使用的 `...-01`、`...-02` 永久保留且禁止重跑；任何后续 live preflight/model/CAD 请求都必须使用新唯一 batch ID，并在固定环境离线验证与独立复核通过后，取得项目负责人对该 batch、输入、预算和整链执行的明确批准。

### 原因与验证要求

第二个获批尝试在 HTTP=0 时被 Adapter 拒绝。代码条件表明 transport 的 `adapter_run_id` 绑定逻辑运行 ID，而 A2 helper 生成随机 Adapter run ID，造成合法 A2 凭证与 transport binding 不一致；不需要打开全局布尔 gate。该失败也暴露出全错误批次被标记为 `complete` 的报告缺陷。

修改必须以正反回归验证 ID 绑定和 summary 状态：A2 正式 mock/spy 路径能通过 scope/binding 检查，错误绑定仍拒绝；三条 error 结果不得 finalize 为 complete，ask 等有效终态仍可 complete。`FORMAL_EVALUATION_ALLOWED` 保持 False。实施和中枢复核通过后，才进入新的 batch 授权步骤。

## ADR-0022：APP-003 首个本地 CAD 演示的运行边界

- 日期：2026-11-12
- 状态：accepted（首个本地演示工作单元边界；不授权 live 模型请求）
- 决策人：Codex 中枢，依据项目负责人对里程碑 C 的推进确认及 ADR-0020 已接受的界面实现授权
- 关联：ADR-0020；APP-003

### 决策

1. 首个演示切片使用 Python 标准库提供仅监听 `127.0.0.1` 的本地 Web UI，不新增运行时依赖；调用现有 schema/IR/CAD pipeline，不重写 CAD 后端。
2. UI 提供自然语言需求文本记录、结构化参数输入/确认、构造状态和错误、IR/验证证据查看、STEP 下载及修改参数后再次生成。首次切片中的参数由用户显式填写；自然语言文本仅作为需求记录与产物追溯信息，不能宣称由模型解析。
3. 首次切片不接入真实模型 transport、不读取 `.env`/API key、不复用 A2 已消耗批次或响应，不产生模型/网络请求。界面须清楚标记本次采用“手动参数 / 离线 CAD 生成”；真实自然语言抽取入口需另行定义产品运行授权、预算和安全策略，并单独批准。
4. 每次生成使用不可预测的新 run ID 和独立目录。只有本次 run 的 compiler manifest、几何验证、STEP 导出、readback comparison 全部通过，才显示成功并开放该次 STEP。失败不得显示或返回此前运行的 STEP。
5. 结果视图展示参数值及来源、IR、验证摘要与文件状态；保留单族、固定环境、几何/STEP 不构成制造认证等限制。真实三维预览与部署暂不纳入首个切片。

### 验收边界

- 代表性目录参数输入可以通过本地浏览器生成真实 STEP 并下载；缺少 bore 参数时明确提示并不调用 CAD。
- 提交目录冲突或无效参数时显示可定位错误，不发布 STEP。
- 修改参数再生成产生新的隔离 run；先成功后失败时，失败 run 不得暴露前一 run 的 STEP。
- 请求文本、用户显式参数、目录/规则派生参数、IR、验证结果和 STEP 均可追溯到对应 run。
- 自动化测试通过固定 CAD venv 执行；整个实现与验收不发起模型或外网请求。

## ADR-0023：APP-003-C2 自然语言产品闭环与离线确认流程

- 日期：2026-11-13
- 状态：accepted（产品流程设计与离线实现边界；不授权真实模型请求）
- 决策人：项目负责人 + Codex 中枢
- 关联：ADR-0020、ADR-0021、ADR-0022；APP-003-C2

### 目的与范围

C1 已证明“手动参数→确定性 CAD→STEP”的本地演示。C2 将产品入口推进到“自然语言需求→v5 抽取/决策→用户确认或补充→Schema→Typed CAD IR→CadQuery→几何验证/STEP→下载”，但首个实现只使用明确标记的离线 v5 envelope 夹具。夹具用于验证状态机、确认边界、证据关联和失败保护，不构成模型理解证据。C1 的手动参数入口保持可用并继续作为独立演示。

本 ADR 不修改 v5 prompt、`app001-io.v1`、Schema、IR、编译器、现有 C1 API 语义或 A2 历史批次；不读取 `.env`/API key，不发起模型或外网请求，不创建 batch，也不打开 `FORMAL_EVALUATION_ALLOWED`。真实产品模型入口须另立 scope、预算、独立 product gate、preflight、batch ID 和负责人批准。

### 产品状态机

产品状态与 `run_pipeline` 的 `success/ask/refuse/blocked/failed/error` 保持分层。内部状态不改名、不回填历史记录，产品响应同时保留内部 `pipeline_status` 和 `pipeline_stage`。

```text
request_received → extraction_pending
extraction_pending → needs_confirmation | blocked | failed
needs_confirmation → constructing | blocked
constructing → succeeded | failed
```

- `needs_confirmation`：`decision=ask`、缺少关键参数、可由用户补充的 `questions`，或需要用户确认/修改的合法候选。
- `blocked`：`refuse`、`unsupported_requests`、不可修复的目录/规则冲突、解析/契约失败、确认拒绝或确认版本过期。此状态不调用 CAD。
- `failed`：Schema/IR/CadQuery/STEP/回读或运行基础设施故障。此状态不发布 STEP，也不复用其他 run 的产物。
- `succeeded`：仅当本 run 的 Schema、IR、编译、几何验证、STEP 导出和回读全部通过。

确认前可以做 envelope 解析、投影、Schema/规则预检，用于展示参数来源、缺参和冲突；确认前绝不调用 IR 编译器或 CAD。确认或用户修改后必须从原始 envelope 重新构造最终输入并完整重跑校验。

### 最小记录契约

每个产品 run 必须有新的 UUID `run_id`、独立目录和可选 `parent_run_id`。用户修改或重新确认创建新的 run，不覆盖旧记录；`confirmation_revision` 从 0 开始递增。记录至少包含：

```text
run_id, parent_run_id, confirmation_revision, created_at
request_text, extraction_source, envelope_fixture_label
raw_envelope (或 repo-relative path + sha256), decision
extracted_parameters
user_explicit_parameters
catalog_derived_parameters
rule_derived_parameters
missing_fields, unsupported_requests, questions, conflicts
confirmation: {required, confirmed, actor, confirmed_at, patch, revision}
pipeline_status, pipeline_stage
schema_result, ir_document, validation_summary
step: {repo_relative_path, sha256, bytes} | null
errors
```

`extracted_parameters` 保留 v5 原始主张；不得把用户修改直接写回原始 envelope。用户修改字段在最终参数中标记为 `user_explicit`，仍须通过既有 Schema/目录规则；修改目录派生值造成冲突时返回 `blocked`，不能静默覆盖派生规则。目录派生值和规则派生值只读展示。摘要只保存相对路径和 hash，不保存 API key、Authorization header 或 evaluator-only 标签；raw 正文遵守既有 retention policy。

### 最小接口语义

实现可以沿用标准库 localhost server，但必须提供等价的三个操作，且不破坏 C1 现有 `/api/generate` 与下载语义：

1. `create_product_run(request_text, fixture_id)`：创建 `request_received/extraction_pending` run，离线读取已登记的 synthetic fixture，返回 `run_id`、产品状态、decision、参数来源、questions/conflicts 和 `confirmation_revision`。
2. `confirm_product_run(run_id, confirmation_revision, confirmed, patch)`：只接受当前 revision；`confirmed=false` 或 patch 校验失败返回 `blocked`/`needs_confirmation`，不调用 CAD。合法确认或修改创建 child run，进入 `constructing` 后调用现有确定性 pipeline。
3. `get_product_run(run_id)` / `download_product_step(run_id)`：只返回该 run 的状态与证据；下载必须复用 C1 的 UUID、注册表、canonical containment、symlink 拒绝和 SHA-256 校验。

HTTP JSON 字段应与上述记录契约同名或提供明确映射。服务端持有所有 transport/fixture 访问权；浏览器只提交需求和确认 patch，绝不接触 key 或 provider 凭证。

### 离线验收边界

CC 必须用固定 synthetic fixtures 覆盖：合法 answer、缺 `bore_d`、目录/规则冲突、unsupported、`decision=ask`、`decision=refuse`、Schema/IR 失败、CadQuery/STEP 导出失败，以及用户修改后新 run 隔离。每个阻断/失败案例都要断言 CAD 编译器未调用、没有 STEP 发布、没有返回旧 run 文件；合法确认必须在固定 CAD venv 生成真实 STEP。离线测试不读取 `.env`、不发网络、不调用 LLM。

### 后续 live 接入条件

离线 C2 与独立复核通过后，才准备新的产品 live smoke scope（建议正常、缺参、冲突/非法各一条）。该 scope 不继承 A2 的批准或预算，必须绑定新的输入/prompt/contract hash、预算、product gate、batch ID 和负责人授权；`FORMAL_EVALUATION_ALLOWED=False` 继续保持。
