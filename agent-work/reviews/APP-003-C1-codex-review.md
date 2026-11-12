# APP-003-C1 中枢最终独立复核

- 日期：2026-11-12
- 结论：`pass`（在 ADR-0022 的本地手动参数演示范围内）
- 分支：`cc/APP-003-C1-LOCAL-DEMO`
- 被审查 HEAD：`4419e27` (`fix: reject truncated decimal bore inputs [APP-003-C1]`)
- 基线：`main=1361f52`
- 复核时工作区：干净；本复核只产生文档记录，不修改被审查代码。

## 范围与不变量

复核确认演示仍是仅绑定 `127.0.0.1` 的手动参数流程：需求文本只作记录，用户选择 GN 705 目录孔径；实现复用既有 Schema、Typed CAD IR、编译/几何验证/STEP pipeline，不调用 LLM、不读取密钥或 `.env`，也不访问 A2 历史批次。`FORMAL_EVALUATION_ALLOWED=False`、冻结契约和 CAD 后端均未改变。演示明确说明单族、固定 CAD 环境、螺纹近似和“STEP 通过不等于制造认证”。

## 固定环境验证

解释器：`work/benchcad-output/venv/bin/python`，Python 3.11.18、CadQuery 2.3.0、OCP 7.9.3.0、jsonschema 4.26.0。

| 检查 | 结果 |
|---|---|
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.demo.test_demo_handler -q` | 55 项通过 |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_pipeline tests.integration.test_schema_to_ir -q` | 81 项通过 |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/schema -p 'test_*.py' -q` | 17 项通过 |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q` | 13 项通过 |
| 固定 venv `py_compile`（demo、启动脚本和测试文件） | 通过 |
| `git diff --check` | 通过 |

Demo 测试出现四条来自测试中 `open(...).read()` 的 `ResourceWarning`，退出码为 0，55 项均通过；CAD 依赖输出包含上游弃用警告，不影响测试结果。

## 真实本地 HTTP / STEP 烟测

在当前 HEAD 用固定 venv 启动 demo 服务，日志确认地址为 `127.0.0.1`；输出写入临时目录，测试后停止服务并清理。

- `GET /` 返回 HTML；浏览器实际打开页面，手动选择 24 mm 后提交，页面显示成功、`step_readback`、6 个参数及其来源、IR、几何摘要和下载入口。
- 24 mm：真实 STEP 生成并下载，148393 bytes；SHA-256 与 API 结果一致；实体数 1、面数 35、回读通过。
- 80 mm：生成独立 UUID run 并成功下载；`second_screw=1` 且来源为 `rule_derived`。
- 24.9：返回 `invalid_input` / `input_validation`，下载返回 403；不会误截断成 24 mm。
- 缺少 bore_d：API 返回 400 / `MISSING_BORE_D`。
- 非目录值 25：返回 `invalid_input`；其 run 下载返回 403，之前成功的 24 mm run 仍可单独下载。
- 非 UUID 下载 ID 返回 400；格式合法但未知的 ID 返回 404。
- 将已成功 STEP 替换为指向 run 外的符号链接、恢复原文件后篡改内容：两种下载分别返回 403；完整性恢复后仍可下载。

浏览器中的动态 HTML 转义回归由 Demo 专项测试覆盖；本次浏览器实操确认页面和生成结果正常展示。未执行任何 LLM/provider 或外网请求。

## 审查结论与限制

交付核心条件通过：参数值及来源、Schema/IR/CAD/几何与 STEP 回读可追溯；不合法/缺失输入不能获得 STEP；新运行独立，失败不泄漏其他运行的文件；下载校验拒绝路径逃逸、符号链接和内容篡改。可以按既定边界合入 `main`。

复核时发现的 P3 下载按钮文案瑕疵已由后续窄修修复：按钮显示为 `下载 STEP（148393 字节）`，并有 HTML 输出回归断言。修复提交为 `b59b551`；固定 CAD venv 下 Demo 56/56、`py_compile` 和 `git diff --check` 通过。演示仍不能证明自然语言理解、广泛语言覆盖、跨族能力、长期稳定性或制造适用性。

状态保持 `review`，直到分支合入 `main`；不得在合并前标记 `done`。没有 push 或 merge。
