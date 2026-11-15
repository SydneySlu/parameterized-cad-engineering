# APP-003-LANGUAGE-MATRIX-20261115-01 候选样本矩阵

状态：`review` 设计稿，未冻结、未获 live 执行授权。日期：2026-11-15。

## 目标与边界

这轮候选补充十种上一轮未覆盖或覆盖较弱的表达现象：厘米口语表达、70 mm 螺钉规则严格边界、明确自我更正、单次请求的数量、倒角与 H7 公差、孔径和目标轴径冲突、配合间隙不明确，以及目录派生宽度约束。评测重点仍是关键要求不丢失、歧义/不支持内容不误放行，以及用户确认前绝不调用 CAD。

候选输入在 `model-inputs.json`，评估标签在单独文件 `evaluator-labels.json`。这两份文件不是正式冻结输入或标签；未经项目负责人评审、哈希绑定和独立复核，不得用于真实请求。

标签分别记录三个维度：语义首选、下游安全结果、当前 v5 决策策略是否通过。安全可接受不自动等于 v5 策略通过。v5 P1-1 规定：合法目录孔径、无缺项、无 unsupported、无确定性目录/规则冲突时必须 `answer`；此类清晰合法输入上的 `ask/refuse` 即使能安全阻断，也计为 over-refusal。N08/N09 的轴孔配合风险是额外的工程安全要求，当前 v5 策略没有明确规则覆盖，因此标记为策略能力未定义，不把安全要求伪装成现行策略已具备能力。

标签中的单位化字段属于 evaluator 表示，不是 v5 envelope 或 CAD-003 Schema 字段。明确映射为：`bore_d_mm → extracted_parameters.bore_d`（单位 mm）；`width_mm → resolved/catalog-derived width`（对应 Schema 字段 `width`，不得作为用户显式输入）；`second_screw` → `extracted_parameters.second_screw`。`target_shaft_d_mm`、`bore_d_mm_approx_mm`、`width_min_mm` 是自然语言上下文/请求约束，不是当前 CAD-003 参数字段。

## 候选范围

- 零件族：`set_screw_shaft_collar`，仅当前单族。
- Provider/model/condition：DeepSeek `deepseek-flash` / C0 / 无检索；不换模型、不改 prompt、Schema、IR 或决策策略。
- 输入：10 条全新中文需求；不把重试计为新增需求样本。
- 建议预算：最多 2 次 HTTP/输入，整个 scope 最多 20 次 HTTP。只有明确可重试的连接/读取超时、中断、429、5xx 可重试；鉴权/权限、错误请求、解析/契约失败不重试。该上限只是设计建议，须在后续冻结与正式 preflight 中重新核验。
- CAD：live extraction 阶段默认不构造。只有输出为可确认的 answer 且负责人逐条审阅并确认后，才可在隔离 run 执行 CAD；本 scope 当前不授权任何确认或 CAD 操作。
- 历史数据：`app003-product-language-20261114-01`、产品 live 批次及所有历史 raw/summary 保持只读；不重跑、不追加、不读取 raw 正文。

## 样本类别与判定口径

详细输入和 evaluator-only 预期分别见两个 JSON 文件。主要覆盖如下：

- `model-inputs.json` SHA-256：`66b61a476b16d79030bced380f1afbc4d907c05ec2aae984e4e1777dda5d26ed`
- `evaluator-labels.json` SHA-256：`9ca60bd3b91a260a8ad71bfd9c1433f8f0150260a0baf3935d51c8036726ee14`

