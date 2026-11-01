# BenchCAD 2.0 深入拆解与轻量版接入建议

- 日期：2026-10-28
- 任务：DATA-001 扩展研究
- 状态：review；不冻结首期零件族
- 访问与核对：BenchCAD 2.0 官方仓库、设计规范、评审规范、状态页、官方博客与 Hugging Face 数据集元数据

## 先说结论：BenchCAD 2.0 要分成两层看

“BenchCAD 2.0 数据集”这个说法容易把两个不同资产混在一起：

1. **社区参数化零件族仓库**：GitHub `BenchCAD-org/benchcad-2` 的 `designs/`。它的目标是逐步积累 150 个有来源、有约束、可确定性生成的工业零件族。它更接近我们的参数化 CAD 数据源和构造器参考。
2. **Public/Core 工程任务评测集**：Hugging Face 上的 `benchcad-2.0-public` 与 `benchcad-2.0-core`。它们用于评估模型从工程图、渲染图、零件文件和 PCB 图像完成真实工程任务的能力，不是参数化零件族训练库。

这两层的许可和用途也不同。GitHub 仓库的代码与合并设计由仓库 MIT 许可证覆盖，发布的数据制品另有 CC BY 4.0 说明；Public 数据卡的评测条款明确禁止训练、微调、蒸馏、RL 环境、预训练、检索和搜索语料使用，也禁止重新上传或公开案例。Core 还需要人工审核的 evaluation-only agreement。因此，**Public/Core 可以作为外部评测或任务设计参考，不能作为我们轻量版的训练集、检索库或样本库**。项目主线应使用许可证和来源都能逐项核验的 GitHub 社区零件族，或者仿照其规范自行扩展目标零件族。

## A. GitHub 社区零件族到底包含什么

一个 BenchCAD 2.0 家族的最小目录是：

```text
designs/<family>/
├── part.py
├── spec.py
└── family.json
```

### `part.py`：人写的参数化几何构造器

核心是一个具名参数函数，例如：

```python
def build(body_w, body_h, body_t, hole_d, has_holes=0) -> cq.Workplane:
    ...
```

它使用普通 CadQuery 操作生成单实体、多实体 compound 或 assembly。每个 `build()` 参数都必须在 `spec.py` 的 `PARAM_SPEC` 中声明。构造器要求：

- 同一组参数得到同一几何；
- 不使用随机数、文件 I/O 或不可控外部状态；
- 固定在项目指定的 CadQuery 环境中运行；
- 可选特征通过布尔型或离散型参数分支控制；
- 多实体族可在 `family.json` 中声明实体数量，防止某个零件在导出时悄悄消失。

BenchCAD 框架还可以把 `build()` 派生为只依赖 CadQuery 和数学库的独立程序，并验证“直接调用构造器”和“派生程序”是否得到相同实体。这一点对我们很有价值，但不能直接替代项目自己的 Typed CAD IR：我们仍然需要把参数、特征节点、来源和验证结果放进自己的 IR。

### `spec.py`：采样合同、参数来源和工程约束

`spec.py` 不是一个普通的数据字典，而是“这个零件族哪些参数可以变化、哪些组合合法、参数从哪里来”的机器可执行合同。

`PARAM_SPEC` 中每个参数至少有四个字段：

| 字段 | 含义 | 对项目的作用 |
|---|---|---|
| `desc` | 参数的物理含义 | 生成用户可读字段说明和 Prompt 词表 |
| `unit` | 单位，如 `mm`、`deg` 或空字符串 | 单位归一化和 JSON Schema 校验 |
| `range` | `easy/medium/hard` 三种难度的合法范围 | 参数边界和难度分层 |
| `source` | 标准、厂商表格、工程规则或 `proportion` | 默认值和范围的可追溯来源 |

常见可选字段如下：

| 字段 | 含义 |
|---|---|
| `integer` | 是否按整数采样，例如孔数、槽数、目录行号 |
| `choices` | 离散选择值，或按难度给出的离散选择集合 |
| `refine` | 不直接采样，而是在 `refine()` 中根据其他参数推导 |
| `feature` | 可选特征开关，如是否有槽、是否有第二个紧定螺钉 |
| `coverage` | 采样必须覆盖的目录值，例如每一个标准型号 |
| `askable` | 部分族使用的标记，表示该字段适合直接向用户询问 |

