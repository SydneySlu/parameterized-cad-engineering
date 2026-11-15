# APP-004 checkpoint

- 日期：2026-11-15
- 任务：技术验收与交付记录
- 状态：done（本地 main 已提交；远端同步状态见最后一节）
- 验收基线：`main` HEAD=`6b90c1998134e1629102720a659fdeae2e027869`，开始时 `main` 与 `origin/main` 一致、工作区干净。
- 目标：汇总并复核 A/B/C 轻量版单族产品链交付证据，运行当前固定 CAD venv 全量相关回归，记录结论与能力边界。

## 修改产物

- `agent-work/reviews/APP-004-TECHNICAL-ACCEPTANCE.md`：正式技术验收和交付记录。
- `docs/PROJECT_STATUS.md`：同步 APP-004 验收结论。
- `docs/PROJECT_PLAN.md`：将 APP-004 标为已完成，并保留后续决策事项。
- `docs/WORKLOG.md`：追加式工作记录。

## 验证

固定环境 `work/benchcad-output/venv/bin/python`，Python 3.11.18：

```text
tests/llm               933 passed, 8 skipped (941 run)
tests/integration       527 passed
tests/demo              219 passed
tests/schema             17 passed
tests/cad_compilation    13 passed
total                  1709 passed, 8 skipped (1717 run)
```

8 项 skip 为既有环境/外部 Ollama 条件测试。测试日志有已知 ResourceWarning 和依赖弃用警告，不影响退出码。

## 正常/失败路径证据与限制

- 正常：A2 已批准批次 24 mm、80 mm 均生成并回读 STEP；C2/C3 synthetic flow 确认后生成 STEP；Product Live P1 经 per-run 确认后生成 STEP。
- 失败/阻断：缺参 ask、unsupported/refuse、Schema 目录冲突、注入 STEP export failure、未回答问题的确认均有阻断/失败且无错误 STEP 发布证据。
- 本轮未调用真实模型/provider、未创建或修改 batch、未运行 formal preflight；固定 CAD 测试使用临时输出。`FORMAL_EVALUATION_ALLOWED=False`。
- 验收只覆盖当前单族、固定 CAD 环境和已审查的小批次；不声称广泛语言能力、生产部署就绪、跨族能力、制造认证或长期稳定性。下一轮 N01–N10 profile 是 FakeTransport offline-only。

## 提交

- 初次记录：待提交。
- 下一步：核对提交与远端状态；远端未同步时由负责人按需推送。任何新的真实模型运行需新的可执行 live 入口、scope、preflight 和负责人明确授权。
