# APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX checkpoint

状态：`review`
分支：`cc/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX`
基线：`16f0d1f`（main，本地领先 origin/main 1 commit）
Python：3.10.12（VM 无 python3.11；用户须在 Mac 本机用 /opt/homebrew/bin/python3.11 复核）

## 问题背景

第三批 `app001-phase1-20261107-03` 的 Ollama C0 有 8 条响应以 `EXTRACTED_TYPE_ERROR` 失败：
模型将数值字段序列化为带单位字符串（`"24 mm"`、`"1.6 cm"`、`"70 mm"`、`"0"` 等），
而 `parse_response()` 按冻结 `app001-io.v1` 契约正确拒绝这些类型。

**根因**：`build_ollama_request()` 原来只设置 `format="json"`，仅要求 JSON 格式但不约束字段类型。

## 修改内容

**`src/llm/providers.py`**
- 新增 `_build_ollama_format_schema()` 函数，构造与 `app001-io.v1` 契约对齐的 JSON Schema
- 新增模块级常量 `OLLAMA_FORMAT_SCHEMA`（JSON round-trip 深拷贝，独立于 contract 常量变化）
- 新增模块级常量 `OLLAMA_FORMAT_SCHEMA_SHA256`（schema 的 SHA-256 指纹）
- `build_ollama_request()` 的 `body["format"]` 从字符串 `"json"` 改为 `OLLAMA_FORMAT_SCHEMA` 对象
- `decoding_parameters_snapshot(OLLAMA_PROVIDER)` 从记录 `"format": "json"` 改为记录
  `format_schema_sha256` + `format_schema_version`，避免快照与请求体漂移
- 更新模块 docstring

**`tests/llm/test_providers.py`**
- 更新 `OllamaRequestTests.test_request_uses_frozen_fields`：改为断言 format 是 dict
- 更新 `OllamaRequestTests.test_decode_snapshot_ollama`：改为断言新快照字段
- 新增 `OllamaFormatSchemaStructureTests`（22 项）：覆盖 Schema 结构对齐
- 新增 `OllamaSchemaVsParserAlignmentTests`（7 项）：数字通过、字符串被拒绝
- 新增 `OllamaDecodingSnapshotConsistencyTests`（4 项）：快照与请求体一致

**`tests/llm/test_adapter.py`**
- 更新 `test_ollama_no_think_field_in_request`：改为断言 format 是 dict（不再是 "json"）

**`tests/llm/test_envelope_fix.py`**
- 更新 `OllamaRequestHasJsonFormat.test_format_is_json` → `test_format_is_schema_object`：改为断言 format 是 dict

## 实际验证命令

```
/usr/bin/python3 --version → Python 3.10.12
PYTHONPATH=src:. python3 -m unittest tests.llm.test_providers tests.llm.test_envelope_fix -v → Ran 86, OK
PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q → Ran 487, OK (skipped=8)
PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q → Ran 17, OK
python3 -m py_compile src/llm/providers.py src/llm/contract.py tests/llm/test_providers.py tests/llm/test_adapter.py → OK
git diff --check → CLEAN
```

## Schema 设计

- 顶层：`type: object`，`additionalProperties: false`，`required` = 全部 9 个 ENVELOPE_KEYS
- `contract_version`：`const: "app001-io.v1"`
- `prompt_version`：`const: "app001-extraction.v2"`
- `decision`：`enum: ["answer","ask","refuse"]`
- `extracted_parameters`：`additionalProperties: false`，6 个字段均可选；长度字段用 `oneOf[number, {value,unit}]`（排除 string）；`second_screw` 为 `integer`
- `confidence`：`type: null`
- 数组字段：string items
- `evidence`：`additionalProperties: false`，`field/quote/source` 均为 string，`source` 有 enum 约束
- **不含**：数值范围、catalog 行、CAD-003 规则、evaluator 标签

Schema SHA-256：`d82e53ad7de7676b5a63ac8cdbf276846a78201bec964d25d9771d9e775bb043`
Schema 标识版本：`ollama-app001-io-v1.0`

## 未解决问题

1. **Ollama 兼容性**：Ollama 结构化输出（structured output via JSON Schema as `format`）在 Ollama ≥0.4 支持，项目基线为 Ollama 0.33.2——该版本**不支持** JSON Schema 作为 `format` 值，只支持字符串 `"json"`。这是本任务最重要的未解决问题，需要 Codex 中枢审查并决策：
   - 选项 A：将本任务标记为 `blocked`，要求先升级 Ollama 并更新运行配置（ADR 需要新版本）；
   - 选项 B：接受此 Schema 约束在 Ollama 0.33.2 下会降级为无效/忽略，依赖新批次验证其实际效果；
   - 此问题不由本 CC Agent 自行决策；本任务代码已实现，等待中枢审查。
2. Python 3.11.18 不可用（VM 仅 3.10.12），用户须在 Mac 本机复核。
3. 修改后会影响后续 Ollama 运行配置，中枢审查通过后再授权新批次。
4. 是否需要新 ADR 记录 JSON Schema 结构化输出约束（区别于旧 `format="json"`），由中枢决策。

## 为什么仍保持 review

- Ollama 版本兼容性未经真实运行验证
- 需要 Codex 中枢独立复核 Schema 结构正确性、快照一致性、parser 行为不变
- 未运行真实模型批次；不能据此声称类型违规问题已解决
