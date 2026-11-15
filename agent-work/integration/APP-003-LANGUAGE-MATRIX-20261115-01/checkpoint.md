# APP-003-LANGUAGE-MATRIX-20261115-01 checkpoint

- 日期：2026-11-15
- 状态：review
- 目标：基于既有失败路径及语言覆盖计划，形成下一轮全新中文语言样本设计；本轮只整理离线候选，不创建 batch、不运行 preflight、不调用模型/网络/CAD、不读取凭据或历史 raw 正文。
- 基线：`main=b791f52`（本地 ahead origin/main 1）；工作分支 `codex/APP-003-LANGUAGE-MATRIX-NEXT-DRAFT`。

## 产物

- `model-inputs.json`：10 条新候选输入，scope id `app003-product-language-next.v1`。
- `evaluator-labels.json`：独立 evaluator-only 标签；只供后续评审，不得进入模型侧流程。
- `scope.md`：目标、边界、接受标准、预算建议和后续 gate。
- 当前草案 SHA-256：inputs `66b61a476b16d79030bced380f1afbc4d907c05ec2aae984e4e1777dda5d26ed`；labels `f5689bed99d77ee6f92a4a11752c96c801059d9ec75f381b1c22c61ffc9801ec`。

## 已核对

- 阅读 `AGENTS.md`、PROJECT_STATUS、PROJECT_PLAN、DECISIONS、WORKLOG、handoff review protocol 和 project memory playbook。
- 核对既有十条样本、产品 live 的 P1–P4、ADR-0024、`src/schema/set_screw_shaft_collar.py` 当前目录与 `second_screw` 严格阈值规则。
- 新样本以表达/语义现象为主，避免复制旧句子；范围仍是 DeepSeek `deepseek-flash`、C0、无检索和当前单一零件族。
- 旧 `product_language.v1` profile 固定绑定旧输入 hash；本候选没有复用授权、batch 或 preflight。

## 验证与限制

- `PYTHONPATH=src:. python3` JSON/ID顺序/数量/输入与labels物理分离校验通过；Schema 定向核对 N01=30 mm、N02=70 mm/单螺钉合法、N03=80 mm/单螺钉冲突拒绝、N10 派生 width=12 mm 均通过；`git diff --check` 通过。
- 已对照 schema 确认目录 30 mm、bore_d=70 的 second_screw=0、bore_d=80 的 second_screw=1、bore_d=12 的派生 width=12；此为规格静态核对，不是模型抽取或 CAD 测试。
- 尚未实施 profile/runner，也未运行测试或 preflight；本候选不构成冻结 scope、真实模型效果证据或执行授权。
- 历史 batch 保持只读；`FORMAL_EVALUATION_ALLOWED=False`。

## handoff_self_check

```text
changed=本目录新增 model-inputs.json、evaluator-labels.json、scope.md；PROJECT_STATUS/PROJECT_PLAN/WORKLOG 同步
commands=PYTHONPATH=src:. python3 JSON/ID/order/separation/hash validation PASS; schema rule checks N01/N02/N03/N10 PASS; git diff --check PASS
confirmed=候选 10 条输入与独立标签已形成；不复用旧授权 profile 或 batch；没有真实模型/CAD运行
unresolved=输入和标签仍待负责人/独立复核；尚未实现新 profile/runner
next_agent_focus=逐条检查标签是否符合现行 v5 contract 和 CAD-003规则；确认 N08/N09 物理配合口径；验证标签不进入任何模型可读路径；不执行 live
```