难度不是“模型分数”，而是参数空间的三档生成合同：`easy` 保留核心几何并使用较窄范围，`medium` 打开部分特征并扩大范围，`hard` 覆盖全部特征和接近约束边界的合法情况。

`check(p)` 返回违反约束的字符串列表，是这个数据接口最重要的工程部分。例如它可以检查：

- 孔径小于外轮廓，避免打穿边壁；
- 壁厚、孔边距和槽间距足够；
- 一个目录型号的尺寸不能与另一个型号混搭；
- 槽数与长度/槽距公式一致；
- 可选特征只在对应尺寸范围内出现。

`refine(p, difficulty, rng)` 处理参数耦合。例如先抽到一个目录行号，再把外径、宽度、螺钉规格和长度全部填成该行的值；或者先抽轮毂直径，再在可行区间中生成孔径。它应该表达公式或目录行选择，而不是靠大规模随机拒绝循环“碰运气”。

### `family.json`：标签和来源元数据

核心字段为：

```json
{
  "family": "...",
  "standard": "...",
  "base_plane": "XY",
  "description": "...",
  "source": "...",
  "contributor": "..."
}
```

可能补充 `solids`（实体数量）、`geomlib`（使用的共享几何辅助函数）以及装配组件信息。它不是完整的训练样本标签，而是零件族的身份、基准平面、标准和出处。

### BenchCAD 的自动检查和人工检查

机器检查大致覆盖：目录结构、参数声明一致性、采样值是否在范围内、约束是否通过、几何是否为有效非退化实体、同一种子是否生成字节一致的程序、难度层是否真的不同、目录值覆盖率、几何重复率和辅助函数是否可内联。

人工评审则检查标准/厂商证据、图纸与几何是否一致、极值尺寸是否合理、孔位和接口是否真的可用、公式是否有来源、约束是否漏掉明显失效模式。这种“机器可运行 + 人工审工程真实性”的组合，正好可以作为我们数据质量门的参考。

## B. 当前公开的社区族和对我们项目的意义

状态页在本次核对时显示 **4/150 个族已合并**，已合并的族为：

| 已合并族 | 已有内容 | 对我们三个候选方向的参考价值 |
|---|---|---|
| `clevis_fork_head` | DIN 71752 叉头；销孔、叉臂间隙、螺纹杆、短/长目录变体 | 连接接口、标准行耦合、孔和螺纹规则；不是安装板 |
| `set_screw_shaft_collar` | GN 705 / DIN 705 风格轴环；轴孔、外径、宽度、径向紧定螺钉和大规格第二螺钉 | 轴类机械件、孔/径向孔、可选特征；不是安装板 |
| `slotted_din_rail` | EN 60715 TH35、35×7.5 mm 导轨、重复槽、长度和槽数变体 | 与自动化设备机架、电控柜和安装系统最接近；不是铝型材角码 |
| `speaker_pole_mount_socket` | 圆形法兰、杆件插孔、四孔安装布局、壁厚、深度和孔距变体 | 法兰、安装接口、孔阵列的直接参考；行业是音响安装，不是机器人 |

仓库中还可能出现开放提案或未进入状态页的设计目录，不能把目录名直接当成已发布、已审查、可用于项目的数据。项目接入前要以具体 commit、状态页和许可证为准。

### 与三个候选零件族的匹配

#### 1. 工业铝型材框架角码/连接板：最容易落地

可直接复用的不是某个完整目标族，而是三类机制：

- `slotted_din_rail` 的“长度—槽数—槽距”耦合；
- `speaker_pole_mount_socket` 的法兰/孔阵列建模；
- 各族共有的“目录行锁定 + 壁厚/边距/干涉检查”。

需要新增的内容相对窄：先固定一个型材规格（如 2020、3030 或 4040），再做一个 L 型角码或平面连接板，加入板长、板宽、板厚、槽宽/孔径、孔距、孔数、沉头或通孔开关，以及型材槽位方向约束。先不要同时覆盖多个型材系列和多家厂商。

