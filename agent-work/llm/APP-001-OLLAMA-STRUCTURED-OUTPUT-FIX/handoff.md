# APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX handoff

```text
handoff_self_check:
  changed=
    src/llm/providers.py — Ollama JSON Schema 常量 + 请求构造改用 schema 对象
    tests/llm/test_providers.py — 更新断言 + 新增 33 项 Schema/parser/快照测试
    tests/llm/test_adapter.py — 更新 Ollama format 断言
    tests/llm/test_envelope_fix.py — 更新 Ollama format 断言
    src/llm/README.md — 待更新（README 修改是允许范围，本 commit 暂未改）
    agent-work/llm/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX/checkpoint.md
    agent-work/llm/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX/handoff.md
    docs/WORKLOG.md — 追加
    commit=待提交（本任务未 push、未合并、未标 done）
  commands=
    /usr/bin/python3 --version → Python 3.10.12
    PYTHONPATH=src:. python3 -m unittest tests.llm.test_providers tests.llm.test_envelope_fix -v → Ran 86, OK
    PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q → Ran 487, OK (skipped=8)
    PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q → Ran 17, OK
    python3 -m py_compile src/llm/providers.py src/llm/contract.py tests/llm/test_providers.py tests/llm/test_adapter.py → OK
    git diff --check → CLEAN
    交接定向复核：OllamaRequestTests.test_request_uses_frozen_fields → ok；
                  parser 接受数字 bore_d=24 → True；
                  parser 拒绝字符串 bore_d="24 mm" → EXTRACTED_TYPE_ERROR；
                  prompt-v2.md hash d95f853d… → 与主线冻结值一致
  confirmed=
    Ollama format 字段现为 dict（JSON Schema 对象），不再是字符串 "json"
    Schema required 覆盖 9 个 ENVELOPE_KEYS；additionalProperties=false
    contract_version / prompt_version 为 const；decision 为 enum；confidence 为 null type
    extracted_parameters 仅允许 6 个字段，全可选，additionalProperties=false
    长度字段接受 number 或 {value:number,unit:string}，不接受 string
    second_screw 为 integer，不接受 number/float/string
    evidence source 受 enum 约束
    parser 数字通过、字符串 "24 mm"/"1.6 cm" 仍被 EXTRACTED_TYPE_ERROR 拒绝
    解码快照 format_schema_sha256 与请求体 schema hash 一致（d82e53ad…）
    DeepSeek 请求不受影响；provider 参数隔离维持原样
  unresolved=
    Ollama 0.33.2（项目基线）是否支持 JSON Schema 作为 format 值未经验证；
    可能需要升级 Ollama 或新 ADR，由中枢决策
    Python 3.11.18 不可用（VM 仅 3.10.12），用户须在 Mac 复核
    是否需要新 ADR 记录结构化输出约束变化由中枢决策
    未运行真实模型批次；不能声称类型违规问题已端到端解决
  next_agent_focus=
    1. 中枢审查 Ollama 版本兼容性：0.33.2 是否接受 dict format，是否需要升级 + 新 ADR
    2. 复核 Schema 结构与 parser 契约对齐：所有 ENVELOPE_KEYS、类型、additionalProperties
    3. 复核快照一致性：format_schema_sha256 是否准确反映请求体 schema
    4. 决策是否需要新 ADR 记录结构化输出约束（区别于旧 format="json"）
    5. 决策是否授权新批次验证实际效果（本任务不授权）
```

## 声明

本任务没有真实网络/模型调用、没有访问密钥、没有修改任何正式批次（`-01`/`-02`/`-03`）、没有修改 `prompt-v2.md`/acceptance-set/ADR-0014/parser 拒绝行为/adapter/runner/预算/授权逻辑，也没有生成新的正式指标。

提醒中枢：Ollama 输出约束改变会改变后续运行配置；本任务不得擅自重跑。中枢审查后再判断是否需要新 ADR/协议版本及新的唯一批次授权。
