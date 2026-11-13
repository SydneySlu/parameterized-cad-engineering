# APP-003 Product Live Smoke Candidate — Checkpoint

- 日期：2026-11-14
- 任务：`APP-003-LIVE-PREFLIGHT-20261114-01`
- 状态：`review`（候选 scope 与离线 preflight 已准备，等待负责人审阅；未授权 live）
- 基线：`main=d80fd433c54d37c135581e92c01c4e4bbee31bb3`，工作区干净；本地 `main` ahead of `origin/main` 7 commits
- 候选 batch：`app003-product-live-20261114-01`
- 前置复核：`APP-003-LIVE-PREFLIGHT-20261113-01` 独立复核 `pass`；代码差异在 `d80fd43`，此前批次仍只读

## 已完成

- 准备新 scope 提案：沿用当前实现绑定的四条冻结输入、DeepSeek `deepseek-flash` / C0 和最多 12 HTTP；目的为在 mapper/diagnostic 修复后验证新的真实 Adapter 路径，不扩大输入或授权范围。
- 固定环境：Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、jsonschema 4.26.0，Draft 2020-12 可用。
- 离线 preflight：`ok=true`；输入 hash 与 prompt 可加载；预算 4 × 3 = 12 可行；候选 batch 目录开始前不存在。
- dry-run：`preflight_ok=true`，计划 4 个 logical runs、0 个实际结果；执行后 batch 目录仍不存在。

## 批准与正式 preflight

- 负责人批准：`Wang sikai`，`approved_at_utc=2026-11-13T17:14:42Z`。
- `ProductLiveFormalApproval` 已按新 batch 构造并通过 `validate_product_formal_approval_binding()`；`is_test_only=False`，scope/hash/provider/model/预算均匹配。
- 正式 preflight（固定 CAD venv，`require_cad_runtime=True`）返回 `ok=true`，错误为空；候选 batch 目录不存在。
- 记录：`formal-preflight.json`。本轮没有调用 formal runner，没有创建 batch/ledger，没有构造 transport，没有读取密钥，没有网络请求。

## 实际命令

```sh
test ! -e work/app001-runs/app003-product-live-20261114-01
PYTHONPATH=src:. work/benchcad-output/venv/bin/python - <<'PY'
import json, platform
from pathlib import Path
from integration.product_live_runner import run_product_batch, run_product_offline_preflight
from llm.product_live_authorization import authorize_product_live_run
batch_id = "app003-product-live-20261114-01"
authorization = authorize_product_live_run(batch_id=batch_id)
preflight = run_product_offline_preflight(authorization, require_cad_runtime=True)
dry_run = run_product_batch(authorization=authorization, dry_run=True)
print(json.dumps({"python": platform.python_version(), "preflight": preflight,
    "dry_run_mode": dry_run.mode, "dry_run_preflight_ok": dry_run.preflight_ok,
    "planned_runs": len(dry_run.planned_runs), "results": len(dry_run.results),
    "batch_dir_exists_after": Path("work/app001-runs").joinpath(batch_id).exists()},
    ensure_ascii=False, indent=2))
PY
git status --short --branch
```

结果：离线 preflight `ok=true`、dry-run `preflight_ok=true`；Python 3.11.18；candidate batch dir absent before/after；未调用 provider/网络，未读取 `.env`/密钥，未创建正式 batch/ledger。

## 尚未完成 / 前置 gate

- scope 与具体 batch ID 已获负责人批准；正式 approval binding 和 preflight 已通过。
- 真实 DeepSeek 请求仍需明确的单独执行授权；在此之前不得调用 formal `run_product_batch(dry_run=False, transport=None)`。
- 结果只能描述本次四条冻结刺激；不代表泛化、统计显著性或制造认证。

## handoff_self_check

```text
changed=新增 scope.md、offline-preflight.json、formal-preflight.json、checkpoint.md；更新 PROJECT_STATUS/PROJECT_PLAN/TASKS/WORKLOG
commands=固定 CAD venv run_product_offline_preflight(require_cad_runtime=True): ok=true；run_product_batch(dry_run=True): preflight_ok=true, planned=4, results=0；ProductLiveFormalApproval binding: pass；candidate dir absent before/after
confirmed=负责人批准 scope/batch；scope/hash/profile/budget/prompt/runtime checks pass；没有网络请求、密钥读取、正式 batch/ledger、transport 或正式 CAD
unresolved=真实 DeepSeek 请求的单独执行授权
next_agent_focus=负责人若明确批准执行，再调用 formal runner；否则保持候选 review；不得重跑 2026-11-13 旧 batch
```

