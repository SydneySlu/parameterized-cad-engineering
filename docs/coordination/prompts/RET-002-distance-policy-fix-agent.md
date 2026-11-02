# RET-002 修正 Prompt：冻结距离策略范围契约

你是“参数化 CAD 工程辅助设计”项目的 RET-002 修正 Agent。你的任务是修复 Codex 中枢在 RET-002 独立审查中发现的一个策略契约问题：调用方可以通过 `RetrievalIndex.from_manifest(..., policy=...)` 传入自定义连续字段范围，而实现仍输出冻结的 `RET-002.parametric_distance.v1`，导致距离语义可以在不改变 policy id 的情况下被绕过。

本轮只修正这个问题，不重做 RET-002，不扩展检索功能。

## 1. 项目根目录与启动检查

必须在 Git 根目录工作：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
git log --oneline -8
```

开始前必须阅读：

```text
AGENTS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/WORKLOG.md
docs/DECISIONS.md
docs/TASKS.md
docs/coordination/handoff-review-protocol.md
agent-work/reviews/RET-002-codex-review.md
agent-work/integration/RET-002-retrieval-baseline/README.md
agent-work/integration/RET-002-retrieval-baseline/checkpoint.md
agent-work/integration/RET-002-retrieval-baseline/handoff.md
src/retrieval/config.py
src/retrieval/distance.py
src/retrieval/baseline.py
tests/retrieval/test_retrieval_baseline.py
```

RET-002 是已完成过续任复核的高风险数据/检索交接。开始修改前必须完成定向复核：

1. 重跑 RET-002 单元测试或 `run_smoke.py` 至少一条核心命令；
2. 检查一个正常查询和一个失败查询；
3. 确认 RET-001 `--tracked-only`、`provisional_small_n`、candidate roles 和 manifest hash 仍保持原状；
4. 若当前提交与审查记录不一致，先记录 `review` 或 `blocked`，不要覆盖前序成果。

## 2. 必须解决的问题

当前问题由以下行为构成：

```python
ranges = catalog_ranges()
ranges["bore_d"] = (0.0, 1.0)
DistancePolicy(ranges=ranges).validate()  # 当前错误地允许
```

随后索引仍会输出：

```text
policy_id=RET-002.parametric_distance.v1
```

这不符合 RET-002 的冻结策略。当前策略要求：

- 连续字段必须是 `bore_d`、`outer_d`、`screw_d`、`screw_len`、`width`；
- 范围必须等于完整 15 行 GN 705 目录范围，即 `catalog_ranges()`；
- 连续字段权重必须为 `0.2`；
- `second_screw` 离散权重必须为 `0.5`；
- 仍使用 policy id `RET-002.parametric_distance.v1`；
- 任何改变范围或权重的实验都必须建立新的策略版本并经过中枢审查，不能从当前公共入口静默改变。

## 3. 实现要求

在现有结构中选择一个最小、可审计的修正方式：

### 推荐方式

让 `DistancePolicy.validate()` 同时校验每个连续字段的 `(min, max)` 必须与 `catalog_ranges()` 完全一致。范围比较应明确处理数值类型和浮点值，不接受通过整数/浮点混写、NaN、无穷值或近似值绕过检查。

自定义范围必须抛出已有的结构化 `RetrievalError`：

```text
code=RETRIEVAL_CONFIG_INVALID
stage=config
fields=<包含对应连续字段>
```

如果你认为移除 `from_manifest(..., policy=...)` 覆盖入口更安全，也可以采用该方案，但必须保持现有默认构造和 `from_config()` 接口可用，并在 checkpoint 中说明理由。不要引入新的 policy id、学习权重或 RET-003 逻辑。

## 4. 必须增加的回归测试

至少增加以下测试：

1. 修改 `bore_d` 范围后，`DistancePolicy.validate()` 返回结构化 `RETRIEVAL_CONFIG_INVALID`；
2. 修改任一其他连续字段范围后同样拒绝；
3. 正常的 `catalog_ranges()` 仍可创建索引并保持现有查询结果；
4. `from_config(retrieval-config.json)` 仍成功；
5. 现有 tie-break、候选角色过滤、manifest hash、正常/边界/失败查询测试继续通过。

不要修改测试来降低验收标准，也不要把自定义范围改成“实验模式”继续挂在当前 policy id 下。

## 5. 文件边界

允许修改：

```text
src/retrieval/**
tests/retrieval/**
agent-work/integration/RET-002-retrieval-baseline/checkpoint.md
agent-work/integration/RET-002-retrieval-baseline/handoff.md
agent-work/integration/RET-002-retrieval-baseline/README.md
docs/WORKLOG.md                         # 只追加
```

不要修改：

```text
src/schema/**
src/cad_compilation/**
agent-work/data/RET-001-retrieval-manifest/**
agent-work/typed-cad-ir/**
agent-work/cad-validation/**
docs/DECISIONS.md
docs/PROJECT_STATUS.md
docs/PROJECT_PLAN.md
docs/TASKS.md
database/**
```

不要读取、生成、提交或公开 STEP、渲染图、第三方图纸或 BenchCAD Public/Core 数据。

## 6. 验证命令

至少运行并记录以下命令：

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"

PYTHONPATH=src work/benchcad-output/venv/bin/python \
  -m unittest discover -s tests/retrieval -v

PYTHONPATH=src work/benchcad-output/venv/bin/python \
  agent-work/integration/RET-002-retrieval-baseline/run_smoke.py

PYTHONPATH=src:work/benchcad-source/api-snapshot-035f467/framework:work/benchcad-source/api-snapshot-035f467 \
  work/benchcad-output/venv/bin/python \
  agent-work/data/RET-001-retrieval-manifest/generator/verify_manifest.py \
  --tracked-only

work/benchcad-output/venv/bin/python -m py_compile src/retrieval/*.py
git diff --check
```

预期至少包括：

- RET-002 测试全部通过，原有 24 项不减少；
- smoke 的正常、边界、失败和确定性检查全部通过；
- RET-001 tracked-only 仍为 660 项、0 失败；
- 自定义范围的新增测试得到结构化拒绝；
- `provisional_small_n`、3 个候选、manifest hash、单环境和许可证限制没有被改写。

若验证命令改写带时间字段的报告，测试完成后恢复无关的运行时差异，不要把时间戳更新当作交付内容。

## 7. 交接要求

任务完成后保持 `review`，不要标记 `done`，不要 push。提交一个修正 commit，格式建议：

```text
fix: enforce frozen retrieval distance ranges [RET-002]
```

在 checkpoint/handoff 中记录：

- 修改了哪些文件；
- 修正前的可绕过行为和修正后的拒绝行为；
- 所有实际运行的命令及结果；
- 一个正常查询、一个失败查询和一个自定义范围失败案例；
- manifest hash、candidate roles、split 状态和所有限制；
- 是否读取或生成 STEP/渲染物；
- 尚未解决的问题和下一 Agent 关注点。

修正完成后由 Codex 中枢重新审查。只有中枢确认策略范围不可绕过，RET-002 才能标记 `done`，随后再决定是否放行 RET-003。
