# APP-001 extraction v4 activation review

日期：2026-11-08  
候选提交：`32caed6`  
审查范围：ADR-0017、v4 prompt/spec、离线 checker、冻结边界和回归测试。未激活、未调用真实模型。

## 结论

本候选**暂不通过 activation review**。v4 的规则方向和生产隔离正确，可以继续做一轮窄范围 checker 修正；ADR-0017 保持 `proposed`，生产继续使用 `app001-extraction.v3`，不得据此启动新模型批次。

## 已确认通过

- v4 候选只覆盖已观测的三类偏差：精确单位换算、用户值优先于不可信 retrieval、unsupported 规范标签。
- `75 mm` 的措辞已明确为“5–80 mm 数值边界内但不属于 15 个离散 selector 也必须拒绝”。
- `src/llm/decision_policy_v4_candidate.py` 未被 adapter、parser 或 runner 导入；生产 v3 路径未改。
- `contract.py`、`parser.py`、`prompt_loader.py`、`adapter.py`、`runner.py` 相对 `origin/main` 无差异。
- active v3 prompt SHA-256 仍为 `3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`。
- acceptance-set SHA-256 仍为 `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`。
- `FORMAL_EVALUATION_ALLOWED` 仍为 `False`，没有真实模型请求或密钥读取。

验证命令：

- v4 专项：18/18 通过
- v3 candidate：55/55 通过
- parser：41/41 通过
- LLM 全量：594 通过、8 个既有 FUSE skip
- Schema：17/17 通过
- `py_compile`、`git diff --check`：通过

## 必须修正的问题

### P1：retrieval 优先级测试不具备判别力

`V4FixtureCase` 接收 `retrieval_bore_value=20`，但 `evaluate_fixture()` 完全不读取该字段。测试因此无论实现是否错误地采用 retrieval 值都会通过；它不能证明“用户 `bore_d=24` 覆盖 retrieval `20`”。

激活前应二选一：

1. 删除该字段，并把 checker 的范围明确为“retrieval 不参与确定性选择”；或
2. 实现一个明确的离线选择函数，返回用户值优先的结果，并增加反向断言：用户值为 24、retrieval 为 20 时结果必须是 24；用户值缺失时不能复制 retrieval 值充当用户主张。

### P2：unsupported evidence quote 尚未由 checker 验证

当前 checker 验证 `阳极氧化/anodized -> anodizing`，但结果对象不携带或检查原文 quote。由于 v4 规范要求规范标签和原文证据同时保留，激活前建议增加最小 fixture assertion；若不增加，应在激活说明中明确该部分仅由 prompt 文案和模型输出审计覆盖。

## 激活边界

修正上述 checker 证据后，才能进入下一次独立 activation review。即使 activation review 通过，仍需单独的激活实现提交，整体更新版本常量、parser 版本检查、prompt loader 路径/哈希、manifest 和兼容性测试；真实效果测试必须使用新的唯一批次并重新取得正式授权。历史 v2/v3 批次不得回写或混合统计。
