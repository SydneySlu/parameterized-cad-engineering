# APP-003-LANGUAGE-SAMPLE-FORMAL-RUNNER R1 中枢独立验收

- 日期：2026-11-15
- 结论：`pass`（本轮 R1 小修与提交链）
- 分支：`cc/APP-003-LANGUAGE-SAMPLE-FORMAL-RUNNER`
- HEAD：`c38167d`；功能/测试修复：`633fc8d`；父功能提交：`9a0bb0f`
- 工作区：验收开始和结束均干净。

## 审查范围

本次独立验收针对 `633fc8d` 修复的 summary 脱敏测试断言及 `c38167d` 的交接记录。其他 formal runner 行为参考已提交实现和同轮专项回归，不将本次结论扩大为真实模型效果验证。

`633fc8d` 将 `test_formal_adapter_exception_sanitized` 中对 `batch_summary.json` 的条件式检查改为强制文件存在，并确认 summary 不包含异常敏感 marker。断言位于 `TemporaryDirectory` 清理前。独立执行过程中曾将断言临时改为强制后发现其原先在临时目录清理后执行，随后将断言移动至目录生命周期内；最终提交差异与此行为一致。

## 实际验证

固定 CAD venv：Python 3.11.18，macOS。

| 命令 | 结果 |
|---|---|
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_language_scope tests.integration.test_product_language_formal_runner -q` | 98/98 通过 |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_language_formal_runner.TestFormalRunnerMockMode.test_mock_all_answer_returns_ten_results tests.integration.test_product_language_formal_runner.TestExceptionSanitization.test_formal_adapter_exception_sanitized -q` | 正常 mock answer 与 formal Adapter 异常脱敏 2/2 通过 |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_live -q` | 109/109 通过 |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m py_compile src/integration/product_language_formal_runner.py src/llm/product_language_authorization.py tests/integration/test_product_language_formal_runner.py tests/integration/test_product_language_scope.py` | 通过 |
| `git diff --check 9a0bb0f..HEAD` | 通过 |

Product Live 测试有既有未关闭 HTTP socket `ResourceWarning`，未造成测试失败。首次定向命令使用了不存在的 unittest 类名，导致该命令本身未能加载测试；按实际类名重跑后的 2 项定向测试通过。

## 安全与范围核对

- `src/llm/contract.py` 中 `FORMAL_EVALUATION_ALLOWED` 仍为 `False`，测试覆盖其值不变。
- 正常路径由固定 FakeTransport mock 验证；异常路径强制走 `transport=None` 的 formal Adapter 路径，断言稳定错误码、固定消息，并检查 result 与磁盘 summary 均不含敏感 marker。
- 获批目标 batch `app003-product-language-20261114-01` 的 canonical 目录不存在；没有创建 batch、ledger 或 raw。
- 本次未运行 formal live、未加载凭据、未读 evaluator labels、未调用 DeepSeek 或其他网络接口。

## 结论和后续

R1 的测试缺口已关闭，提交差异与 checkpoint/状态页/计划页一致；本轮结论为 `pass`。任务仍处于 `review`，分支尚未 push/merge。后续如合入 `main`，应在合入提交上复跑语言专项及必要回归并完成文档收束；真实 DeepSeek 执行仍需按独立 batch、preflight 和明确授权 gate 处理。
