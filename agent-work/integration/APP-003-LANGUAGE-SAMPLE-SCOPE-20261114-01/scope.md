# APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01 候选范围

状态：`review` 草案；尚未批准、不可执行。日期：2026-11-14。

## 假设与目标

窄测十种中文表达是否保持关键抽取安全性：明确值、单位换算、离散目录冲突、缺参、unsupported、近边界值、混合支持/unsupported、备选歧义和模糊需求。核心风险指标是关键参数误抽/错误放行，以及 ask/refuse/解析失败是否误入 CAD。此轮只评估当前 v5 与现有确定性 gate，不比较 prompt、模型、检索或零件族。

## 冻结候选配置

- Provider/model：DeepSeek `deepseek-flash`
- Condition：C0，无检索
- Prompt/contract/Schema/IR：沿用当前已激活冻结版本；scope 冻结前记录精确 hash
- 零件族：`set_screw_shaft_collar`
- 输入数：10 条独立语言需求，详见同目录 `model-inputs.json`
- 标签：单独文件 `evaluator-labels.json`；不得传入 prompt、transport、UI、summary 或执行 adapter
- CAD：模型抽取结束后默认不自动构造；只有 answer 且逐条负责人审阅/确认后，才允许该 run 的 CAD confirmation
- 重试：每条最多 2 次 HTTP 总尝试（初次+最多 1 次重试），仅连接/读取超时、连接中断、HTTP 429/5xx；认证/权限、错误请求、无效 JSON、输出契约或 Schema/规则拒绝不重试
- HTTP 预算：总上限 20（10 条×2 次）；每个请求必须预留账本额度
- 旧 batch：全部只读，不继承其预算、结果或授权

## 冻结输入与标签摘要

- `model-inputs.json` SHA-256：`8339431ee66a14d838cdbded48240019254182886c85af5cd611e04eaf361801`
- `evaluator-labels.json` SHA-256：`a5055025e4a01740b9bc25daa5ab51e43bdac9748151ccd10c152cdf7151bcf9`
- 两文件内容彼此独立；正式执行前由独立复核确认代码/summary/log 均不加载 evaluator labels。

## 执行前阻塞

当前 `ProductLiveAuthorization` / `product_live_runner` profile 固定绑定现有 P1–P4 的四条输入和输入 hash，并非通用十样本入口。不能把这份候选输入清单直接交给现有 runner 运行。需要先：

1. 评审十条输入及标签口径；特别确认 L02 0.8 英寸=20.32 mm 的离散目录拒绝/追问口径，及 L03/L06/L08/L09 的 evaluator 预期；
2. 若接受该矩阵，建立新的版本化产品语言评测授权 profile 与输入 hash 绑定，不修改或复用旧 profile；
3. 为新 profile 编写离线测试和 summary 隔离；独立复核、固定 CAD venv 回归；
4. 生成新 scope、batch ID、offline preflight；由负责人分别批准正式 preflight 和真实执行。

本候选文件不生成 batch ID，也不执行 preflight、模型、网络或 CAD。`FORMAL_EVALUATION_ALLOWED=False` 保持不变。
