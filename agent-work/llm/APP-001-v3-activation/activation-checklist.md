# APP-001 v3 激活检查清单

## 当前状态

- [x] 项目负责人接受 ADR-0016，允许生产 prompt 版本切换和离线验证。
- [x] 候选 v3 离线专项测试覆盖 A01-A09 的样例登记、正常/拒绝/澄清边界、主张保留、目录表一致性和 retrieval reference 隔离。
- [x] 生产冻结 prompt 已使用正式措辞，并与未修改的候选源分开记录哈希。
- [x] `contract.py`、`prompt_loader.py`、parser 派生版本校验和版本相关测试作为一个工作单元切换到 v3。
- [x] `FORMAL_EVALUATION_ALLOWED` 保持 `False`；无真实模型请求授权。
- [x] Python 3.11.18 下专项、LLM 全量和 Schema 全量复核通过（LLM 576 项通过，8 项既有 FUSE skip；Schema 17 项通过）。
- [x] Codex 中枢独立审查并提交激活单元（合入 `main`：`7dc7a37`）。
- [ ] 如要测模型效果，另行取得唯一正式批次授权。

## 激活内容

- `src/llm/contract.py`: `PROMPT_VERSION` 为 `app001-extraction.v3`。
- `src/llm/parser.py`: 通过共享契约常量拒绝其他版本。
- `src/llm/prompt_loader.py`: 正式路径为本目录 `prompt-v3.md`，锚定版本和文件 SHA-256。
- 生产 prompt SHA-256：`3dd8bd5505e62f6c96b851b292a83a8905743306de62356a4e093b1d0cd1d86b`。
- 候选源文件 SHA-256：`e90ad55ca20cf356c3c143a723da271f1874eb9fa902dd1379d4afba657a8b5b`。
- acceptance-set-v0 保持原哈希 `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`，其中冻结的 `frozen_prompt_version` 是历史元数据，不是当前运行版本字段。

## 回滚

若激活后发现契约/解析/运行记录不一致，将单一激活提交回滚到 v2：恢复 `PROMPT_VERSION`、prompt loader 路径/版本/hash、对应冻结 prompt 断言和文档。v2 prompt 哈希为 `d95f853d325e05d9b045921da994256c7b8656336b5be02d75ced20d22755eac`。不修改或重写历史批次。
