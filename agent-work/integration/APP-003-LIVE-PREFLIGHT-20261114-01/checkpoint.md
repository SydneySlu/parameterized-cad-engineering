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

- 负责人审阅并批准新候选 scope 与具体 batch ID。
- 获批后再制作绑定该新 batch 的正式 approval 记录并执行 live preflight。
- 真实 DeepSeek 请求仍需明确的单独执行授权；在此之前不得调用 formal `run_product_batch(dry_run=False, transport=None)`。
- 结果只能描述本次四条冻结刺激；不代表泛化、统计显著性或制造认证。

## handoff_self_check

```text
changed=新增 scope.md、offline-preflight.json、checkpoint.md；更新 PROJECT_STATUS/PROJECT_PLAN/TASKS/WORKLOG
commands=固定 CAD venv run_product_offline_preflight(require_cad_runtime=True): ok=true；run_product_batch(dry_run=True): preflight_ok=true, planned=4, results=0；candidate dir absent before/after
confirmed=hash/profile/input/budget/prompt/runtime checks pass；没有网络请求、密钥读取、正式 batch/ledger 或真实 CAD
unresolved=负责人对新 scope 和 batch ID 的批准；live approval、正式 preflight 和执行授权
next_agent_focus=先核对负责人批准文本是否精确匹配 scope；获批后才准备 formal approval/preflight；不得重跑 2026-11-13 旧 batch
```
