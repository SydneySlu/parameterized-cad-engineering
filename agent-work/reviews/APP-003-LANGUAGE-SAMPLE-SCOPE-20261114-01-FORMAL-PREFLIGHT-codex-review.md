# APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01 formal preflight 独立复核

- 复核日期：2026-11-14
- 复核者：Codex 中枢
- 复核基线：`codex/APP-003-FAILURE-PATHS-LANGUAGE-MATRIX`, HEAD `424a0eb`
- 结论：`pass`（仅限新 batch 的批准绑定、离线 formal preflight 和 fail-closed 边界）；真实执行仍为 `review`/blocked by runner availability

## 复核范围

核对新 batch `app003-product-language-20261114-01` 的批准绑定、十条输入和 hash、DeepSeek/C0 scope、20 次 HTTP 预算、batch 目录状态、labels 隔离及执行入口的 fail-closed 行为。没有调用 DeepSeek、读取 `.env`/API key、创建 batch/ledger、读取 evaluator labels 或运行 CAD。

## 实际验证

固定 CAD venv（Python 3.11.18）执行：

| 命令/检查 | 结果 |
|---|---|
| `python -m unittest tests.integration.test_product_language_scope -q` | 8/8 通过 |
| 定向正常 preflight + `urlopen`/credential loader spy | 通过；10 planned runs、20 HTTP，网络/凭据调用均为 0 |
| 已有 batch 目录 | 通过；返回 `batch_directory_already_exists`，不执行请求 |
| 输入 hash 失败 | 通过；返回 `ok=false` 且 `planned_runs=[]` |
| `run_product_language_batch()` | 通过；明确抛出 `offline-preflight-only` |
| `py_compile`（profile、runner、专项测试） | 通过 |
| `git diff --check` | 通过 |

`formal-preflight.json` 与实际结果一致：`preflight.ok=true`、十条 ID 顺序正确、输入 hash 和预算匹配、`batch_dir_exists=false`、`formal_evaluation_allowed=false`、`network_requests=0`、`formal_batch_created=false`。

## 结论边界与下一步

本轮准备证据通过，且旧 `app003-product-live.v1` profile/batch 未被复用。负责人批准了该 scope 的真实 DeepSeek 执行方向，但当前 `run_product_language_batch()` 仍是显式 offline-only 占位；因此不能把本复核或批准记录解释为已经可以发送请求。下一步必须实现独立 formal runner（批准绑定、20 次硬预算 ledger、重试分类、raw/summary 隔离、执行报告），完成固定环境离线测试和新的独立复核后，才能进入真实请求。