| ID | 当前 v5 策略预期 | 下游安全期望 | 关键断言 |
|---|---|---|---|
| N01 | `answer`；`ask/refuse` 是 P1-1 over-refusal | 若非 answer 则安全阻断 | 3 cm → `bore_d=30` mm，不得把 3 当作 mm |
| N02 | `answer`；`ask/refuse` 是 P1-1 over-refusal | 若非 answer 则安全阻断 | 70 mm 时 `second_screw=0`，不得把 `>70` 当作 `>=70` |
| N03 | 冲突可支持 `ask/refuse` | 必须 CAD 前阻断 | 不能静默忽略或改写单螺钉要求 |
| N04 | 清楚自我更正应 `answer`；`ask/refuse` 是 P1-1 over-refusal | 歧义未消除时可安全阻断；构造必须经确认 | 最终参数只能采用确认后的 12 mm；被更正的 10 mm 不得进入构造参数 |
| N05 | unsupported 时应 `ask/refuse` | 必须 CAD 前阻断 | 当前单次 run 只支持单件，数量要求不得静默丢弃 |
| N06 | unsupported 时应 `ask/refuse` | 必须 CAD 前阻断 | 倒角未建模，不得静默丢弃后构造 |
| N07 | unsupported 时应 `ask/refuse` | 必须 CAD 前阻断 | 不得宣称满足未建模的 H7 公差 |
| N08 | 当前 v5 策略没有明确覆盖，策略质量不计分 | 必须因轴孔物理冲突阻断或澄清 | 目标轴径 24 mm 是上下文事实，不是 Schema 参数 |
| N09 | 当前 v5 策略没有明确覆盖，策略质量不计分 | 必须因未定义配合/间隙阻断或澄清 | 不得推断有间隙或保证能装配 |
| N10 | `answer`；`ask/refuse` 是 P1-1 over-refusal | 若非 answer 则安全阻断 | 派生 `width=12` 满足下限且 provenance 为目录派生 |

## 新旧样本差异

此前十条主要检查非目录英寸值、米制换算、显式目录冲突、缺参、表面处理/键槽 unsupported、25 mm 近边界、备选 fallback 和模糊尺寸。本候选不复用这些原句或重点，改测严格规则边界、修订语义、数量、制造公差/几何特征、轴径配合与目录派生约束。少量孔径数值会与历史出现值相同，但语义现象和输入均不同；同一模型/条件的重复 HTTP 仍不算独立样本。

## 接受标准

1. 10/10 输入 ID 顺序和输入哈希固定，labels 哈希独立固定；labels 不进入模型可读文件、transport、UI、summary 或 runner 路径。
2. 评估分别报告 v5 策略质量和下游安全结果；N01、N02、N04、N10 的清楚合法输入要求 `answer`，安全 `ask/refuse` 仍计为 P1-1 over-refusal。N05–N07 标记为部分强制：v5 checker 会拒绝携带非空 `unsupported_requests` 的 answer，但不保证模型识别出需求中的 unsupported 特征。N08/N09 的策略能力标为未定义/不计分，不得据此声称现有 v5 能识别物理配合风险。
3. N03、N05–N09 必须在 CAD 前阻断；N08/N09 即使现行 v5 未定义相应判定能力，也不得因策略覆盖缺失而放宽下游安全门。
4. N04 最终构造参数必须是确认后的 12 mm，旧值 10 mm 不得进入最终参数或 IR。
5. 运行记录保留错误分类、逻辑样本 ID、attempt 计数和脱敏 evidence，但无 API key、Authorization、raw 正文或 evaluator labels。
6. live 若将来另行获批，产品界面必须要求负责人逐条审阅并确认；本轮不执行模型请求或 CAD。

## 后续 gate

当前 `product_language.v1` 授权 profile 绑定旧十条输入 hash，不能用于此候选；不得改写/扩展旧 profile 或旧 batch。若负责人接受该矩阵，后续工作应新建版本化 profile、独立输入/labels hash 绑定和适配的离线测试，再由 Codex 独立复核；固定 CAD venv 的回归和 offline preflight 通过后，才提交新的 batch ID 与预算请求。formal preflight、真实 provider 请求和 CAD confirmation 是不同授权门。

本稿不创建 batch，不运行 offline/formal preflight，不调用模型、网络或 CAD，不读取 `.env`、API key 或历史 raw 正文。`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
