# APP-002-INTEGRATION-A2-SCOPE checkpoint

## Status: in_progress

日期：2026-11-11。负责人：Codex 中枢 + CC（准备阶段）。

### 基线

- A1 已合入 `main`：`d6faf70`。
- 固定环境已验证：集成 81、CAD 13、Schema 17；bore24 合成 envelope 真实生成并回读 STEP；P1 fail-closed 成功门经独立复核通过。
- 当前 `FORMAL_EVALUATION_ALLOWED=False`；无 A2 batch ID，无 live 请求授权。

### 本工作单元目标

准备真实模型→A1 pipeline 的受控入口和授权材料。仅做接口核对、离线 preflight、mock 测试和 scope 草案；不发模型/网络请求，不读密钥/.env，不创建正式批次。

### 草案 scope（待负责人批准）

- provider/model：DeepSeek `deepseek-flash`，沿用已审查 v5 配置；Ollama 暂不纳入本次最小整链 smoke。
- 代表性输入：普通合法孔径 24 mm、第二螺钉边界孔径 80 mm、缺少 `bore_d` 的追问路径。
- 目标证据：每个 run 的 request、受约束 envelope、参数/来源、IR、几何/STEP 验证、产物 hash 和失败原因可追溯。
- 这不是完整效果评测，也不证明语言泛化；真实执行前必须生成唯一 batch ID、明确预算并取得项目负责人单独授权。

### 交接关注点

- 旧 APP-001 runner 的 formal gate、预算和历史 batch 不自动扩展到 CAD 整链。
- A1 的 `scripts/run_cad_pipeline.py` 仍是 synthetic-only；A2 需要独立受控入口或明确的 model→pipeline adapter。
- live 请求前必须完成输入/标签隔离、版本/hash、预算预留、raw 路径和零副作用拒绝测试。

### handoff_self_check

```text
changed=scope prompt, A2 checkpoint, project status/plan/worklog（准备阶段）
commands=待 CC 认领后填写
confirmed=A1 d6faf70 已合入 main；A2 尚无 batch/授权；FORMAL_EVALUATION_ALLOWED=False
unresolved=受控入口实现、预算数字、唯一 batch_id、负责人授权、live preflight
next_agent_focus=核对 adapter→pipeline 接口和正式 gate，先完成离线测试再申请授权
```
