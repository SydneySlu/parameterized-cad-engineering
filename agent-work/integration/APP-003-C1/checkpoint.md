# APP-003-C1 checkpoint

- 日期：2026-11-12
- 负责人：CC 实现 / Codex 中枢独立验收
- 状态：`in_progress`
- 目标：交付首个本地可用浏览器演示，支持需求文本记录、用户参数确认、Schema/IR/CAD/STEP 生成、状态/错误查看、STEP 获取和修改参数后重新生成。
- 基线：`main=00b9819`，开始时工作区干净且与 `origin/main` 对齐。

## 已完成：C1 范围与授权边界

- 项目负责人已确认推进里程碑 C，且 ADR-0020 明确由中枢结合现有架构选择界面方式。
- 新增 ADR-0022：首切片采用仅监听 `127.0.0.1` 的 Python 标准库 Web UI；不新增依赖；复用已验收 pipeline；用户手动确认结构参数；本任务不接真实模型、不读取密钥、不发网络请求。
- 已创建 CC 实施 prompt：`docs/coordination/prompts/APP-003-C1-local-demo-cc.md`。
- 已更新 `docs/TASKS.md`、PROJECT_STATUS、PROJECT_PLAN。下一步由 CC 认领 prompt 实现；Codex 中枢在固定 CAD venv 独立复核。

## 不变量

- 仅支持冻结单族 `set_screw_shaft_collar`，调用现有 schema/IR/compiler/geometry/STEP 实现。
- 每次 run 独立 UUID 目录；下载路径必须约束在当前成功 run 内，并验证成功 manifest/hash；失败不得返回旧文件。
- 文本只作为需求记录；首切片手动录入参数，不宣称模型理解。UI 实际调用 live LLM 需要另行制定产品授权、预算和 gate。
- A2 `...-01` 至 `...-04` 历史批次保持只读；`FORMAL_EVALUATION_ALLOWED=False` 不变。

## handoff_self_check

```text
changed=ADR-0022; APP-003-C1 task row; PROJECT_PLAN/PROJECT_STATUS; CC prompt docs/coordination/prompts/APP-003-C1-local-demo-cc.md; this checkpoint
commands=git root/status/log verified; reviewed existing README, pipeline, A2 runner, task board, project docs and ADR-0020; implementation tests not_run (this unit defines scope only)
confirmed=no existing Web framework; existing run_pipeline accepts v5 envelope and saves IR/index/compiler validation/STEP; fixed CAD venv available; no additional model authorization exists
unresolved=CC implementation, automated HTTP/UI tests, local runtime validation, Codex independent review
next_agent_focus=implement only APP-003-C1 per prompt; preserve localhost-only, manual-parameter/no-LLM boundary, run/download isolation, schema provenance and fail-closed success reporting
```
