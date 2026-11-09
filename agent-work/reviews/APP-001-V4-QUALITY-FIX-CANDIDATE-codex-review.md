# APP-001-V4-QUALITY-FIX-CANDIDATE — Codex 独立审查

日期：2026-11-09  
候选提交：`1a0bd94`  
基线：`b1a31b9`  
审查状态：**review，暂不合并/激活**

## 已确认通过

- 候选文件仅新增 checker、测试和交付记录；相对 `b1a31b9` 未修改生产 v4、parser、adapter、runner、contract、prompt、Schema、预算、授权或旧批次。
- `/opt/homebrew/bin/python3.11` 为 Python 3.11.18。
- `PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_decision_policy_v5_candidate -q`：51/51 通过。
- 定向回归实际以 unittest 重跑：191 通过、6 skipped；输出中的 abort 均为测试设计的负路径，不是测试失败。
- `git diff --check` 通过；正式批次目录未被修改。
- `src.llm.decision_policy_v5_candidate` 下的正常案例 `bore_d=24, decision=answer` 通过，A02/C1 refuse 和 A05 overlap 反例可被 checker 检出。
- 候选没有真实模型调用、网络访问或密钥读取证据，`FORMAL_EVALUATION_ALLOWED` 和生产 v4 版本未改变。

## 阻塞问题

### 1. 正式导入路径失败

执行：

```text
PYTHONPATH=src /opt/homebrew/bin/python3.11 -c \
  'import llm.decision_policy_v5_candidate'
```

结果：`ImportError: attempted relative import beyond top-level package`。

`src/llm/decision_policy_v5_candidate.py:47` 使用 `from ..schema...`，而项目正式运行/测试入口使用 `PYTHONPATH=src` 下的顶层 `llm` 和 `schema` 包。专项测试在 `tests/llm/test_decision_policy_v5_candidate.py:63` 使用 `src.llm` 导入，因此没有覆盖正式导入路径。候选 checker 至少应在项目约定的 `PYTHONPATH=src` 入口可导入，并补一个直接导入测试。

### 2. 确定性目录/规则冲突未实现

任务 prompt 要求 `decision=answer` 不得与确定性目录/规则冲突共存。当前 `_check_p2()` 只检查：

- `missing_fields` 与 `extracted_parameters` 重叠；
- `answer` 与非空 `missing_fields`/`unsupported_requests`；
- `missing_fields` 重复。

它没有检查 `bore_d=20, outer_d=40` 的目录冲突，也没有检查 `bore_d=80, second_screw=0` 的规则冲突。实际反例：

```text
decision=answer,
extracted_parameters={bore_d: 20, outer_d: 40},
missing_fields=[], unsupported_requests=[]
→ 当前 checker: ok=True

decision=answer,
extracted_parameters={bore_d: 80, second_screw: 0},
missing_fields=[], unsupported_requests=[]
→ 当前 checker: ok=True
```

这与候选任务中的“或确定性冲突”要求不一致。请在不导入 adapter/parser/runner 的前提下，补充最小的目录行/`second_screw` 冲突判定和反向测试，或明确缩小候选规格并同步策略文档；不能继续把当前 51 项测试称为完整 P2 验收。

## 需要补的边界测试

- `bore_d=24.0` 应按当前 Schema 的数值归一化规则识别为合法目录值；当前 `_is_catalog_bore_d()` 只接受 `int`。
- measurement object 形式如 `{"value": 1.6, "unit": "cm"}` 应按 Schema 归一化为 16 mm，不能被 checker 静默当作非目录值。
- 用 `PYTHONPATH=src` 运行专项测试或增加独立 import smoke test，避免测试只在 `src.llm` 命名空间下通过。

## 结论和下一步

候选的已确认三条过度拒绝和 A05 字段重叠检测方向正确，但本轮交付不能标记 `done`。状态保持 `review`，不合并到 `main`，不激活 v5，不创建新正式 `batch_id`。CC 需做一次窄范围修正并提交后，再由 Codex 重跑上述导入、冲突、float/单位和专项回归检查。

本审查未启动任何模型请求，未读取或打印 API key，未修改 `work/app001-runs/app001-phase1-v4-20261109-01/`。
