# APP-001-RUNNER-R3-FIX-R2 handoff

**日期**: 2026-11-06  
**任务**: APP-001-RUNNER-R3-FIX-R2  
**状态**: review  
**分支**: cc/APP-001-RUNNER-R3  

---

## 自检清单

```yaml
changed:
  - src/llm/budget.py        # 移除 temp 豁免，token 绑定增强
  - src/llm/real_transport.py # token 验证消费，tags/chat 分离
  - src/llm/runner.py        # C1 索引完整身份验证
  - tests/llm/test_budget.py # 规范批次目录适配，6 个 FUSE skip
  - tests/llm/test_runner.py # 规范批次目录适配
  - tests/llm/test_runner_r1.py # 规范批次目录，1 个 FUSE skip，snapshot 前移至 with 块
  - tests/llm/test_r3_fixes.py  # 新建：19 项 R3-FIX 针对性测试
  - tests/llm/test_runner_r3.py # 新建：12 项 R3 核心验证测试
  - agent-work/llm/APP-001-runner-R3/checkpoint.md
  - agent-work/llm/APP-001-runner-R3/handoff.md
  - docs/WORKLOG.md

commands:
  - discover tests/llm: Ran 357, 2 pre-existing FUSE errors, 8 FUSE skips
  - discover tests/schema: Ran 17, OK
  - py_compile budget/real_transport/runner: OK
  - git diff --check: OK
  - test_r3_fixes: 19/19 OK
  - test_runner_r3: 12/12 OK

confirmed:
  - 临时目录被 BudgetIntegrityError 拒绝（无豁免开关）
  - 规范路径 work/app001-runs/<batch_id>/ 被接受
  - 无预算凭证时 0 次 urlopen (mock 验证)
  - 伪造 token、重放 token、provider/model/endpoint 错配均在 urlopen 前拒绝
  - Ollama tags 和 chat 各有独立 token 和预留
  - 无索引、MagicMock、错误 sha256/path/version/policy 均在 HTTP 前拒绝
  - 真实冻结 RetrievalIndex 通过身份门
  - FORMAL_EVALUATION_ALLOWED=False 未改变
  - 无真实 API 调用，无密钥读取

unresolved:
  - 2 个 pre-existing FUSE symlink 错误（test_r3_regression.RetentionBypassRemovedTests）
  - 8 个 FUSE 锁文件删除限制 skip（在 macOS 原生文件系统可以运行）
  - Ollama 18 次 tags 预检消耗 provider 配额，实际可用 chat 次数 ≤ 36
  - Codex 中枢独立审查仍是正式运行前置门

next_agent_focus:
  - 审查 budget token 绑定是否足够防止绕过（特别是 endpoint 绑定逻辑）
  - 审查 C1 索引路径验证是否在跨平台场景（Windows 路径分隔符）稳健
  - 审查 Ollama tags 预检不占用模型调用计数是否有明确测试证明
  - 确认 FUSE skip 的 6 个测试逻辑在原生文件系统下是正确的
```

---

## 预算口径说明

物理 HTTP 请求（总计 ≤ 108，每 provider ≤ 54）：
- DeepSeek: 每次 POST /chat/completions = 1 次物理请求
- Ollama: 每次 GET /api/tags = 1 次物理请求 + 每次 POST /api/chat = 1 次物理请求

模型调用计数（每 logical run ≤ 3 次）：
- 仅 POST /api/chat（Ollama）和 POST /chat/completions（DeepSeek）算模型调用
- GET /api/tags 不算模型调用，但消耗 provider 物理 HTTP 配额

Ollama 极限场景分析：
- 18 个 Ollama run，每个 run 需要 1 次 tags + 最多 3 次 chat = 最多 4 次物理请求
- 18 × 4 = 72 > 54（provider 限额）
- 实际上：18 次 tags 已占 18，剩余 54 - 18 = 36 次 chat，最多支持 36 次 chat = 12 个 run（每个 3 次重试）或 36 个 run（每个 1 次）
- tags 在第一次 send 时执行，后续 send 使用缓存的 verified_digest，不再发 tags 请求

---

## 结果

R3-FIX-R2 全部四项修复已实现、测试覆盖。状态保持 review，等待 Codex 中枢独立验收。未 push。
