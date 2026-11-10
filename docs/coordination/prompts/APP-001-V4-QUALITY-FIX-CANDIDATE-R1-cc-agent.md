# APP-001-V4-QUALITY-FIX-CANDIDATE-R1：窄范围修正

## 任务目标

修正 Codex 对提交 `1a0bd94` 的独立审查发现，仅完善未激活的离线 v5 候选 checker 和测试。当前候选仍处于 `review`，不得合并到 `main`、不得激活 v5、不得创建新正式批次。

执行者：CC
建议分支：继续使用 `cc/APP-001-V4-QUALITY-FIX-CANDIDATE`，从当前 HEAD `18941af` 继续。

## 开始前必须执行

在 `/Users/syd/Desktop/参数化 cad 工程辅助设计` 内工作，并阅读：

1. `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/WORKLOG.md`、`docs/DECISIONS.md`；
2. `docs/coordination/handoff-review-protocol.md`、`docs/coordination/project-memory-and-delivery-playbook.md`；
3. `agent-work/reviews/APP-001-V4-QUALITY-FIX-CANDIDATE-codex-review.md`；
4. 本文件的前序任务 prompt；
5. `src/schema/set_screw_shaft_collar.py`、`src/llm/decision_policy_v5_candidate.py` 及其测试。

先确认分支、HEAD、工作区和前序提交。写入 checkpoint 的 `handoff_successor_check`：重跑一条已有测试，并给出一个正常案例和一个拒绝/冲突案例。发现分支或交接事实不一致时先标记 `review`/`blocked`，不要覆盖前序结果。

## 本轮必须修正的问题

### R1-1：正式包导入兼容

项目正式入口使用 `PYTHONPATH=src`，模块应可通过：

```bash
PYTHONPATH=src /opt/homebrew/bin/python3.11 -c \
  'import llm.decision_policy_v5_candidate as m; print(m.CANDIDATE_VERSION)'
```

当前 `from ..schema...` 会报 `ImportError: attempted relative import beyond top-level package`。修正候选 checker 的导入方式，使其至少在项目约定的 `llm` 包入口下可导入；同时保留测试环境可用性。补充直接 import smoke test，不能只测试 `src.llm` 命名空间。

不要因此修改 `src/llm/__init__.py`、生产模块或包结构。

### R1-2：确定性目录/规则冲突

任务规格要求：`decision=answer` 不得与确定性 CAD-003 目录/规则冲突共存。候选 checker 需在不导入 adapter/parser/runner/contract/prompt_loader 的前提下，使用现有只读 `CATALOG_ROWS` 和规则实现最小判定：

- `bore_d=20, outer_d=40` → 目录冲突，`answer` 必须被判为违规；
- `bore_d=80, second_screw=0` → `second_screw` 规则冲突，`answer` 必须被判为违规；
- 正确的 A05 `ask`/`refuse` 和 A09 `ask`/`refuse` 不应被误报为 P1 过度拒绝；
- 不得改写、纠正或删除显式 claim，只返回可审计 violation；
- 不得把 checker 接入生产执行链，也不得复制 evaluator 标签到模型输入。

可以新增明确的 P2 rule id（例如 `P2-5`），但必须在 candidate-strategy、checkpoint、handoff 和测试中统一说明。

### R1-3：数值和单位边界

当前 Schema 会把下列输入归一化为合法目录值，checker 不能漏报：

- `bore_d=24.0` 应视为目录值 24；
- `bore_d={"value": 1.6, "unit": "cm"}` 应归一化为 16 mm；
- 合法 measurement object 的单位需按现有 Schema 支持的单位处理；非法单位或非有限值应保持不通过/不触发“合法目录值”判断。

不要导入 parser 或 contract 来绕过隔离；可复用 Schema 中已冻结的目录/单位事实，但候选 checker 仍须保持离线、纯函数和不改变输入。

## 允许修改的文件

只允许修改：

- `src/llm/decision_policy_v5_candidate.py`；
- `tests/llm/test_decision_policy_v5_candidate.py`；
- `agent-work/llm/APP-001-v4-quality-fix-candidate/candidate-strategy.md`、`checkpoint.md`、`handoff.md`；
- `docs/WORKLOG.md` 追加记录。

如需新增纯测试辅助文件，必须放在 `tests/llm/`，并在报告中说明。

禁止修改：

- `src/llm/adapter.py`、`parser.py`、`runner.py`、`contract.py`、`prompt_loader.py`、`providers.py`；
- 生产 `prompt-v4.md`、任何 v4/v3 冻结哈希、`acceptance-set-v0.json`、RET-002、CAD-003 规则源；
- ADR、预算、授权逻辑、`FORMAL_EVALUATION_ALLOWED`；
- `work/app001-runs/app001-phase1-v4-20261109-01/` 和所有旧批次。

## 最低测试要求

测试必须覆盖：

1. `PYTHONPATH=src` 下 `import llm.decision_policy_v5_candidate` 成功；
2. A02 C1 refuse、A03 C0 refuse、A08 C1 refuse 仍被 P1-1 检出；
3. A04 缺失、A07 越界/unsupported、A05/A09 的 ask/refuse 边界不被错误标成过度拒绝；
4. A05 answer + `outer_d` 冲突被 P2 新规则检出；
5. A09 answer + `second_screw` 冲突被 P2 新规则检出；
6. A05 正确 ask/refuse、A09 正确 ask/refuse 通过；
7. `bore_d=24.0` 和 `{"value":1.6,"unit":"cm"}` 的合法目录识别；非法单位/非有限值不被当作合法目录值；
8. v5 checker 仍不被 adapter/parser/runner/contract/prompt_loader 导入；
9. 输入 envelope 不被修改；不读取网络、`.env`、API key；
10. 一个正常案例和一个失败/拒绝案例在 checkpoint 中给出实际输出。

## 验证和交付

至少运行并如实记录：

```bash
/opt/homebrew/bin/python3.11 -m py_compile \
  src/llm/decision_policy_v5_candidate.py \
  tests/llm/test_decision_policy_v5_candidate.py

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest \
  tests.llm.test_decision_policy_v5_candidate -q

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest \
  tests.llm.test_decision_policy_v4_candidate \
  tests.llm.test_decision_policy_v3_candidate \
  tests.llm.test_authorization tests.llm.test_parser \
  tests.llm.test_budget tests.llm.test_run_script_v4_batch -q

PYTHONPATH=src /opt/homebrew/bin/python3.11 -c \
  'import llm.decision_policy_v5_candidate as m; print(m.CANDIDATE_VERSION)'

git diff --check
```

如使用 pytest，必须同时报告实际解释器和 pytest 是否可用；不能把未运行的命令写成通过。

提交前确认 `git status` 只有本任务文件，创建符合约定的 commit，并在报告中写明 commit、命令结果、skip、正常/失败案例和未解决问题。不得 push、合并、激活或运行任何真实模型批次。

## 完成定义

本轮只在上述窄范围问题全部有实际测试证据后提交。即使修正通过，也只能交给 Codex 独立复核；离线 checker 通过不代表 v5 模型效果通过，也不构成新批次授权。
