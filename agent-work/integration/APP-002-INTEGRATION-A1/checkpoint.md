# APP-002-INTEGRATION-A1 checkpoint

## 当前事实

- 日期：2026-11-11；状态：planned。CC尚未认领或实现，不代表已启动后台任务。
- 负责人：CC（Schema/CAD连接层实现）；独立验收：当前Codex中枢。
- 代码核验基线：main=993a5b1；本轮中枢只改决策/计划/交接文档，工作启动时干净、ahead12。执行者需核对实际HEAD与工作区，不用聊天快照替代Git。
- 决策：ADR-0020 accepted，优先A/B/C闭环；v5冻结为集成基线；12-run检索研究真实执行deferred。
- 首工作包：需求文本+synthetic v5 envelope→严格gate→Schema→正式IR映射→真实本地CAD/几何/STEP与运行关联。真实模型整链属于A2，未授权。

## 输入与产物

输入：冻结v5/app001-io.v1合成envelope、原需求文本、已有Schema/IR规范和CAD公共接口。
产物：src正式参数到IR adapter、隔离离线pipeline/CLI、缺失集成测试、用法、证据索引；运行文件位于ignored work/integration-runs，不提交STEP/大型产物。

接口重点：原始单位与user/catalog/rule来源；missing_fields及unsupported构造门；真实Schema重验；acceptedIR不是最终成功；step_readback及本次文件hash；失败无发布STEP、无旧文件串档。

## 已完成中枢准备

- 读取最新项目与三层交接/记忆协议，并核实历史v5真实响应和后端最终修复记录。
- final offline preflight在993a5b1 pass（12组合，global44，Ollama26，冻结索引有效，无目录），只使用review-only标识。
- 固定环境实测CAD13、Schema/IR22、v5相关161项通过；7个合成接口探针包含合法/单位/70与80/缺参/冲突/unsupported，正常与拒绝符合预期。
- 证据：agent-work/reviews/APP-001-V5-INTEGRATION-BASELINE-preflight.md。
- 具体执行指令：docs/coordination/prompts/APP-002-INTEGRATION-A1-cc.md。

## 未完成与下一步

CC按工作prompt执行启动复核并记录handoff_successor_check，然后依M1映射与门禁→M2真实本地STEP→M3交付实现。实现后review，中枢按高风险接口double check独立验收；仅合入且验收通过后done。A1之后准备A2真实模型新scope/输入/预算/batch/授权；不以heldout实验替代整链。

## 边界

不改冻结prompt、Schema/IR策略、CAD规则、provider/预算/授权；FORMAL_EVALUATION_ALLOWED=False。无模型/HTTP、live preflight、密钥/.env/历史raw正文读取；历史批次只读。合成提取不能写成真实语言理解；模块成功不能写成真实模型整链。固定环境、单族、螺纹近似、来源许可及非制造认证限制保留。

```text
handoff_self_check:
  changed=中枢资产核验/ADR/计划/工作prompt；无A1代码实现
  commands=参见preflight报告的实际命令与结果；CAD13、Schema/IR22、v5相关161、7个合成探针
  confirmed=单族模块可复用；缺正式连接层；研究离线门通过且真实执行deferred
  unresolved=CC实现与独立验收待做；真实模型整链not_run
  next_agent_focus=先完成续任正常/失败复核，再实现gate/provenance/canonical IR/隔离与最终成功语义
```