这是当前最适合两三个月轻量版交付的方向，因为几何可以保持为平板/折板和孔阵列，工程规则容易从厂商目录或标准图纸核验，且和自动化设备机架、防护围栏、工装台、机器人工作站的应用场景一致。

#### 2. 机器人末端工具安装转接板：应用价值高，但来源扩展更多

`speaker_pole_mount_socket` 可借用“法兰 + 四孔阵列 + 中心接口”的建模思路，`clevis_fork_head` 可借用连接接口和尺寸耦合思路。但机器人转接板必须新增 ISO 9409-1 或具体机器人品牌法兰的真实尺寸、定位止口/定位孔、工具侧孔阵列和螺栓规则。它不能把音响法兰尺寸直接改名为机器人法兰。

最小可行范围是：一个机器人法兰规格 + 一个工具侧孔阵列 + 2–3 个板厚/外形变体。若一开始同时支持多品牌、多种轴端和任意工具安装孔，数据、命名和约束工作会迅速超过轻量版范围。

#### 3. 电机安装板/支架：可行，但标准要先冻结

`speaker_pole_mount_socket` 对法兰和孔阵列有参考价值，`set_screw_shaft_collar` 对轴孔和圆柱接口有参考价值。但电机支架还需要电机安装标准或具体型号系列、法兰外形、孔距/孔径、中心止口、板厚、折弯/加强筋和线缆避让规则。

最小范围应先做一个电机系列的平板安装板，不把受力分析和复杂折弯支架作为首期依赖。平板版可作为第二候选；加入加强筋、长圆孔、折弯和多型号兼容后，延伸量高于角码/连接板。

## C. BenchCAD 2.0 Public/Core 评测集包含什么

官方博客将 2.0 定义为六类硬件工程任务。每个案例通常由任务说明、输入资产、参考答案和评测配置组成；公开数据的文件树可以看到 `case.json`、`TASK.md`、`input/`、`gt/`、`bom.json`、STEP 文件或渲染图等文件。它的核心内容是**输入模态与工程任务**，不是 `PARAM_SPEC` 那样的参数化族合同。

六类任务及其主要输入输出是：

| 任务 | 输入 | 输出 |
|---|---|---|
| Drawing to CAD Part | 一张有尺寸标注的工程图 | 一个 CAD 零件 |
| Assembly, parts supplied | 装配图、零件 STEP 文件、零件清单 | 装配体 |
| Parts and assembly | 装配图、需要新建的零件图、其他零件的 STEP 文件、BOM | 新建零件和装配体 |
| Reverse engineering Part | 同一零件的四个渲染视图 | CAD 零件 |
| Reverse engineering Assembly | 装配体及各零件的多视图、零件清单 | 零件和装配体 |
| ECAD | PCB 六个视图，必要时加内层铜图 | 电路连接图/网络图 |

从项目接入角度，应把字段分为四组理解：

1. **案例身份字段**：任务类型、案例 ID、版本、输入/参考资产路径、评测配置。
2. **输入字段**：工程图 PDF、零件/装配 STEP、BOM、四视图或六视图渲染、PCB 内层图等。
3. **参考输出字段**：零件 STEP、装配实例/变换信息、需要生成的零件参考、ECAD 网络图。
4. **评测字段**：任务专用的几何、装配位置、可执行性或连接性检查结果。

这里不要把 `case.json` 的任务元数据误认为参数化零件族的 `PARAM_SPEC`。Public/Core 案例能告诉我们“真实工程输入长什么样、评测应检查什么”，但通常不能直接提供“用户输入某个孔距后，合法范围是多少、默认值来源是什么、如何从参数确定性构造”的完整信息。

## D. 我们应该用 BenchCAD 的哪一部分

### 可作为项目数据主线的部分

优先采用 GitHub 社区族的**代码与设计接口**，或按该接口新增一个目标族：

