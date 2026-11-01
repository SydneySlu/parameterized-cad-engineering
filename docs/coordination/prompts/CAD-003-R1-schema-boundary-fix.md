# CAD-003-R1：Schema JSON 边界一致性修正 Prompt

将下面内容复制回原 CAD-003 Agent 对话框，或交给负责 Schema 的执行 Agent。该任务只修正 JSON Schema 与 Python 校验器之间的输入协议不一致，不重新设计参数规则。

```text
你是“参数化 CAD 工程辅助设计”项目的 CAD-003-R1 修正 Agent，负责修正 CAD-003 Schema v0 的 JSON 输入边界一致性问题。

## 修正目标

当前 CAD-003 文档把正式输入写成 envelope：

{
  "schema_version": "set_screw_shaft_collar.v0",
  "family_id": "set_screw_shaft_collar",
  "parameters": {
    "bore_d": {"value": 20, "unit": "mm"}
  }
}

但 `schema-v0.json` 当前导出的 `json_schema` 描述的是根级扁平参数对象，不能直接约束正式 envelope，也不能表达 `{value, unit}` 的测量值形式。Python 校验器已经支持 envelope、扁平兼容输入和单位归一化；本任务要让公开 Schema 描述与实际协议对齐。

## 项目根目录

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = "/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

不要 reset、clean、checkout 或覆盖其他 Agent 的未提交改动。只修改 CAD-003-R1 相关文件。

## 必读材料

1. `AGENTS.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/TASKS.md`
4. `docs/DECISIONS.md`
5. `agent-work/schema-rules/CAD-003-schema-v0/README.md`
6. `agent-work/schema-rules/CAD-003-schema-v0/schema-v0.json`
7. `src/schema/set_screw_shaft_collar.py`
8. `tests/schema/test_set_screw_shaft_collar.py`
9. `docs/coordination/prompt-sequence.md`

## 必须保持的规则边界

- 仍然只覆盖 `set_screw_shaft_collar`；不扩展第二族。
- 不修改 `CATALOG_ROWS`、字段来源、单位换算、目录耦合、`second_screw`、壁厚或宽度规则，除非发现可由 DATA-003 证据证明的错误。
- 不实现 Typed CAD IR、CadQuery/OCP、STEP 或 LLM。
- Python 校验器仍可兼容扁平对象，但必须明确这只是内部/过渡兼容路径。
- JSON Schema 不能假装表达跨字段目录耦合和几何规则；这些继续由 Python 规则校验器负责，并在文档中明确分层。

## 推荐修正方案

将正式的 `json_schema` 改为 envelope Schema：

- 根对象包含 `schema_version`、`family_id`、`parameters`；
- 正式 Schema 的 `parameters` 下描述六个参数；
- 长度参数支持当前 Python 接口接受的两种表示：裸数字（按 mm 解释）或 `{value: number, unit: string}`；
- `second_screw` 保持无量纲整数 0/1，不接受长度单位；
- `additionalProperties: false` 的范围要与正式 envelope 和参数对象一致；
- 如果保留内部扁平对象描述，另存为明确命名的 normalized/internal schema，不能继续把它称为唯一正式输入 Schema。

你可以选择把 envelope 字段设为正式必填，同时保留 Python 对缺失 `schema_version`/`family_id` 的过渡兼容；如果这样做，必须在 README 中明确“JSON Schema 是正式外部协议，Python 兼容入口允许简化输入”。不要静默改变已有调用方。

## 测试要求

补充或调整测试，至少覆盖：

1. 正式 envelope + 裸数字参数可以通过 Schema/校验路径；
2. 正式 envelope + `{value, unit}` 参数可以通过并归一化为 mm；
3. 缺少 `parameters`、未知 envelope 字段、错误 `family_id` 或错误 `schema_version` 会得到结构化错误；
4. 扁平对象仍按兼容路径工作，并在文档中标明不是正式 envelope；
5. `schema-v0.json` 的根结构、必填字段、参数属性和单位对象与 README 示例一致；
6. 原有 13 个测试继续通过；
7. 目录耦合和跨字段规则仍由 Python 校验器测试，不能声称仅靠 JSON Schema 已经完成这些规则。

如果没有 `jsonschema` 依赖，不要为了这一修正引入大型新依赖；可以用结构断言和现有 Python 校验测试验证生成文件，并在交接中说明没有执行第三方 JSON Schema validator。若仓库已有 JSON Schema validator，再增加一条真实验证测试。

## 文件范围

允许修改：

- `src/schema/set_screw_shaft_collar.py`
- `agent-work/schema-rules/CAD-003-schema-v0/schema-v0.json`
- `agent-work/schema-rules/CAD-003-schema-v0/README.md`
- `tests/schema/test_set_screw_shaft_collar.py`
- `agent-work/schema-rules/CAD-003-schema-v0/checkpoint.md`

不要修改 DATA-003 审计材料、Typed CAD IR、生产 CAD 构造器或其他 Agent 的工作。

## 三层交接检查（高风险任务，必须执行）

本任务涉及接口、数据来源或 CAD 执行链，必须执行 `docs/coordination/handoff-review-protocol.md` 中的 double check。

如果本任务是续任任务，开始实现前必须：

1. 阅读上一个 Agent 的 checkpoint、交接文档和提交；
2. 复跑至少一条上一个 Agent 声称通过的核心命令；
3. 检查一个正常案例和一个失败/拒绝案例；
4. 确认输入输出接口、版本、来源和已知限制与本任务一致。

如果交接记录与实际结果不一致，先记录 `review` 或 `blocked`，不要直接覆盖前一个 Agent 的成果。

完成交接前必须记录：修改内容、实际命令及结果、已确认内容、未解决问题和下一 Agent 的重点。`checkpoint.md` 中必须包含 `handoff_self_check` 和（如有前序任务）`handoff_successor_check`。续任复核是定向复核，不替代 Codex 中枢的最终独立审查。

## 验收条件和交接

运行：

```bash
python3 -m unittest discover -s tests/schema -p 'test_*.py' -v
python3 -m py_compile src/schema/set_screw_shaft_collar.py
python3 -m json.tool agent-work/schema-rules/CAD-003-schema-v0/schema-v0.json >/dev/null
```

交接格式：

```text
task=CAD-003-R1
status=review | blocked
changed=<文件列表>
verified=<命令和结果>
canonical_input=<正式 envelope 结构>
compatibility=<扁平输入是否保留及边界>
cross_field_rules=<仍由 Python 规则负责的内容>
known_limits=<未覆盖的验证能力>
next=Codex 审查后决定是否启动 IR-001
```

提交信息使用：

`fix: align schema json boundary [CAD-003-R1]`

完成后不要自行把 CAD-003 标记为 done；等待 Codex 中枢审查。
```
