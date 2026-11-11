# APP-001-NEXT-REAL-MODEL-EVALUATION — Codex 中枢独立审查

- 日期：2026-11-11
- 结论：`review`；held-out runner 暂不能进入 final preflight 或请求授权阶段。
- 审查基线：`main`，HEAD `5928b23`，本地 `origin/main` ahead 6；工作区审查前干净。
- 审查范围：`origin/main..HEAD` 的 runner、CLI、授权 profile、分类账本、测试与任务交接材料。

## 必须修复

### P1 — runner API 可绕过关闭的全局评测 gate 和批次授权检查

`HeldoutRunner.run_formal()` 只校验参数是 `HeldoutRunAuthorization` 实例，之后即可进入 `_execute_batch()`。它没有验证 `FORMAL_EVALUATION_ALLOWED`，也没有校验该授权对应项目负责人批准的 batch ID 或授权凭据。`authorize_heldout_v5_run(batch_id=...)` 可由任意调用者针对任意非空 batch ID 直接构造 profile；因此直接调用 Python API 可绕过 CLI 的 `FORMAL_EVALUATION_ALLOWED=False` 与 `--allow-formal-run` 检查。

证据：`src/llm/heldout_runner.py:688-752`、`src/llm/heldout_authorization.py:153-172`；CLI 的 gate 仅位于 `scripts/run_app001_heldout_v5.py:157-183`。CLI 防护不能替代 runner API 自身的执行边界。当前配置下任何路径都不得发出正式请求；需先以 ADR-0019 不改变既有全局 gate 的方式设计可验证的显式批次批准凭据/门禁，并让 API 与 CLI 共同强制。补充测试必须证明直接调用 API 在无该批准时于任何目录创建、账本写入、凭据读取或网络 I/O 前拒绝。

### P1 — offline preflight 错误计算总预算却无条件报告 pass

`offline_preflight()` 在 `src/llm/heldout_runner.py:656-667` 将 chat cap 36 与 identity cap 20 直接相加，实际输出 `56 ≤ 44`，同时硬编码 `feasible=True` 和 `offline_preflight_status="pass"`。本机执行 CLI 得到的该结果与输出直接矛盾，不能作为 final offline preflight 或授权依据。

硬上限的实际可执行关系依赖 Ollama 的每次 transport attempt：runtime `/api/tags` 失败会消耗该次调用且不产生 chat；tags 成功后才会执行 chat，已验证 digest 的后续 retry 只发 chat。因此各上限不能简单按独立最大值相加。实现需明确建模/报告可达到的组合上限（同时展示类别、provider、global 限制），避免虚假的不等式；`feasible` 必须从校验结果计算，不可常量写死。测试应覆盖真实边界和不可行的 scope/cap 变体。

## 已通过的检查

- 当前分支 `main`，HEAD `5928b23`，`origin/main` ahead 6，工作区干净。
- Python `/opt/homebrew/bin/python3.11` 为 3.11.18。
- `tests.llm.test_heldout_runner`：53 项通过。
- `tests.llm.test_heldout_authorization tests.llm.test_authorization tests.llm.test_budget tests.llm.test_runner`：120 项通过，7 项既有 skip。
- `tests/llm` 全量：908 项通过，8 项既有 skip。
- `tests/schema`：17 项通过。
- `py_compile` 涉及 runner、profile、ledger、CLI 和新测试文件通过；`git diff --check origin/main...HEAD` 通过。
- CLI `--dry-run --json` 以 exit 0 输出 12 个唯一组合，并显示 `formal_evaluation_allowed=false`。
- CLI `--offline-preflight --batch-id review-only-not-a-batch --json` 以 exit 0 返回检索 manifest SHA 正确、batch dir 不存在；同时暴露错误的 `56 ≤ 44` 与硬编码 pass。

## 边界与下一步

本次没有运行 `--run`、live preflight 或任何 HTTP 请求；没有访问密钥、`.env`、旧批次 raw；CLI offline-preflight 只读取冻结输入/标签/manifest 做 hash/配置校验，没有创建批次目录。未分配正式 batch ID，也没有模型请求授权。

下一步由实现者窄修 P1 项并更新 checkpoint、WORKLOG、PROJECT_STATUS/PROJECT_PLAN；之后 Codex 中枢按本报告复跑 API 直接拒绝、预算边界、dry-run、offline-preflight 与回归。通过后才能进行 final offline preflight，再提交唯一 batch ID 和完整授权模板供项目负责人决定。此审查不授权任何请求。

## R1 跟进复核（commit `fd99ddb`）

- 跟进日期：2026-11-11
- R1 对上述两项修复通过定向复核：`run_formal()` 在全局 gate、profile 类型、单独 approval token 和 batch ID 一致性检查通过前拒绝；当前 `FORMAL_EVALUATION_ALLOWED=False` 未改变。approval token 明确标记为软件操作门，不声称是不可伪造凭据。预算函数按 Ollama tags→chat 重试顺序计算：每 run 最多 `max(3 tags failures, 1 tags success + 3 chat)=4`；Ollama 26、DeepSeek 18、全局 44，分类 cap 分别为 chat 36、identity 20。
- R1 验证复跑（Python 3.11.18）：held-out 专项 70 项通过；授权/预算/runner 回归 120 项通过、7 项 skip；LLM 全量 925 项通过、8 项 skip；Schema 17 项通过；`py_compile` 与 `git diff --check HEAD^ HEAD` 通过。dry-run 产生 12 个组合，offline-preflight 在真实本地 retrieval index 下返回 44/44 且未创建 batch 目录。
- **新增 P1：缺少 RET-002 retrieval index 时 offline-preflight 仍返回 pass。** `HeldoutRunner().offline_preflight("review-no-retrieval-index-only")` 实测返回 `retrieval_index_provided=False`、`retrieval_config_check="skipped: no retrieval_index"`、`offline_preflight_status="pass"`。CLI `_try_load_retrieval_index()` 会吞掉加载异常并返回 `None`，offline-preflight 随后接受缺失 index。正式 runner 的 C1 六项必须依赖该 index，因此这个 pass 不能作为最终 preflight 通过证据。
- 结论：整体仍为 `review`，不进入 final offline preflight gate，不生成 batch ID/授权模板。需窄修为 offline-preflight 缺失或加载失败时 fail closed，并增加无 index / 配置或 manifest 加载失败拒绝测试；通过后重新做中枢审查。
- 边界：所有复核均未执行 `--run`、live preflight 或 HTTP；未读密钥、`.env` 或历史 raw，未创建正式批次目录。离线检查传入的 `review-only-not-a-batch-fd99ddb` 仅用于核验，不是正式 batch ID。