- `part.py` 给出可读的确定性 CadQuery 构造器；
- `PARAM_SPEC` 给出单位、范围、离散规格、难度和来源；
- `check()` 给出工程约束和失败原因；
- `refine()` 给出参数耦合和目录行选择；
- `family.json` 保存族身份、标准和出处；
- `bench2 validate/preview` 提供可复现的机器检查和渲染证据。

这些内容可以转换成我们自己的轻量版 manifest 和 Typed CAD IR，但不要把 BenchCAD 的字段直接当成项目最终接口。

### 只能作为外部评测或任务设计参考的部分

Public/Core 可用来参考：

- 工程图到 CAD 的输入形式；
- 装配图、BOM 和 STEP 的组织方式；
- 逆向建模的多视图输入；
- “零件形状正确但装配位置错误”这类失败分析；
- 对几何、装配变换和电路连通性的分层评测思路。

但按照当前数据卡条款，不能把其案例、图纸、参考 STEP 或检索样本放进我们的训练/检索语料，也不能把它们复制到公开项目中。若需要公开可复现实验，应发布自己的样本和生成代码，或只发布不受限的案例 ID、指标脚本和来源说明。

## E. 预计需要做多少延伸

以下是面向轻量版的工程估算，不是 BenchCAD 官方要求。

### 角码/连接板

建议最小扩展包：

- 1 个明确的零件族；
- 1 个型材规格系列；
- 3–5 个真实目录规格或型号；
- 6–12 个参数；
- 8–15 条可解释的几何/接口约束；
- 20–50 个经过验证的代表性实例用于检索和回归；
- 50–150 条人工编写的自然语言请求、缺失参数和冲突参数案例。

这里的实例量主要是覆盖和回归规模，不是要训练一个大模型。若要形成更饱满的公开小数据集，可以把合法参数组合扩展到几百个，但必须按参数组合去重并保留来源。

### 机器人末端转接板

- 至少 1 个机器人法兰标准或具体型号；
- 1 个工具侧孔阵列族；
- 2–3 个板厚/外形/孔型变体；
- 需要新增标准图、厂商图和定位接口规则；
- 自然语言样本要额外覆盖“机器人端/工具端/定位止口/孔阵列”术语。

它的几何构造本身不难，难点在接口标准和来源核验，因此延伸量中等，数据采集风险高于角码。

### 电机安装板/支架

- 先冻结一个电机系列或安装标准；
- 2–4 个法兰尺寸或孔距变体；
- 先做平板版，后续再做折弯/加强筋版；
- 需要新增中心止口、孔阵列、板厚和避让规则；
- 如果加入强度或重量约束，需另建仿真/工程计算链，不应混进首期几何交付。

它的延伸量中等到偏高，主要取决于是否从平板安装板扩大到真正的支架族。

## F. 获取方式和许可证检查

### 社区族代码与规范

- GitHub：<https://github.com/BenchCAD-org/benchcad-2>
- 设计接口：仓库 `docs/DESIGN_SPEC.md`
- 人工评审规则：仓库 `docs/REVIEWING.md`
- 当前合并状态：仓库 `docs/STATUS.md`

建议固定到具体 commit 下载或 git clone，不要只保存网页截图。至少保存：

```text
family source commit
part.py / spec.py / family.json
source URL and drawing/table reference
license and attribution
bench2 validation output
preview images and generated instance manifest
```

### Public/Core 评测集

- Public：<https://huggingface.co/datasets/BenchCAD/benchcad-2.0-public>
- Core：<https://huggingface.co/datasets/BenchCAD/benchcad-2.0-core>
- 任务说明和背景：<https://benchcad.com/blog/benchcad-2.html>

Public 是自动门控下载，Core 是人工审核访问。下载前要保存当时的数据卡和协议版本；在当前协议下只能用于评测，不能把文件下载后接入检索或训练 pipeline。

## G. 接入轻量版的推荐处理流程

### 第 1 步：先做许可和来源分流

建立一个数据台账，把每个资产标记为：

```text
source_kind = community_family | public_eval | core_eval | self_authored
license
allowed_use = build_reference | local_eval_only | retrieval | training | redistribution
source_commit_or_version
```

`public_eval` 和 `core_eval` 在当前条款下应标为 `local_eval_only`，不能进入检索/训练目录。

