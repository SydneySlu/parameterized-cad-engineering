# APP-003 Product Live Credential Diagnostic Scope — Candidate 2026-11-14-02

**状态：候选提案，待负责人审阅；未获 live 执行授权**  
**基线：`main=711b4d3`**  
**候选 batch：`app003-product-live-20261114-02`**  
**前置：`APP-003-LIVE-CREDENTIAL-ENTRY-FIX` 独立复核 `pass`（`df3f7b4`）；provider 权限尚未验证。**

## 目的

在 Product Live formal runner 已修复 `.env` credential entry 后，用全新 batch 确认真实 DeepSeek 请求能否越过认证/权限阶段，并记录真实 transport/provider 结果。旧 batch `app003-product-live-20261114-01` 已消耗 4/12 请求且失败，不重跑、不追加、不使用其剩余预算。

本候选沿用当前 `app003-product-live.v1` 已冻结的全部范围，**不修改授权 profile、输入、prompt、模型、预算或 CAD gate**。这不是广泛语言效果评测。所有有效 answer 仍须人工确认后才能运行 CAD；ask/refuse/冲突/unsupported 和任何失败均 fail closed。

## 冻结范围

| 项目 | 候选值 |
|---|---|
| profile / sample set | `app003-product-live.v1` / `app003-product-live-smoke.v1` |
| provider / model | DeepSeek / `deepseek-flash` |
| condition | `C0`，无检索 |
| prompt / contract | `app001-extraction.v5` / `app001-io.v1` |
| prompt file SHA-256 | `18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9` |
| frozen input IDs | P1-24mm, P2-ask-bore, P3-catalog-conflict, P4-unsupported |
| inputs SHA-256 | `666a4c08bbbb051a2bac038db4f5184c18a01829d4fff8f6d698832195fc0e8a` |
| evaluator labels SHA-256 | `73c671a7950afebb7e7e4c3a1e4fdc52702ebf43ec85fec0a588308abc4fd795` |
| budget ceiling | 12 HTTP total; max 3 attempts per each of 4 runs |
| CAD pipeline | enabled only after a valid answer receives explicit user confirmation |
| batch ID | `app003-product-live-20261114-02` |

预算是硬上限，不是目标消耗。认证拒绝、transport failure 或成功响应后，后续动作遵循 runner 与 batch 状态；禁止重跑本 batch。旧 batch 与 evaluator labels 均保持隔离。

## 验证和授权分层

- 已完成离线 preflight/dry-run：固定 CAD venv Python 3.11.18；runtime 版本检查通过；4 runs 预算可行；候选 batch 目录不存在；网络=0、正式 batch/ledger=0、凭据读取=0。
- 本 scope 文档和离线 preflight **不构成负责人批准，也不授权读取凭据或发出请求**。
- 负责人审阅并批准此精确 batch/scope 后，才可记录 approval credential 并运行 formal preflight。Formal preflight 只做本地校验和 credential entry 验证，不发送请求。
- 通过 formal preflight 后，真实 provider 请求还需单独、明确的执行批准；届时仅执行此 batch，绝不运行旧 batch。

## 证据和安全边界

summary 仅记录稳定状态、允许的诊断字段、repo-relative paths 与 hashes；不写 raw 正文、API key、Authorization header 或 evaluator labels。未经确认不得构造 CAD/STEP。保持 `FORMAL_EVALUATION_ALLOWED=False`。不改 `.env`、不打印 key、不访问其他 provider、不扩大 scope。

## 负责人审阅

请确认是否批准：批次 `app003-product-live-20261114-02`，沿用上表四条冻结输入、DeepSeek `deepseek-flash` / C0、最多 12 次 HTTP、CAD 仅在明确确认后运行。若批准 scope，下一步只做 formal preflight；真实请求另行批准。
