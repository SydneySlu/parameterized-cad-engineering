# APP-001 Ollama structured output 修正中枢审查

- 任务：`APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX`
- 审查日期：2026-11-07
- 审查对象：CC commit `0e1721f`
- 状态：`review`，暂不合入 `main`，暂不授权新正式批次

## 已确认

1. `build_ollama_request()` 的 `body["format"]` 已从字符串改为 `OLLAMA_FORMAT_SCHEMA` 对象；DeepSeek 请求保持 `response_format={"type":"json_object"}`，provider-specific 参数隔离未回退。
2. Schema 顶层键、版本常量、decision 枚举、六个抽取字段、长度字段的 number/measurement-object 类型、`second_screw` integer、数组和 additionalProperties 约束与冻结契约的主要意图一致。
3. schema hash 与实际 request body、Ollama decoding snapshot 一致：`d82e53ad7de7676b5a63ac8cdbf276846a78201bec964d25d9771d9e775bb043`。
4. 严格 parser 行为未被改动：数字和 `{value, unit}` 正常案例通过，`"24 mm"`、`"1.6 cm"`、`"0"` 仍拒绝为 `EXTRACTED_TYPE_ERROR`。
5. 未修改冻结 Prompt、旧正式批次、预算/runner、parser 生产代码或正式评测数据。

## 独立验证

```text
/opt/homebrew/bin/python3.11 --version
Python 3.11.18

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest tests.llm.test_providers tests.llm.test_envelope_fix -q
Ran 86, OK

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/llm -q
Ran 487, OK (skipped=8)

PYTHONPATH=src:. /opt/homebrew/bin/python3.11 -m unittest discover -s tests/schema -q
Ran 17, OK

/opt/homebrew/bin/python3.11 -m py_compile ...; git diff --check 16f0d1f..HEAD
通过
```

当前本机 Ollama 事实为：`ollama version is 0.33.2`。未调用 `/api/chat`，未运行模型，未读取密钥。

## 阻塞与偏差

### 1. 运行时兼容性未证明，且当前基线存在高风险

本修正把 `format` 改成 JSON Schema 对象；项目冻结运行基线是 Ollama 0.33.2，历史 probe 只证明该版本接受字符串 `format="json"`。本次没有证明 0.33.2 接受对象形式，也没有升级运行时或建立兼容性证据。不能将离线 Schema 测试当作实际 Ollama 兼容性通过，不能据此启动新批次。

README 中“需要 Ollama ≥0.4”的版本边界仍缺本项目内的来源或实机证据，应在升级/新 ADR 前补齐，不要把它当作已验证事实。

### 2. Schema 与 parser 的 evidence null 行为不完全一致

Schema 要求 evidence 的 `field`/`quote`/`source` 为 string，但当前 parser 对这些键显式为 `null` 时实际放行（`parse_response()` 返回 `ok=True`）。这不是本次改动引入的回归，但 CC 报告把二者描述为完全对齐并不准确。应在后续窄修正中二选一：修 parser 使其真正拒绝 null，或明确 Schema 兼容现有行为；在没有决策前不应声称“完全对齐”。

### 3. 第三方 JSON Schema validator 未执行

本机 Python 3.11 环境没有 `jsonschema` 包。结构和 parser 回归测试通过，但没有 Draft 2020-12 引擎验证；这属于证据限制，不是失败。

## 结论

代码范围和离线回归测试通过，任务保持 `review`。当前不能合入 `main` 或授权新批次。下一步应由项目负责人决定是否：

1. 保持 Ollama 0.33.2，撤回/隔离对象形式，继续使用旧 `format="json"`；或
2. 明确升级 Ollama，新增决策记录并在新运行环境中完成无密钥的请求兼容性 smoke test；随后再决定是否以唯一新批次重跑。

无论选择哪条路径，都应先补齐 evidence null 契约处理和 JSON Schema validator/等价验证证据。三个既有正式批次保持只读，不混合统计。