### 第 2 步：抽取 BenchCAD 家族到项目 manifest

不要直接把 `PARAM_SPEC` 当成项目 IR。建议转换为：

```text
family_id
part_type
source / license / attribution
parameters[name, desc, unit, range, choices, default_provenance]
constraints[id, expression, reason, source]
feature_sequence
builder_ref / builder_version
ir_version
validation_version
```

同时保留原始参数名和映射后的项目字段，便于追溯。例如 `hole_bcd` 可以映射到项目字段 `mounting_bolt_circle_diameter_mm`，但不能丢掉原始名字和来源。

### 第 3 步：生成项目实例

在固定的 CadQuery 环境中按 `easy/medium/hard` 生成合法实例，保存：

- 参数 JSON；
- Typed CAD IR；
- 多视图渲染；
- STEP 文件；
- 构造日志和错误码；
- B-Rep/STEP 回读检查结果；
- 参数到实例的来源记录。

轻量版只需要精选多样实例用于小样本检索和回归，不需要把所有可生成组合都放进 Prompt。

### 第 4 步：补齐 BenchCAD 没有的用户交互数据

BenchCAD 社区族主要描述“零件如何被参数化生成”，不天然提供我们的用户输入层。因此需要人工补写：

- 完整描述，如“做一块适配 3030 型材的双孔角码”；
- 缺失字段请求，如未给出板厚或槽宽；
- 冲突字段，如孔距导致边距不足；
- 参考零件示例和可选图片线索；
- 期望结构化 JSON、追问和验证结果。

首期几十到几百条即可用于 Prompt、检索和验收，不需要把它包装成大规模监督训练集。

### 第 5 步：设置切分和防泄漏规则

训练/开发/测试如果未来需要，不能随机把同一个目录行的近邻尺寸拆到不同集合。应按型号、规格行、参数区域或 near-duplicate group 分组切分；Public/Core 评测样本更不能进入这些集合。

### 第 6 步：以项目验证器收口

BenchCAD 的 `bench2 validate` 只能证明其接口和族样本满足 BenchCAD 合同。接入项目后仍要追加：

- 单位和 JSON Schema 校验；
- Typed CAD IR 引用完整性；
- 白名单 CadQuery 构造；
- STEP 导出与回读；
- B-Rep 有效性；
- 孔位、边距、厚度和接口规则；
- 参数修改后的几何稳定性；
- 失败字段和版本化运行日志。

## 最终建议

如果目标是两三个月完成轻量版，我建议把 BenchCAD 2.0 的作用限定为：

1. 用 GitHub 社区族学习“来源—参数—约束—确定性构造—验证”的数据组织方式；
2. 选择一个目标零件族，按同样接口补一个小而完整的自有族；
3. 将社区族的合法实例作为少量检索/回归参考，前提是逐项确认许可证；
4. 把 Public/Core 留在外部评测位置，只借鉴任务形式和失败指标；
5. 优先从工业铝型材角码/连接板开始，其次是单一标准机器人转接板，最后是平板式电机安装板。

这样得到的是一个能在轻量版中真正运行的“小而可审计”的参数化 CAD 数据闭环，而不是把评测集、参数化族和未经授权的外部 CAD 文件混成一个无法公开或复现的大数据库。

## 来源

- BenchCAD 2.0 GitHub：<https://github.com/BenchCAD-org/benchcad-2>
- 设计接口：<https://raw.githubusercontent.com/BenchCAD-org/benchcad-2/main/docs/DESIGN_SPEC.md>
- 评审规范：<https://raw.githubusercontent.com/BenchCAD-org/benchcad-2/main/docs/REVIEWING.md>
- 当前状态：<https://raw.githubusercontent.com/BenchCAD-org/benchcad-2/main/docs/STATUS.md>
- 官方博客：<https://benchcad.com/blog/benchcad-2.html>
- Public 数据卡：<https://huggingface.co/datasets/BenchCAD/benchcad-2.0-public>
- Core 数据卡：<https://huggingface.co/datasets/BenchCAD/benchcad-2.0-core>
