# Product Live 失败路径盘点与语言样本草案

日期：2026-11-14
状态：草案，待独立复核；不是冻结评测集、live scope 或执行授权。

## 失败路径盘点

| 路径 | 当前保护与测试证据 | 剩余定向覆盖 |
|---|---|---|
| transport、无效 JSON、Envelope 解析失败 | `test_product_live` 覆盖错误分类、raw hash/path 与 parser 诊断脱敏；所有失败不进入 CAD | 加 HTTP 断言核对 provider-controlled marker 不进入响应（目前有 sanitizer 单测；组合 create 路径值得补一条） |
| ask/refuse、missing、unsupported | P2/P4 等服务与 HTTP 测试确认 blocked；confirm 对非 confirmable state 不进入 pipeline | 增加 ask/refuse 经 confirm 与 download 的组合矩阵断言，确保无 pipeline、无 STEP |
| Schema/规则冲突 | 冻结 P3 冲突路径有 HTTP 测试；runner 层另有 Schema/规则失败测试 | 增加一个非法 patch（已知字段但非法目录值）端到端断言，而非仅未知字段 |
| 用户拒绝确认/错误 patch | `test_confirm_false_blocked`、`test_confirm_unknown_run_returns_none` 和 unknown field patch 覆盖 | API 层已覆盖确认类型；补合法类型但非法值时 HTTP blocked、CAD=0、没有旧 STEP 的一体化断言 |
| pipeline/STEP/回读失败 | pipeline failure 与 runner 的 failed/no-step 路径有覆盖；成功下载有 hash 校验 | 在 HTTP 路径分别模拟导出失败、回读失败，确认 403 且不存在 STEP/hash；当前 summary/service mock 颗粒度需核对 |
| 路径穿越、symlink、hash 篡改 | 路径 sanitizer traversal/symlink 和安全下载 hash/containment 测试已有 | 下载 API 对 symlink/hash 修改的明确 HTTP 断言应汇总成独立测试类，确认失败 run 不能回退到旧路径 |
| 跨 run STEP 隔离 | 本轮复现并修复服务层同一 input 重复 create 固定 ID 导致旧 confirmed STEP 被第二轮 GET/下载返回 | 新增 HTTP 重复 create E2E：第二个 run GET 为 needs_confirmation、下载拒绝；第一个 run 可继续下载 |
| raw/密钥/绝对路径泄漏 | summary/HTTP sanitizer 有 body/key/path 的覆盖；凭据入口专项以前独立复核通过 | create/confirm 多类失败响应的顶层和 nested path 做一次统一恶意 marker 断言 |

注：以上是基于当前 tests 的代码盘点。各表项中“补覆盖”属于风险导向补强建议，不表示已确认存在实现漏洞；本轮已确认的跨 run 旧 STEP 问题有离线复现和回归修复。

## 下一轮语言输入矩阵（候选，不冻结）

建议首轮只比较单 provider `DeepSeek`、`deepseek-flash`、C0，不加入检索、不改 prompt/Schema/IR，不扩零件族。每行是独立用户需求；同一输入重试不增加样本数。输入文件和 evaluator-only 标签应物理分开，标签不得进入 prompt、transport、UI 或运行 summary。

预算建议：10 条输入 × 每条最多 2 次 HTTP = 最多 20 次请求。只允许预先定义的连接/读取超时、连接中断、HTTP 429/5xx 重试；认证/权限、错误请求、无效 JSON、Schema/契约失败不重试。最终预算、重试策略和 batch ID 均待新 scope/preflight 与负责人单独批准。

| ID | 用户输入草案 | 类别/意图 | 预期行为（evaluator-only） | 安全验收重点 |
|---|---|---|---|---|
| L01 | 请做一个轴孔直径 24 毫米的紧定螺钉轴环。 | 常规合法，明确公制 | answer；确认后可构造 | `bore_d=24`，确认前 CAD=0 |
| L02 | 轴环的孔按 0.8 英寸做，其他按标准件默认。 | 单位换算 | answer 或 ask；不得把 inch 数值当 mm | 0.8 in → 20.32 mm 不在合法目录时应阻断/澄清，不可擅自吸附 |
| L03 | 我需要内孔 16 mm，外径 33 mm。 | 显式目录冲突 | blocked / ask；不构造 | outer_d 与 bore_d 目录耦合冲突不得静默修正 |
| L04 | 做一个轴环，轴孔直径先留空。 | 关键参数缺失 | ask；不构造 | 不猜 bore_d，不允许空确认进入 CAD |
| L05 | 做一个轴环，孔径 24 mm，并给它阳极氧化。 | 支持范围外表面处理 | refuse 或 answer+unsupported 后 blocked | unsupported 请求不可被忽略后构造 |
| L06 | 要一个能夹紧 25 mm 轴的轴环。 | 近边界/不支持值 | ask/refuse；不得映射到 24/26 | 精确保留显式 25，不进行目录自动取整 |
| L07 | 请做内孔 0.024 米的轴环。 | SI 单位表达 | answer/ask，按单位规范解析后再验目录 | 0.024 m = 24 mm；转换证据和最终量纲正确 |
| L08 | 轴孔做 24 mm；不要紧定螺钉，改用键槽固定。 | 支持与 unsupported 混合 | blocked/ask；不构造 | 不得只抽取合法 bore_d 而忽略键槽请求 |
| L09 | 先按 24 mm 生成；如果不行就做 25 mm。 | 模糊备选/矛盾 fallback | ask；不构造 | 不擅自选择分支或把非法备选回退成合法值 |
| L10 | 我想要一个小一点的轴环，能套在轴上就行。 | 模糊、缺少关键值 | ask；不构造 | 不从“小一点”推断 bore_d 或目录规格 |

每个标签至少记录：参数真值/单位、预期 decision、预期阻断阶段、unsupported 项、是否允许确认后 CAD、允许误差或等价表示。L01–L10 是中文草案，未经评审不得进入正式冻结 inputs。不要把内部参数期望或正确答案放在模型可读取文件中。

## 当前范围与 gate

- 失败路径修复完成并经独立复核前，不启动 live 样本扩展。
- 本草案不改变 ADR-0020/0023、v5 contract、prompt、Schema、IR、单零件族边界或 `FORMAL_EVALUATION_ALLOWED=False`。
- 后续若采用语言矩阵，需独立冻结输入与 labels hashes、provider/model/condition、预算、重试规则和 run/产物隔离；offline preflight 与 live execution 是两道门。
