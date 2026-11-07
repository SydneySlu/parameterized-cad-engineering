# APP-001 v3 激活检查清单

## 当前状态

- [x] 候选 v3 离线专项测试通过，覆盖 A01-A09 的样例登记、正常/拒绝/澄清边界、主张保留、目录表一致性和 retrieval reference 隔离。
- [x] 生成版本化 prompt 副本和 SHA-256 manifest。
- [x] 生产 v2 路径、冻结哈希、旧正式批次保持不变。
- [ ] 项目负责人接受 ADR-0016。
- [ ] Python 3.11.18 环境复核通过。
- [ ] 生产激活提交同时更新 `contract.py`、`parser.py`、`prompt_loader.py` 和对应测试。
- [ ] 激活后的 prompt/system/user 哈希和版本记录写入审查文档。
- [ ] 新的唯一正式批次授权（若要测模型）单独取得。

## 计划中的生产改动（本阶段不执行）

- `src/llm/contract.py`: `PROMPT_VERSION` 从 v2 改为 v3。
- `src/llm/parser.py`: 接受并校验 v3 版本标记。
- `src/llm/prompt_loader.py`: 指向本包中的正式冻结 prompt，更新版本标记和文件级 SHA-256。
- 测试与运行记录：增加 v3 版本/哈希断言，并确认 v2 旧批次仍可只读解析。

## 退出条件

只有在上述生产改动完成、测试和审查通过、并由项目负责人决定是否开新批次后，才能把本包状态改为 `active`。在此之前必须保持 `prepared-not-active`。
