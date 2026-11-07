# APP-001-V4-CHECKER-FIX Codex 独立验收

日期：2026-11-08
审查分支：`codex/APP-001-V3-DECISION-FIX-DRAFT`
审查基线：`3665293`；修正提交 `6d1f90a`；交接记录提交 `2c7d199`

## 结论

报告中的 P1/P2 修正已在当前工作区实现，目标用例通过，且没有触碰生产 v3 或冻结验收集。本轮接受为 **checker 修正和离线候选准备已完成**。P1/P2 关闭，可进入独立的 v4 激活实现工作单元；这不等于生产激活或模型评测授权。

## 代码复核

- `resolve_bore_precedence()` 返回显式用户 bore，不把 retrieval 值提升为用户主张；缺失用户 bore 时返回 `None`。
- `evaluate_fixture()` 调用上述函数；反向测试覆盖 retrieval=75 不可覆盖用户 24，以及缺失用户值时 retrieval=20/24 均不能令结果 answer。
- unsupported evidence fixture 把中文原词映射到规范标签 `anodizing`，保留原词 quote，并固定 source 为 `user_input`；空用户 unsupported 输入不会产生 evidence。
- checker 仍只在测试中导入，生产 adapter/parser/runner/contract/prompt_loader 不引用。

低优先级限制：同一规范标签的多种原词会按 canonical label 去重，因此例如同一 fixture 同时给出 `阳极氧化` 和 `anodized` 时只留第一条 quote。单一 unsupported 请求的原文保留符合本轮目标；若未来要求多次原文逐条审计，应另补规则和测试。

## 独立验证

初次复跑使用 Python 3.15.2 后，按项目固定基线再用本机 Python 3.11.18 复跑，两个环境结果一致。固定环境命令使用 `/opt/homebrew/bin/python3.11`：

- v4 checker：34/34 通过
- v3 candidate：55/55 通过
- parser：41/41 通过
- LLM 全量：610 通过，8 个既有 FUSE skip
- Schema：17/17 通过
- `py_compile`、`git diff --check`：通过

重新核对 active v3 prompt SHA-256=`3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`、acceptance-set SHA-256=`ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`，均与交付报告一致。

## Git 状态和后续

原有 0 字节 `.git/index.lock` 已在检查无活动 Git 进程并获项目负责人授权后删除。修正及流程手册提交为 `6d1f90a`，交接哈希记录为 `2c7d199`；工作区干净，分支尚未 push。

当前没有真实模型请求、密钥读取或历史批次变更。若启动 activation 实现，仍须独立核验 activation bundle 的 prompt hash、manifest、contract/parser/loader 升级、兼容性和回滚；真实效果仍需新的唯一批次和单独授权。
