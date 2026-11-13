# APP-003 Product Live Smoke：执行准备包

状态：`review`，待项目负责人批准具体 batch 执行；本文件不授权网络请求。

日期：2026-11-13  
基线：`main=6fe4b43`  
批次候选：`app003-product-live-20261113-01`

## 目标

在已完成的 Product Live UI 和受控服务端入口之上，验证 4 条冻结自然语言刺激经过当前 v5 抽取、用户确认门和既有 CAD pipeline 的最小产品链路。结果只描述这 4 条刺激在固定配置下的行为，不构成广泛语言效果、统计评测或制造认证。

## 固定范围

| 项目 | 固定值 |
|---|---|
| profile | `app003-product-live.v1` |
| sample set | `app003-product-live-smoke.v1` |
| provider / model | DeepSeek / `deepseek-flash` |
| condition | `C0`，无检索 |
| prompt / contract | `app001-extraction.v5` / `app001-io.v1` |
| prompt file SHA-256 | `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9` |
| inputs SHA-256 | `666a4c08bbbb051a2bac038db4f5184c18a01829d4fff8f6d698832195fc0e8a` |
| evaluator labels SHA-256 | `73c671a7950afebb7e7e4c3a1e4fdc52702ebf43ec85fec0a588308abc4fd795` |
| logical runs | 4 |
| HTTP 上限 | 12（每条最多 3 次尝试） |
| CAD pipeline | 允许，但必须先由用户确认；ask/refuse/conflict/unsupported/失败均阻断 |

冻结输入位于 `agent-work/integration/APP-003-LIVE-PRODUCT/model-inputs.json`；evaluator labels 只用于人工评估，不进入模型请求、UI、summary 或 runner state。

## 输入与验收目标

1. `P1-24mm`：`请按 GN 705 做一个轴环，轴孔直径 24 mm。`。抽取合法后进入 `needs_confirmation`；只有显式确认后才允许生成和回读 STEP。
2. `P2-ask-bore`：`请按 GN 705 做一个轴环。`。缺少 `bore_d` 时必须 ask/blocked；不得自动填默认值、不得生成 STEP。
3. `P3-catalog-conflict`：`请按 GN 705 做一个轴环，轴孔直径 24 mm，外径 33 mm。`。目录/Schema 冲突必须阻断，不得静默覆盖或构造。
4. `P4-unsupported`：`请按 GN 705 做一个轴环，轴孔直径 24 mm，并要求阳极氧化表面处理。`。unsupported 请求必须阻断，即使几何字段合法。

## 证据与停止条件

- 每条 run 保留 input/prompt/contract/model identity、decision、字段来源、questions/missing/unsupported/conflicts、确认记录、Schema/IR/CAD/STEP 状态、错误码、raw/STEP 相对路径和 hash。
- summary 只保留相对路径和 hash，不写 raw 正文、API key、Authorization header 或 evaluator-only 标签。
- 任何 preflight、approval binding、预算、依赖、解析、Schema、IR、CAD、几何或 STEP 失败都停止；不能把失败记为 succeeded，也不能暴露其他 run 的产物。
- 正式执行前必须有项目负责人填写并批准同批次 `ProductLiveFormalApproval`；批准前只允许离线 preflight/dry-run。

## 当前结论

固定 CAD venv 的离线 preflight 已通过，批次目录尚不存在，dry-run 未创建目录、账本、transport 或网络请求。等待项目负责人审阅并明确批准后，才进入 live preflight 的正式执行步骤。
