# APP-001-RUNNER-R3-FIX-R2 handoff（更新版）

**日期**: 2026-11-06
**任务**: APP-001-RUNNER-R3-FIX-R2（续任完成）
**状态**: review
**分支**: cc/APP-001-RUNNER-R3

> **2026-11-06 更新（R3-FIX-R3 续任）**: 本 handoff 仍由 R3-FIX-R2 产出，其自检清单
> 反映 R3-FIX-R2 完成状态。R3-FIX-R3 续任完成三项窄范围修正（详见
> `R3-FIX-R3-checkpoint.md`）：
> - Issue-2 修复 Ollama tags/chat token 消耗顺序（先 tags 后 chat）及 tags 失败时
>   chat outcome 记为 `blocked`（新增 `OllamaTagsPreflightError`）
> - Issue-3 改用 `RetrievalConfig.from_path()` 加载冻结配置 sha256，替代磁盘文件实时
>   hash
> - Issue-1 新增 transport 级 `@patch urlopen call_count==0` 测试（batch/provider/
>   model/endpoint 错配 + token 重放）
> - test_r3_fixes 25 → 35 项；全量 363 → 373；skipped=8 不变
> - 验证在 VM Python 3.10.12 通过；用户须在 Mac 用 python3.11 复核

> **2026-11-06 更新（R3-FIX-R6 续任）**: R3-FIX-R6 修复 BudgetLedger 进程内线程竞态：
> - `__init__` 新增 `threading.RLock(_thread_lock)`
> - `reserve_attempt`, `_claim_pending_reservation`, `record_outcome`,
>   `record_run_result` 四个方法加 `with self._thread_lock:` 保护
> - 新增 `TestR6TrueConcurrentClaimAtomicity`（2 项真实两线程竞态测试）
> - test_r3_fixes 49 → 51 项；全量 387 → 389；skipped=8 不变
> - 验证在 VM Python 3.10.12 通过；用户须在 Mac 用 python3.11 复核
> - 12 文件已暂存，`.git/index.lock` 阻塞 commit，需用户 `rm .git/index.lock`
>   后执行 `git add R3-FIX-R6-checkpoint.md && git commit`

---

## 自检清单

```yaml
changed:
  - src/llm/budget.py          # reserve_attempt 分离 HTTP/模型调用；_verify_integrity 更新；
                                # _verify_pending_reservation 新方法；BudgetAwareTransport.send() 更新
  - src/llm/real_transport.py  # _BudgetReservationToken weakref ledger；consume() ledger cross-check；
                                # OllamaTransport.send() tags/chat 检查顺序调整
  - src/llm/runner.py          # 精确 manifest_version；sha256 文件比较；policy.validate()；移除未用 import
  - src/retrieval/config.py    # 新增 MANIFEST_FORMAT_VERSION = "retrieval-manifest.v0"
  - tests/llm/test_r3_fixes.py # 25 项测试（原 19 项 + 6 新项）；更新 3 个现有测试
  - tests/llm/test_r3_regression.py  # 修复两个 symlink 测试（唯一 link 名 + FUSE 兼容清理）
  - docs/WORKLOG.md             # 追加本次结果
  - agent-work/llm/APP-001-runner-R3/R3-FIX-R2-checkpoint.md  # 新建

commands:
  - "PYTHONPATH=src python3 -m unittest discover -s tests/llm -q"
    result: "Ran 363, OK (skipped=8)"
  - "PYTHONPATH=src python3 -m unittest tests.llm.test_r3_fixes -v"
    result: "Ran 25, OK"
  - "PYTHONPATH=src python3 -m unittest discover -s tests/schema -q"
    result: "Ran 17, OK"
  - "python3 -m py_compile src/llm/budget.py src/llm/real_transport.py src/llm/runner.py src/retrieval/config.py"
    result: "OK"
  - "git diff --check"
    result: "OK (no trailing whitespace)"

confirmed:
  - forged token（无 ledger 引用）被 BudgetBypassError 拒绝，0 次 urlopen（mock 验证）
  - token 有 ledger 但 ledger 中无匹配 pending 记录→被拒绝，0 次 urlopen
  - token 重放（已消费）被拒绝（在 consumed-state 检查阶段，先于 ledger 查询）
  - provider/model/endpoint/batch_id 错配均在 urlopen 前拒绝
  - Ollama /api/tags 预留使用 is_model_call=False，不消耗 per-run 3 次模型调用额度
  - /api/tags 计入 provider 物理 HTTP 总数（54 上限）和全批总数（108 上限）
  - tags 与 chat 各有独立 attempt_number（tags 为负，chat 为正），各自单独记账
  - manifest_version 须精确等于 "retrieval-manifest.v0"（exact match，非前缀）
  - manifest_sha256 须精确等于磁盘文件 SHA-256（非仅格式检查）
  - policy.validate() 须通过（ranges/weights/policy_id 全量验证）
  - 真实冻结 RetrievalIndex（from_config）通过 C1 身份门
  - 8 个 FUSE skip 均为 lock 文件删除限制（标记 skipTest，非测试逻辑问题）
  - 2 个前次 symlink 错误已修复（唯一 link 名 + FUSE 兼容清理）
  - 无真实 API 调用，无密钥读取，FORMAL_EVALUATION_ALLOWED=False 未改变

unresolved:
  - 8 个 FUSE lock skip（test_budget/test_runner/test_runner_r1；原生 macOS 下可运行）
  - Ollama 18 次 tags 预检消耗 provider 配额，实际 chat 额度 ≤ 36 次（设计限制，已文档化）
  - Codex 中枢独立审查仍是正式运行前置门

next_agent_focus:
  - 审查 _verify_pending_reservation() 是否有 TOCTOU（读 ledger 时无锁）；
    当前做法：consume() 在 transport.send() 内部调用，而 send() 在 BudgetAwareTransport.send()
    内部调用，后者在 with ledger: 块内（已持有锁）——因此 consume() 调用时锁已持有
  - 审查 is_model_call=False 预留的 run_attempts_used 不写入是否影响 max_logical_runs 检查；
    当前做法：HTTP-only 预留不进入 run_attempts_used，max_logical_runs 检查只在 is_model_call=True 时触发
  - 审查 sha256 文件比较是否在不同机器/操作系统上稳健（文件以 binary 读取，SHA-256 与 OS 无关）
  - 确认 8 个 FUSE skip 的测试逻辑在原生文件系统下是否正确
```

---

## 预算口径说明（最终版）

物理 HTTP 请求（总计 ≤ 108，每 provider ≤ 54）：
- DeepSeek：每次 POST /chat/completions = 1 次物理请求
- Ollama：每次 GET /api/tags = 1 次物理请求 + 每次 POST /api/chat = 1 次物理请求

模型调用计数（每 logical run ≤ 3 次）：
- 仅 POST /api/chat（Ollama）和 POST /chat/completions（DeepSeek）算模型调用
- GET /api/tags 不算模型调用，但消耗 provider 物理 HTTP 配额

Ollama 极限场景分析（与前次相同）：
- 18 个 Ollama run，每 run 1 次 tags + 最多 3 次 chat = 最多 4 次物理请求
- 18 × 1 tags = 18；54 - 18 = 36 次剩余 chat；最多支持 36 次 chat（12 个 run×3 或 36 个 run×1）
- tags 在第一次 send 时执行，后续 send 使用缓存的 verified_digest，不再发 tags 请求

---

## 结果

APP-001-RUNNER-R3-FIX-R2 四项修复已全部实现并通过测试。状态保持 review，等待 Codex 中枢独立验收。未 push。
