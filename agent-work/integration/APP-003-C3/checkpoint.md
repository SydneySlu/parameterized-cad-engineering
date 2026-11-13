# APP-003-C3 checkpoint

- 日期：2026-11-13
- 任务：`APP-003-C3-PRODUCT-UI`
- 负责人：CC 实现 / Codex 中枢独立验收
- 状态：`planned`（已定义工作单，等待 CC 认领）
- 基线：`main=b90a83c`，本地 `main` 比 `origin/main` ahead 1；不自动 push。
- 前置：C2 `d839954` 已合入并经中枢独立验收；C2 handler 与 `/api/product/*`、`/product-download/<run_id>` 已可复用。
- 范围：仅离线 synthetic fixture 驱动的 `/product` 确认 UI；不接模型、不读取密钥、不创建 batch，不改变 C2 状态机和全局 gate。
- 验收目标：合法 bore24/bore80 确认后真实本地 STEP；ask 缺 bore_d 补充后新 child run；冲突/unsupported/refuse/Schema/CAD 失败安全阻断；C1 页面保持兼容；仅当前成功 run 可下载；动态内容安全渲染。
- CC 工作单：[`docs/coordination/prompts/APP-003-C3-product-ui-cc.md`](../../../docs/coordination/prompts/APP-003-C3-product-ui-cc.md)
- 下一步：由已有 C1/C2 CC 对话框认领工作单并实现；Codex 中枢随后独立复核固定 CAD venv、HTTP/界面正常及失败路径。
