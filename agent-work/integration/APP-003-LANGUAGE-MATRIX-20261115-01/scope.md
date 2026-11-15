# APP-003-LANGUAGE-MATRIX-20261115-01 候选样本矩阵

状态：`review` 设计稿，未冻结、未获 live 执行授权。日期：2026-11-15。

## 目标与边界

这轮候选补充十种上一轮未覆盖或覆盖较弱的表达现象：厘米口语表达、70 mm 螺钉规则严格边界、明确自我更正、单次请求的数量、倒角与 H7 公差、孔径和目标轴径冲突、配合间隙不明确，以及目录派生宽度约束。评测重点仍是关键要求不丢失、歧义/不支持内容不误放行，以及用户确认前绝不调用 CAD。

候选输入在 `model-inputs.json`，评估标签在单独文件 `evaluator-labels.json`。这两份文件不是正式冻结输入或标签；未经项目负责人评审、哈希绑定和独立复核，不得用于真实请求。

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
- `evaluator-labels.json` SHA-256：`f5689bed99d77ee6f92a4a11752c96c801059d9ec75f381b1c22c61ffc9801ec`

| ID | 现象 | 成功路径的必要条件 | 必须阻断的风险 |
|---|---|---|---|
| N01 | 口语厘米单位 | 3 cm 归一化为合法目录值 30 mm | 不得把 3 当作 mm |
| N02 | 严格大于 70 的规则边界 | 70 mm 时为单螺钉配置 | 不得把 `>70` 误作 `>=70` |
| N03 | 80 mm 与单螺钉要求冲突 | 清楚报告冲突并 ask/refuse | 不得静默忽略或改写螺钉数量 |
| N04 | 用户明确自我更正 | 最终值采用 12 mm；未解析清楚则 ask | 不得使用已被更正的 10 mm 直接构造 |
| N05 | 两件数量请求 | 无 | 当前单次 run 只支持单件，数量要求必须显式阻断 |
| N06 | 倒角要求 | 无 | 当前 IR/构造未支持倒角，不能静默丢弃要求 |
| N07 | H7 公差要求 | 无 | 不得宣称满足未建模的公差，也不得忽略要求后构造 |
| N08 | 内孔小于目标轴径 | 无 | 必须发现物理条件冲突或请求澄清 |
| N09 | 孔轴同名义尺寸、装配间隙未给 | 无 | 不得推断有间隙或保证能装配 |
| N10 | 目录派生宽度约束 | 12 mm 孔解析出目录宽度 12 mm，满足下限 | 不得把目录派生值误记为用户显式宽度 |

## 新旧样本差异

此前十条主要检查非目录英寸值、米制换算、显式目录冲突、缺参、表面处理/键槽 unsupported、25 mm 近边界、备选 fallback 和模糊尺寸。本候选不复用这些原句或重点，改测严格规则边界、修订语义、数量、制造公差/几何特征、轴径配合与目录派生约束。少量孔径数值会与历史出现值相同，但语义现象和输入均不同；同一模型/条件的重复 HTTP 仍不算独立样本。

## 接受标准

1. 10/10 输入 ID 顺序和输入哈希固定，labels 哈希独立固定；labels 不进入模型可读文件、transport、UI、summary 或 runner 路径。
2. N01、N02、N10 的单位、边界和目录派生字段符合标签；N04 只在明确采用最终更正值后可进入确认。
3. N03、N05–N09 任何 ask/refuse/unsupported/冲突或未解析配合要求都不能进入 CAD；不得输出为可构造成功。
4. 运行记录保留错误分类、逻辑样本 ID、attempt 计数和脱敏 evidence，但无 API key、Authorization、raw 正文或 evaluator labels。
5. live 若将来另行获批，产品界面必须要求负责人逐条审阅并确认；本轮不执行模型请求或 CAD。

## 后续 gate

当前 `product_language.v1` 授权 profile 绑定旧十条输入 hash，不能用于此候选；不得改写/扩展旧 profile 或旧 batch。若负责人接受该矩阵，后续工作应新建版本化 profile、独立输入/labels hash 绑定和适配的离线测试，再由 Codex 独立复核；固定 CAD venv 的回归和 offline preflight 通过后，才提交新的 batch ID 与预算请求。formal preflight、真实 provider 请求和 CAD confirmation 是不同授权门。

本稿不创建 batch，不运行 offline/formal preflight，不调用模型、网络或 CAD，不读取 `.env`、API key 或历史 raw 正文。`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
