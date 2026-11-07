# APP-001 extraction v3 激活记录

ADR-0016 已被项目负责人接受。`app001-extraction.v3` 已接入生产 prompt 加载与解析契约，并经 Codex 独立复核后合入 `main`（`7dc7a37`）；真实模型效果仍未验证。

候选源 `../APP-001-baseline-prep/prompt-v3-candidate.md` 保持原样，SHA-256 为 `e90ad55ca20cf356c3c143a723da271f1874eb9fa902dd1379d4afba657a8b5b`。生产冻结副本 `prompt-v3.md` 去除了候选/未激活元说明，SHA-256 为 `3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`；manifest 分别锚定两者。

保持不变：`app001-io.v1`、9 条 evaluator-only `acceptance-set-v0`（原 SHA-256）、CAD-003 Schema、36 个逻辑运行/108 次 HTTP 上限、重试策略和 C2/IR/CAD/STEP 禁用范围。`FORMAL_EVALUATION_ALLOWED` 仍为 `False`，本次没有任何真实模型/API 调用授权。模型效果如需评测，必须使用新唯一批次并单独授权。

回滚目标是 v2 prompt `d95f853d325e05d9b045921da994256c7b8656336b5be02d75ced20d22755eac`；回滚不修改历史批次或候选 v3 证据。
