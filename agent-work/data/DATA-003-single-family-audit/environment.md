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

## DATA-003-R1 source snapshot evidence

现有 `work/benchcad-source/benchcad-2/` 不可作为干净快照：HEAD 仍为 `035f467...`，但 `git status --short --branch` 显示大量 staged deletion，且 `README.md`、`pyproject.toml`、`uv.lock`、`framework/bench2/__init__.py` 和三个候选族的关键文件缺失。尝试 `git archive` 时由于 promisor checkout 缺少 blob，生成了 0 字节无效 tar；GitHub codeload 也在本机网络中截断，未将截断文件当作证据。

按用户指定的 API/raw 退路，从固定 commit 的递归 tree 获取完整 blob 清单并下载全部 217 个 blob，快照目录：

- `work/benchcad-source/benchcad-2-035f467-raw/`
- 清单：`work/benchcad-source/benchcad-2-035f467-raw/SNAPSHOT-MANIFEST.json`
- 递归 tree 中 217 个 blob，成功下载 217，缺失 0；清单记录每个路径、commit 对应 blob SHA、raw URL、文件大小和下载 SHA-256。
- 关键文件均存在：`README.md`、`LICENSE`、`pyproject.toml`、`uv.lock`、`framework/bench2/__init__.py`、三个候选族的 `part.py`。
- 为便于复核生成 ignored tar：`work/benchcad-source/benchcad-2-035f467-raw.tar`
- tar SHA-256：`b390bc953416cfcf27b94b4ec1f497a0ba0ee5f3afb04c4b8454c411fc3c33ad`
- tar 字节数：`31177216`
- tar 条目数：`256`（包含目录项；源文件清单以 `SNAPSHOT-MANIFEST.json` 的 217 个 blob 为准）

## DATA-003-R2 固定快照复核

- 固定输入再次核对为仓库 `https://github.com/BenchCAD-org/benchcad-2`、commit `035f467142888edfd0bd7cd73906f9b155c8f43c`、族 ID `set_screw_shaft_collar`、路径 `designs/set_screw_shaft_collar`。快照中的 `family.json` ID 与目录名一致，存在 `part.py::build()`、`spec.py::check()`；固定 commit `docs/STATUS.md:10` 为 `MERGED`，状态页 `:5` 显示 `0 release-qualified`。
- 本次重查原 promisor checkout：`git -C work/benchcad-source/benchcad-2 rev-parse HEAD` 返回固定 commit，但 `git status --short --branch` 仍含大量 staged deletions；`README.md` 和 `designs/set_screw_shaft_collar/part.py` 不存在。因此它不是干净完整 checkout。该失败情况作为反例保留，没有清理或修改该 checkout。
- 可用快照类型仍为 `reproducibility_partial`，不是完整 Git checkout，也不是官方 `git archive`。API recursive tree/raw 路径快照记录 tree 中 217 个 blob，下载 217、缺 0；原 tar SHA-256 `b390bc953416cfcf27b94b4ec1f497a0ba0ee5f3afb04c4b8454c411fc3c33ad`，大小 31,177,216 bytes。关键文件包括 README、LICENSE、pyproject、uv.lock、framework/bench2/__init__.py 和族 `family.json/part.py/spec.py/NOTES.md`；逐文件 blob SHA、下载 SHA-256、大小和 raw URL 见 ignored `work/benchcad-source/benchcad-2-035f467-raw/SNAPSHOT-MANIFEST.json`。
- 归档/目录核验：`shasum -a 256 work/benchcad-source/benchcad-2-035f467-raw.tar` 与上述 SHA 一致；tar 有 256 个条目（含目录项），清单所列源文件 217 个。运行原生 CLI 后快照工作目录中出现额外 Python `__pycache__` 文件；它们不在 217 个 commit blob 清单内，属于运行时缓存，不是上游源文件。项目不得将此 raw 快照写成 clean checkout/archive。
- 失败原因与补救：原 promisor checkout 缺 blob；旧 `git archive` 结果为 0 字节；此前 codeload 下载截断。因此当前没有真正完整 Git 快照。网络/上游可用后，在新的 ignored 目录完整 clone/fetch 固定 commit，或从已完整仓库生成 archive；核对 HEAD、无工作树改动、tree 文件数和关键文件，再更新 `source_snapshot` 状态。
- R2 核心复跑从 raw 快照实际运行目录 `work/benchcad-source/benchcad-2-035f467-raw/` 执行 `work/benchcad-output/venv/bin/bench2 validate set_screw_shaft_collar --seeds 1`，结果 PASS。正常用例：固定族 `family.json` 存在且 ID 匹配。失败/不完整用例：原 checkout 缺上述关键文件且有 staged deletions，确认该来源不可运行/归档。
- 许可证细项见 `license-matrix.md`。源码 MIT、官方 released dataset CC BY 4.0、项目生成 STEP/渲染物以及 NOTES 外链第三方素材分别处理；生成物与第三方材料保持 `license_scope_uncertain`。Public/Core 未下载，不进入训练、检索或再发布语料。

由于该快照通过 API/raw 重建而非源 Git 仓库的 `git archive`，DATA-003-R1 的 source snapshot 标记为 **`reproducibility_partial`**，不能写成完整 checkout 或官方 git archive。原始 source commit、每个 blob SHA 和完整清单已保存，后续网络恢复后仍应由中枢优先复核一次真正干净 checkout。
