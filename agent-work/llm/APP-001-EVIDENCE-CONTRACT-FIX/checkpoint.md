# APP-001-EVIDENCE-CONTRACT-FIX checkpoint

状态：`review`
分支：`cc/APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX`（在现有分支继续工作）
Python：3.10.12（VM 无 python3.11）

## 问题背景

`OLLAMA_FORMAT_SCHEMA` 要求 evidence 的 `field`/`quote`/`source` 为 `string`，
但 `src/llm/parser.py` 第 214 行使用：

```
if val is not None and not isinstance(val, str):
```

其中 `val is not None` 守护导致显式 `null`（Python `None`）跳过检查，parser 放行了
Schema 声明为 string 的字段为 null 的情况。这是 Codex 中枢审查
`APP-001-OLLAMA-STRUCTURED-OUTPUT-FIX` 时发现的 parser 与 Schema 不完全对齐问题。

## 修复

**`src/llm/parser.py`**，evidence type-check 循环：

- 移除 `val is not None` 守护
- `None` 现在进入 `not isinstance(val, str)` 检查，产生 `EVIDENCE_FIELD_TYPE_ERROR`
- 现有错误码、错误路径、source 枚举检查、其他 parser 行为均不改变

## 修改文件

- `src/llm/parser.py`（单行修复）
- `tests/llm/test_parser.py`（新增 `EvidenceNullFieldTests` 12 项）
- `agent-work/llm/APP-001-EVIDENCE-CONTRACT-FIX/checkpoint.md`（本文件）
- `docs/WORKLOG.md`（追加）

未修改：`OLLAMA_FORMAT_SCHEMA`、`prompt-v2.md`、Ollama 版本、transport、adapter、
runner、正式批次、ADR-0015。

## 实际验证命令

```
/usr/bin/python3 --version → Python 3.10.12
PYTHONPATH=src:. python3 -m unittest tests.llm.test_r1_regression tests.llm.test_providers -v → Ran 83, OK
PYTHONPATH=src:. python3 -m unittest tests.llm.test_parser -v → Ran 36, OK (含 12 新增)
PYTHONPATH=src:. python3 -m unittest discover -s tests/llm -q → Ran 499, OK (skipped=8)
PYTHONPATH=src:. python3 -m unittest discover -s tests/schema -q → Ran 17, OK
python3 -m py_compile src/llm/parser.py → OK
git diff --check → CLEAN
```

## 正常案例

- `test_valid_string_evidence_passes`：合法 string evidence 通过
- `test_empty_evidence_array_passes`：空 evidence 数组通过

## 失败案例

- `test_field_null_rejected`：`field=null` → `EVIDENCE_FIELD_TYPE_ERROR`，路径 `evidence[0].field`
- `test_quote_null_rejected`：`quote=null` → `EVIDENCE_FIELD_TYPE_ERROR`，路径 `evidence[0].quote`
- `test_source_null_rejected`：`source=null` → `EVIDENCE_FIELD_TYPE_ERROR`，路径 `evidence[0].source`
- `test_all_three_null_produces_three_errors`：三个 null 产生三个 `EVIDENCE_FIELD_TYPE_ERROR`
- `test_source_wrong_string_still_evidence_source_invalid`：非枚举字符串仍产生 `EVIDENCE_SOURCE_INVALID`

## 未解决问题

1. Python 3.11.18 不可用（VM 仅 3.10.12），用户须在 Mac 本机用 `/opt/homebrew/bin/python3.11` 复核。
2. 本任务不授权新正式批次。
