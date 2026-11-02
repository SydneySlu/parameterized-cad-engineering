# DATA-003-R2 族级许可证矩阵（审计材料）

范围：固定来源 `https://github.com/BenchCAD-org/benchcad-2`，commit `035f467142888edfd0bd7cd73906f9b155c8f43c`，族 `designs/set_screw_shaft_collar`。本表区分上游文字证据和本项目暂定操作边界；它不是法律意见，也不把许可不确定项判成可公开发布。

| 资产类别 | 证据 | 当前可接受的项目内用途 | 当前禁止/不应推断 | 署名/保留要求 | 待确认事项 |
|---|---|---|---|---|---|
| BenchCAD 仓库代码、族源文件和框架代码 | 固定 commit 的 `README.md:53-55` 写明 code and designs are MIT；`LICENSE:1-21` 为 MIT 正文；族 `part.py/spec.py/family.json` 和 `framework/bench2/*` 位于该仓库。固定 commit 文件及 blob 证据见 raw snapshot manifest。 | 可在本地审计和运行；如项目复制、修改或再分发这些源码，按 MIT 条款处理。 | 不把源码 MIT 文字自动扩展解释为所有生成 CAD、外链内容或数据集的许可。 | 再分发源码时保留 copyright 与 MIT permission notice；上游 copyright 为 `The BenchCAD Authors`，具体随文件分发。 | 若将族代码打包进本项目产品或发布仓库，确认所需 notice 的放置方式及是否存在额外文件级声明。当前未发现该族文件单独 SPDX 覆盖声明。 |
| BenchCAD 官方 released dataset artifacts | 固定 commit 的 `LICENSE:25-30` 将 HuggingFace BenchCAD 数据集单列为 CC BY 4.0；README:53-55 同样区分 code/designs 与 released dataset artifacts。该族源 status 为 `MERGED`，STATUS 页面记录 `0 release-qualified`。 | 只有取得官方发布资产并遵守其 CC BY 4.0 及具体资产元数据后，才按该许可处理其适用的数据资产。此任务未下载或使用这类资产。 | 不将 CC BY 4.0 自动套用到项目自行生成 STEP/渲染物；不因为族 `MERGED` 就声称已存在可用 released artifact。 | 对确属 CC BY 4.0 的资产按 CC BY 4.0 提供署名、许可链接和变更说明，并遵守适用条款。 | 当前固定 commit 对实际 HuggingFace 文件的资产清单、版本和每个文件的许可标记没有给出本审计所需证据；需在使用具体发布资产前确认。 |
| 本项目从构造器生成的 STEP、渲染图和其他派生 CAD | `part.py` 是 MIT 仓库中的参数化构造代码；STATUS 仅表示族已 MERGED 且整体 `0 release-qualified`。仓库许可没有明确说本项目自行运行生成的输出归属或再发布条件。 | 仅用于本地、非公开审计实验，保存在 ignored `work/benchcad-output/`；manifest/run log 可记录参数、指标、相对路径和哈希。 | `license_scope_uncertain`。不得宣称输出自动受 MIT 或 CC BY 4.0 覆盖；未确认前不公开发布 STEP、渲染图或 CAD 派生物，也不将其放入公共训练/检索语料。 | 暂无可证实的输出署名规范。内部材料保留 BenchCAD 仓库 URL、commit、族 ID、构造器来源和参数来源。 | 向 BenchCAD 上游确认：MIT 的 “code and designs” 是否涵盖由其族代码生成的几何/STEP；参数化重建是否构成许可意义上的衍生作品；公开发布时是否要求/建议署名；不同格式的渲染/网格是否同样适用。 |
| `NOTES.md` 引用但未随族源码分发的标准图纸、SVG、产品照片及外链文件 | `designs/set_screw_shaft_collar/NOTES.md` 列出 JW Winco GN 705 标准页链接，并提到 `gn705_standard_sheet.pdf`、`gn705_engineering_drawing.svg`、`gn705_product_photo.jpg`；这些文件不在该族目录快照文件清单中。 | 可保留引用文本和来源链接用于审计；本任务未下载或复制这些材料。 | `license_scope_uncertain`。不得因为 NOTES 引用、BenchCAD 仓库 MIT 或公开可访问就复制、训练、检索或再发布第三方图纸、图片、SVG/PDF。 | 若未来经权利人许可使用，按权利人指定的署名、来源链接和许可版本执行；现阶段没有可确认的署名许可。 | 分别确认 JW Winco 页面、标准图纸、SVG、产品图片的权利人、许可范围、商业/非商业使用条件和再发布权；还需确认从图纸提取尺寸进入项目材料的边界。 |
| BenchCAD Public/Core 评测资产 | 当前任务明确不下载 Public/Core；本审计未将其纳入源快照、smoke、训练或检索。项目计划将受限评测数据与可用族源码区分。 | 不需要它们即可完成固定族来源审计和本地构造 smoke。 | 不下载、不进入训练/微调、检索索引、样本语料或再发布材料；不能从代码 MIT 或数据集 CC BY 描述推断 Public/Core 的许可。 | 不适用；未获取资产。 | 若未来有独立评测需求，需由中枢先核对该评测资产的访问条件、许可和防泄漏约束，再决定流程；本任务不作此授权。 |

## 保守结论与上游问题

- 源码层面：固定 commit 的仓库 README/LICENSE 明确声称 BenchCAD code/designs 适用 MIT；再分发源码时保留 MIT notice。
- 数据层面：官方 released dataset artifacts 被单独说明为 CC BY 4.0；这不是项目自己运行构造器所导出 STEP 的许可证明。
- 第三方材料层面：NOTES 中的文件名/链接只说明来源线索，不构成授权；不复制材料。
- 生成物层面：`license_scope_uncertain`。在上游回答之前，限定本地实验，最多发布本项目代码、审计草案 manifest 和不包含第三方材料的来源/哈希摘要；不发布 STEP、渲染图、网格或引用素材。
- 评测集层面：Public/Core 不进入训练、检索或再发布语料；本任务未下载。

本矩阵是 DATA-003-R2 审计材料，须由 Codex 中枢复核。它不代表首族 `release-qualified`，也不替代权利人对具体输出/引用材料的许可确认。
