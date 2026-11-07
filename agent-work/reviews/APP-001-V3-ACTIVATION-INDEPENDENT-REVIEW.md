# APP-001 extraction v3 独立复核

- 日期：2026-11-07
- 复核者：Codex 中枢
- 复核对象：`cc/APP-001-DECISION-POLICY-V3-DRAFT`
- 候选激活提交：`6260cd3`
- closeout 文档提交：`ceb5fdb`
- 当前结论：`review`，建议保留 v3 方向，但先补历史 v2 只读解析兼容，再合入 `main`

## 复核范围

核对生产版本常量、冻结 prompt loader、parser 版本门、FormalRunAuthorization scope、acceptance-set 哈希、候选策略与生产 prompt 的内容关系、旧批次可审计性、测试证据和正式运行边界。本次没有真实模型请求，没有读取密钥，没有修改 `work/app001-runs/`。

## 已确认通过

1. `PROMPT_VERSION`、`FROZEN_PROMPT_VERSION` 和生产 prompt envelope 一致，均为 `app001-extraction.v3`。
2. 生产 prompt 位于 `agent-work/llm/APP-001-v3-activation/prompt-v3.md`，文件 SHA-256 为 `3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`；候选源保持未修改，SHA-256 为 `e90ad55ca20cf356c3c143a723da271f1874eb9fa902dd1379d4afba657a8b5b`。
3. `acceptance-set-v0.json` 未改，SHA-256 仍为 `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`。其 `frozen_prompt_version=app001-extraction.v2` 是冻结时的历史元数据；当前 projection 不把该字段注入模型输入。
4. `FORMAL_EVALUATION_ALLOWED` 仍为 `False`；36 个逻辑运行、108 次物理 HTTP、重试上限、C2/IR/CAD/geometry/STEP 禁用范围均未改变。
5. v3 prompt 的目录表、`second_screw` 阈值、不支持项证据、主张保留和 retrieval reference 隔离均由候选专项测试覆盖；生产 prompt 去除了候选/未激活元说明。
6. Python 3.11.18 下定向 153 项、LLM 全量 572 项（8 个既有 FUSE skip）、Schema 17 项通过；旧版本 envelope 的拒绝路径也有测试。

## 阻塞问题：历史 v2 原始响应的程序化只读复核

现行 `src/llm/parser.py::parse_response()` 只接受当前 `contract.PROMPT_VERSION`。切到 v3 后，对现有 `work/app001-runs/app001-phase1-20261107-03` 的 32 个 v2 原始响应逐条统计结果为：

```text
raw_version_counts = {'app001-extraction.v2': 32}
first_legacy_parse_ok = False
first_legacy_errors = ['PROMPT_VERSION_MISMATCH']
```

这意味着任何未来使用生产 parser 重解析旧批次的审计/回归脚本都会把历史 v2 响应当成 v3 协议错误。旧批次仍然可以人工读取原始 JSON，但“只读保留、可审计”缺少稳定的程序化入口。当前测试只覆盖“旧 v2 响应在 v3 默认 parser 中被拒绝”，没有覆盖历史兼容解析。

### 建议的窄范围修复

保持 `parse_response()` 默认严格接受当前 v3，避免新运行混入旧协议；新增显式版本化入口（例如 `parse_response_for_version(raw, prompt_version="app001-extraction.v2")`，或等价的内部 parser 参数）供只读审计使用。该入口必须：

- 只允许明确列入的历史版本 `app001-extraction.v2`；
- 使用同一 `app001-io.v1` envelope/schema 检查；
- 不改变默认 v3 parser 的拒绝行为；
- 在结果/调用方记录实际 prompt version，禁止把 v2 结果标记成 v3；
- 增加一个 v2 正常案例、一个 v2 失败案例、v3 默认拒绝 v2 的回归测试；
- 不连接 runner 的正式路径，不打开 gate，不重写旧批次。

## 决策

建议：**继续采用 v3，并在合入前完成上述历史解析兼容修复和测试。** 不建议因为该兼容问题回退 v3；也不建议直接把 parser 改成无条件接受 v2/v3，因为那会削弱新运行的版本边界。

在兼容修复、Python 3.11.18 全量回归和中枢复核完成前，v3 激活分支保持 `review`，不合入 `main`，不启动新的正式模型批次。兼容修复通过后，才进入合入；若要测 v3 效果，再另行取得唯一正式批次授权。
