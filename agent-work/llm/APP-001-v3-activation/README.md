# APP-001 extraction v3 activation package (staged)

状态：`prepared-not-active`。

本目录是 `app001-extraction.v3` 的版本化激活准备包，不是生产冻结目录。`prompt-v3.md` 从候选 prompt 复制而来，必须与候选源文件通过 SHA-256 比对后才能进入新的 ADR 激活流程。

当前生产路径仍使用 `app001-extraction.v2`：`src/llm/contract.py`、`src/llm/parser.py` 和 `src/llm/prompt_loader.py` 没有修改，`FORMAL_EVALUATION_ALLOWED` 仍为 `False`。本包不授权模型调用、不改变旧批次，也不改变 `acceptance-set-v0`。

激活前必须完成：

1. 项目负责人接受 ADR-0016（目前为 `proposed`）；
2. 在 Python 3.11.18 下重跑候选专项、LLM 全量和 Schema 全量测试；
3. 将 `contract.py` 的 prompt 版本、`parser.py` 的版本检查和 `prompt_loader.py` 的路径/版本/文件哈希作为同一提交更新；
4. 记录激活前后的接口、哈希和回滚点；
5. 另行取得新的唯一批次授权后，才允许任何真实模型请求。

回滚方式：恢复生产 v2 文件和其 `d95f853d...` 文件哈希锚点；不修改或重写任何历史批次。
