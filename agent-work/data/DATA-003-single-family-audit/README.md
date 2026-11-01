# DATA-003：BenchCAD 单族来源、环境与最小 smoke test

这是 DATA-002 数据优先计划下的第一个可执行纵向切片工作区。

## 输出文件

- `source-audit.md`：来源 URL、commit、族路径、状态和许可证证据。
- `candidate-matrix.md`：首族候选、第二族候选和回退候选的存在性/运行性/许可比较；不直接冻结最终族。
- `environment.md`：操作系统、架构、Python、CadQuery/OCP、安装命令和依赖结果。
- `run-log.md`：README/源码中发现的入口、实际执行命令、参数、stdout/stderr 摘要和退出码。
- `minimal-manifest.json`：通过审计的最小字段清单和临时产物哈希；不嵌入大文件。
- `checkpoint.md`：阶段完成比例、已验证内容、阻塞项和下一步。

外部源码、虚拟环境、STEP、网格和缓存放在项目根目录下被忽略的 `work/benchcad-source/` 或 `work/benchcad-output/`，不要提交。正式事实仍需由 Codex 中枢审查后同步到 `docs/`。
