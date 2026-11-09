# APP-001-V4-QUALITY-FIX-CANDIDATE R1 — Codex 独立复核

日期：2026-11-09  
提交：`d706639`  
前序审查修正记录：`18941af`  
状态：**review 通过离线候选 gate；未合并、未激活**

## 实际复核

解释器：`/opt/homebrew/bin/python3.11`，Python 3.11.18。

```text
/opt/homebrew/bin/python3.11 -m py_compile src/llm/decision_policy_v5_candidate.py tests/llm/test_decision_policy_v5_candidate.py
→ 通过

PYTHONPATH=src /opt/homebrew/bin/python3.11 -c 'import llm.decision_policy_v5_candidate as m; print(m.CANDIDATE_VERSION)'
→ app001-extraction.v5-candidate

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_decision_policy_v5_candidate -q
→ Ran 78, OK

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest \
  tests.llm.test_decision_policy_v4_candidate \
  tests.llm.test_decision_policy_v3_candidate \
  tests.llm.test_authorization tests.llm.test_parser \
  tests.llm.test_budget tests.llm.test_run_script_v4_batch -q
→ Ran 191, OK (skipped=6)

git diff --check
→ CLEAN
```

专项和定向回归均使用当前工作区实际重跑；6 个 skip 为既有 FUSE 环境限制。没有依赖未安装的 pytest 作为唯一证据。

## 关键案例

- 正常：`answer + bore_d=24 + empty missing/unsupported` → `ok=True`。
- P1-1：`A02/A08 C1 refuse + bore_d=24` → `P1-1`。
- P2-5：`answer + bore_d=20 + outer_d=40` → `P2-5`；`answer + bore_d=80 + second_screw=0` → `P2-5`。
- 合法冲突处理：A05/A09 的 `ask`/`refuse` 不再被 P1-1 误报。
- 归一化：`24.0 → 24`，`{"value": 1.6, "unit": "cm"} → 16`；未知单位、非有限值、分数毫米不被当作合法目录值。
- 生产入口：`PYTHONPATH=src` 下顶层 `llm` 导入成功；候选仍未被 adapter/parser/runner/contract/prompt_loader 导入。

## 边界核对

- 仅修改候选 checker、测试、checkpoint/handoff/strategy 和工作日志。
- `prompt-v4.md`、生产 `src/llm` 运行模块、Schema、预算、授权、`FORMAL_EVALUATION_ALLOWED` 未改变。
- 旧批次 `work/app001-runs/app001-phase1-v4-20261109-01/` 未修改。
- 未调用 DeepSeek/Ollama、未读取或打印 API key、未创建正式批次。

## 结论

R1 已关闭前一轮审查的导入、P2-5 和数值归一化阻塞，离线候选 gate 通过。该结论不等于 v5 模型效果通过，也不等于生产激活。候选分支仍需项目流程决定是否合并；若要继续，下一工作单元应是独立的 v5 prompt 候选/激活准备，随后再申请新的唯一 `batch_id` 和正式授权。
