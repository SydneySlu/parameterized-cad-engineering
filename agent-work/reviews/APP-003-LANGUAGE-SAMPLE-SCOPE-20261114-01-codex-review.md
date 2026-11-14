# APP-003-LANGUAGE-SAMPLE-SCOPE-20261114-01 独立复核

- 复核日期：2026-11-14
- 复核者：Codex 中枢
- 复核基线：`codex/APP-003-FAILURE-PATHS-LANGUAGE-MATRIX`, HEAD `34a65e0`
- 结论：`pass`（仅限独立授权 profile 与离线 preflight 准备）

## 复核范围

核对十条输入 scope、授权 profile、输入/labels 隔离、预算边界、旧 Product Live profile 不变，以及 preflight 的无网络/无凭据/无 batch 副作用。没有执行真实模型请求，也没有把本次结果视为语言质量证据。

## 代码与范围核对

- 新 profile 为 `app003-product-language.v1`，绑定 10 条 `L01`–`L10` 输入、DeepSeek `deepseek-flash`、C0、无检索。
- `model-inputs.json` SHA-256 为 `8339431ee66a14d838cdbded48240019254182886c85af5cd611e04eaf361801`；`evaluator-labels.json` SHA-256 为 `a5055025e4a01740b9bc25daa5ab51e43bdac9748151ccd10c152cdf7151bcf9`，与 profile 常量一致。
- 预算为 10 条 × 每条最多 2 次 = 20 次 HTTP；`max_chat_attempts_for()` 已窄修为 2，provider 总 cap 为 20。
- 独立 runner 只提供离线 preflight；`run_product_language_batch()` 明确抛出 `offline-preflight-only`。
- 旧 `src/llm/product_live_authorization.py` 与 `src/integration/product_live_runner.py` 在本轮差异中未修改；旧 P1–P4 profile 和历史 batch 不受影响。
- runner 未读取 evaluator labels 文件；只读取 model inputs，并在读取前核对 hash、数组格式、ID 顺序和字段集合。

## 实际验证

固定 CAD venv：Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0。

| 命令 | 结果 |
|---|---|
| `python -m unittest tests.integration.test_product_language_scope -q` | 8/8 通过 |
| `python -m unittest tests.integration.test_product_live -q` | 109/109 通过 |
| `python -m unittest tests.demo.test_product_live_ui tests.demo.test_product_flow tests.demo.test_product_ui tests.demo.test_demo_handler tests.integration.test_pipeline tests.integration.test_schema_to_ir -q` | 300/300 通过 |
| `python -m unittest discover -s tests/schema -p 'test_*.py' -q` | 17/17 通过 |
| `python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q` | 13/13 通过 |
| `python -m py_compile ...` | 通过 |
| `git diff --check a3a4f5d..HEAD` | 通过 |

专项正常路径的 preflight 规划 10 个 logical runs、20 次 HTTP，输入 hash 通过。专项失败路径验证了错误 profile/hash、错误授权类型、输入 hash 错误和已有 batch 目录均 fail-closed；执行 API 拒绝运行。网络、凭据加载和 evaluator labels 文件均由 spy 确认为 0 次调用。

测试输出有既有 HTTP socket `ResourceWarning` 和 CAD 依赖弃用警告；没有测试失败，不改变本次结论。

## 结论边界

本复核允许进入下一步 scope/batch 准备，但不批准真实 DeepSeek 请求，不创建 batch，不读取 `.env`/API key，不运行 CAD confirmation。下一步仍需明确 batch ID、formal preflight 和负责人对真实执行的单独批准。
