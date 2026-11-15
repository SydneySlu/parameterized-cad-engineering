# APP-003-LANGUAGE-MATRIX-20261115-01 checkpoint

- 日期：2026-11-15
- 状态：review
- 目标：基于既有失败路径及语言覆盖计划，形成下一轮全新中文语言样本设计；本轮只整理离线候选，不创建 batch、不运行 preflight、不调用模型/网络/CAD、不读取凭据或历史 raw 正文。
- 基线：`main=b791f52`（本地 ahead origin/main 1）；工作分支 `codex/APP-003-LANGUAGE-MATRIX-NEXT-DRAFT`。

## 产物

- `model-inputs.json`：10 条新候选输入，scope id `app003-product-language-next.v1`。
- `evaluator-labels.json`：独立 evaluator-only 标签；只供后续评审，不得进入模型侧流程。
- `scope.md`：目标、边界、接受标准、预算建议和后续 gate。
- 当前草案 SHA-256：inputs `66b61a476b16d79030bced380f1afbc4d907c05ec2aae984e4e1777dda5d26ed`；labels `f812a3fb9c83bcc23785083f8bfd89ba968de94a3bc9ea92f991722760001b48`。

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

## Codex review pass

- 对草案做了第二轮口径检查，将 evaluator 标签拆为 `preferred_decision` 与 `acceptable_decisions`，避免把安全 `ask` 和最佳抽取混为一谈；负向样本仍必须在 CAD 前阻断。
- 自我更正样本允许 answer 或保守 ask；只有明确采用最终 12 mm 并经负责人确认时才允许构造。N08/N09 的轴径属于上下文事实，不伪装成 Schema 参数字段；N10 的宽度下限属于请求约束，解析出的 `width` 仍为目录派生。
- 本轮审查仅为同一 Codex 的复核精炼，不声称是独立审查。labels hash 已更新；其它范围和禁止项不变。

## Independent review refinement

- 日期：2026-11-15；状态继续为 `review`，本轮只修候选 scope/labels 口径，不冻结矩阵、不授权 preflight 或 live 请求。
- 输入：独立复核结论 `review`，要求修正 scope 中过期的 labels SHA、明确 evaluator 字段映射、分开安全可接受与当前 v5 策略通过，并特别核验 N04 的更正值和 N08/N09 的策略覆盖边界。
- 修改：`scope.md` 更新为 labels SHA-256 `9ca60bd3b91a260a8ad71bfd9c1433f8f0150260a0baf3935d51c8036726ee14`；`evaluator-labels.json` 声明单位化标签到 v5/Schema 字段的映射，并为每条输入分列安全决策/门与 v5 策略评估。N01/N02/N04/N10 的 `ask/refuse` 标为安全可阻断但属于 P1-1 over-refusal；N05–N07 标为部分强制（checker 只拒绝已识别 unsupported 后仍 answer，不保证识别本身）；N08/N09 明确标为当前策略未定义、不计策略分，同时仍要求 CAD 前安全阻断。N04 增加最终构造参数必须 `bore_d=12` 且排除 superseded `10` 的断言。
- 范围：没有修改输入、prompt、Schema、IR、provider、runner、profile、授权或历史批次；没有创建 batch、运行 preflight、调用模型/网络/CAD，也没有读取凭据或历史 raw 正文。`FORMAL_EVALUATION_ALLOWED=False` 未改变。
- 验证：JSON 解析、ID 顺序/数量、输入与 evaluator labels 文本隔离、v5 策略分类、字段映射、N04 正反值断言、scope hash 与文件 hash 一致性检查通过；`git diff --check` 通过。未运行测试套件或任何执行路径。
- 未解决：矩阵仍待独立复核和负责人接受；N08/N09 暴露的策略能力缺口不在本轮修补，需未来单独决策是否修改 v5 策略或将安全识别放在另一层。
- 下一步：独立复核更新后的 labels/scope 口径；复核通过且负责人接受后，才讨论新版本化 profile 与离线测试。