## 正式执行结果

- 负责人于 `2026-11-13T17:19:48Z` 明确批准执行该 batch，最多 12 次 HTTP。
- formal runner 已执行 4 条逻辑输入，各 1 次 HTTP，账本 `4/12`；批次状态为 `failed`。
- P1–P4 均为 `product_status=error`、`llm_status=error`、`TRANSPORT_ERROR`，稳定原因码为 `authentication_or_permission`；没有模型响应、确认、Schema/IR/CAD/STEP 结果。
- `raw/` 文件数为 0，pipeline 文件数为 0；没有读取 raw 正文、密钥或 Authorization header。
- 执行摘要：`execution-report.json`；批次目录 `work/app001-runs/app003-product-live-20261114-01/` 只读保留，不重跑、不追加请求、不改写历史证据。

### 执行后 handoff_self_check

```text
changed=新增 execution-report.json；正式 runner 已写入该 batch 的 batch_summary.json 与 budget_ledger.json
commands=formal run_product_batch(dry_run=False, transport=None): 完成；ledger total_attempts_used=4/12；summary batch_status=failed；raw/pipeline files=0
confirmed=四条输入均在响应前以 TRANSPORT_ERROR/authentication_or_permission 失败；没有确认、CAD、STEP 或 raw 正文；旧 batch 与本 batch 均不重跑
unresolved=provider authentication/permission 根因需负责人在外部凭据/账户层面处理；本 batch 授权已消耗，不得追加请求
next_agent_focus=只读审查 batch summary/ledger 和执行报告；如需再次尝试，必须先解决凭据问题并创建全新 scope、batch、approval 与 preflight
```

## 凭据入口根因核查与窄修（2026-11-14）

- 诊断：只检查 `.env` 中变量名与是否非空，没有输出 key；文件和非空值存在，但 formal runner 进程中的 `DEEPSEEK_API_KEY` 缺失。`DeepSeekTransport.send()` 只读取进程环境变量，因此原 batch 的稳定原因码不能用于判断 DeepSeek 账户权限。
- 修改候选：`src/llm/env_loader.py` 提供保守、fail-closed 的 required-key loader；Product Live formal path 在审批 binding 和 CAD/runtime offline preflight 通过后、batch 目录/ledger/transport 创建前加载。dry-run/mock 不调用 loader；不修改 transport 的 env-only 行为，也不改变全局 gate。
- 测试：固定 CAD venv Python 3.11.18，`tests.integration.test_product_live_env` 9/9 通过；`tests.integration.test_product_live` 107/107 通过；py_compile 与 `git diff --check` 通过。测试中模拟 loader 缺 key 时 runner 在 batch root 创建前 fail closed。
- 边界：本轮无网络/HTTP；没有检查或输出 key 内容；旧批次 `app003-product-live-20261114-01` 仍只读，4/12 已消耗，不得重跑或追加。`.env` 内容未修改、未提交。
- 未解决：provider 实际是否接受该账户/key 仍未验证。需先完成本窄修复核，再创建全新 scope/batch/approval/preflight 并获得新的明确执行授权，才能做最小真实 provider 诊断。

### handoff_self_check（credential entry fix）

```text
changed=src/llm/env_loader.py; src/integration/product_live_runner.py; src/llm/__init__.py; tests/integration/test_product_live_env.py; PROJECT_STATUS/PLAN/TASKS/WORKLOG/checkpoint
commands=CAD venv Python 3.11.18: test_product_live_env 9/9; test_product_live 107/107; py_compile 通过; git diff --check 通过
confirmed=dotenv key 存在且非空、formal process env 原缺失；transport 仅读 os.environ；正式路径在基础设施创建前加载；dry-run不加载；模拟缺凭据时零 batch 创建
unresolved=未发 HTTP；provider 账户权限尚不能判定；窄修仍待独立复核
next_agent_focus=复核 dotenv parser 与正式路径时序；确认不输出 key、不影响 mock/dry-run；任何真实 provider 请求必须新 batch 和新授权
```
