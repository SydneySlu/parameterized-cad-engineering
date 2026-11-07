# APP-001-V4-CHECKER-FIX Codex 独立验收

日期：2026-11-08
审查分支：`codex/APP-001-V3-DECISION-FIX-DRAFT`
审查基线：`3665293` + 工作区未提交修正（`.git/index.lock` 存在，尚无本轮 commit）

## 结论

报告中的 P1/P2 修正已在当前工作区实现，目标用例通过，且没有触碰生产 v3 或冻结验收集。本轮可以接受为 **checker 修正已完成、等待 Git 提交和 Python 3.11.18 固定环境复核**。ADR-0017 仍保持 `proposed`；这次验收不等于 v4 activation review 通过，也不授权模型调用。

## 代码复核

- `resolve_bore_precedence()` 返回显式用户 bore，不把 retrieval 值提升为用户主张；缺失用户 bore 时返回 `None`。
- `evaluate_fixture()` 调用上述函数；反向测试覆盖 retrieval=75 不可覆盖用户 24，以及缺失用户值时 retrieval=20/24 均不能令结果 answer。
- unsupported evidence fixture 把中文原词映射到规范标签 `anodizing`，保留原词 quote，并固定 source 为 `user_input`；空用户 unsupported 输入不会产生 evidence。
- checker 仍只在测试中导入，生产 adapter/parser/runner/contract/prompt_loader 不引用。

低优先级限制：同一规范标签的多种原词会按 canonical label 去重，因此例如同一 fixture 同时给出 `阳极氧化` 和 `anodized` 时只留第一条 quote。单一 unsupported 请求的原文保留符合本轮目标；若未来要求多次原文逐条审计，应另补规则和测试。

## 独立验证

当前 Codex 主机实际为 Python 3.15.2（macOS），不等于项目固定复核基线 Python 3.11.18，也不等于交付报告声称的 Linux Python 3.10.12。复跑结果：

- v4 checker：34/34 通过
- v3 candidate：55/55 通过
- parser：41/41 通过
- LLM 全量：610 通过，8 个既有 FUSE skip
- Schema：17/17 通过
- `py_compile`、`git diff --check`：通过

重新核对 active v3 prompt SHA-256=`3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`、acceptance-set SHA-256=`ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`，均与交付报告一致。

## Git 状态和后续

工作区显示本轮四个文件有未提交改动；HEAD 仍是 `3665293`。`.git/index.lock` 是 0 字节文件，符合交付报告。按交接约束，本次没有删除锁，也没有尝试 add/commit/push。

待用户在本机处理 stale lock 并提交后，再对提交对象进行最终核对；之后若要宣称 v4 可激活，仍须另行完成明确针对 activation bundle（prompt hash、manifest、contract/parser/loader 升级、兼容性和回滚）的审查。当前没有真实模型请求、密钥读取或历史批次变更。
