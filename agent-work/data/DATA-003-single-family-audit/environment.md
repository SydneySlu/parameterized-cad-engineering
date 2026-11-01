# DATA-003 环境记录

核查日期：2026-11-01；主机：macOS Apple Silicon (`arm64`)；项目根目录：`/Users/syd/Desktop/参数化 cad 工程辅助设计`。

## 源码

- remote：`https://github.com/BenchCAD-org/benchcad-2.git`
- commit：`035f467142888edfd0bd7cd73906f9b155c8f43c`
- checkout：`work/benchcad-source/benchcad-2/`（网络 clone 的 worktree 在 fetch/index-pack 过程中出现长时间未完成；同时保留同 commit API raw 快照 `work/benchcad-source/api-snapshot-035f467/` 供可重放 smoke 使用；两者均被 `work/` 忽略）
- 未修改 BenchCAD 族源文件。

## 声明依赖与安装

来源：`pyproject.toml:5-25,40-42`、README `:36-43`。

```bash
uv sync
uv run bench2 validate <family>
uv run bench2 preview <family>
```

项目侧实际隔离命令（临时环境在 ignored `work/benchcad-output/venv`）：

```bash
brew install uv python@3.11
uv venv work/benchcad-output/venv --python /opt/homebrew/bin/python3.11
uv pip install --python work/benchcad-output/venv/bin/python -e work/benchcad-source/api-snapshot-035f467
```

安装结果：成功。关键版本：

- Python 3.11.18（满足 `>=3.11,<3.12`）
- `cadquery==2.3.0`
- `cadquery-ocp==7.9.3.0`
- `numpy==1.26.4`
- `vtk==9.5.2`、`ezdxf==1.4.5`、`casadi==3.8.2`、`nlopt==2.11.0`、`pillow==13.0.0`
- uv 0.13.6（Homebrew arm64）

依赖安装未替换仓库声明的 CadQuery/OCP/Numpy 版本；uv 对未锁定的下限依赖解析到了上述实际版本，应在复现时以 `uv.lock`/安装日志为准。

## 官方/实际入口

- 官方 CLI：`bench2 validate <family>`、`bench2 preview <family>`（README）；脚本注册为 `bench2 = "bench2.cli:main"`（pyproject:24-25）。
- 原生 Python API：从 `designs/<family>/part.py` 加载 `build(**named_params)`；约束入口是 `spec.check(params)`，耦合填充入口是可选 `spec.refine(params, difficulty, rng)`。这由 README:21-27 和三族源码共同证实。
- 本任务 smoke 直接调用 `part.build(**params)`，再用 CadQuery `shape.exportStep()` 和 `cq.importers.importStep()` 做 STEP 往返；没有臆造 `preview`/`check` 以外的 CLI。

## 额外文件/系统依赖

- `set_screw_shaft_collar/NOTES.md` 提到外部标准 PDF/SVG/JPG，但本任务未下载、未复制。
- 不需要 Public/Core 评测集；本任务未下载。
- macOS ARM 上官方声明依赖安装可完成；未发现必须替换到非声明版本的失败。
