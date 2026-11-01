# DATA-003-R1：可复现源码快照与几何/拓扑重复性补充 Prompt

将下面的内容发送给刚刚完成 DATA-003 的同一个 Agent。继续使用原聊天框和原工作区，不需要重新分配一个陌生的数据 Agent。

```text
你继续负责参数化 CAD 工程辅助设计项目的 DATA-003，当前是补充任务 DATA-003-R1。不要重新扩大任务范围，也不要实现 Schema、Typed CAD IR、family adapter、LLM、检索系统或生产验证器。

本次只补两项可复现性证据：

1. 建立一个干净、可复现的 BenchCAD source commit 快照；
2. 为已重复运行的 set_screw_shaft_collar 合法案例补充几何/拓扑签名，避免把 STEP 字节哈希当作唯一重复性标准。

## 项目根目录和工作区

```bash
cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
test "$(git rev-parse --show-toplevel)" = \
"/Users/syd/Desktop/参数化 cad 工程辅助设计"
git status --short --branch
```

继续使用：

- 审计记录：`agent-work/data/DATA-003-single-family-audit/`
- 外部源码/临时产物：被忽略的 `work/benchcad-source/`、`work/benchcad-output/`

不要 reset、clean、覆盖或提交其他 Agent 的未提交改动。

## A. 干净 source 快照

当前基准必须保持为：

```text
https://github.com/BenchCAD-org/benchcad-2
035f467142888edfd0bd7cd73906f9b155c8f43c
```

先检查现有 `work/benchcad-source/benchcad-2` 是否是完整、干净的 checkout。若它仍有大量 staged deletion、sparse/incomplete 状态或不是完整工作树，不要把它作为可复现快照。

优先采用以下任一方式建立干净快照：

### 方案 1：完整 checkout

在新的 ignored 目录中 clone/fetch 到指定 commit，确认：

```bash
git rev-parse HEAD
git status --short --branch
git ls-tree -r --name-only HEAD | wc -l
```

工作树必须没有删除/修改状态，且关键文件存在：`README.md`、`LICENSE`、`pyproject.toml`、`uv.lock`、`framework/bench2/__init__.py`、三个候选族目录。

### 方案 2：git archive

如果完整 checkout 受网络或稀疏检出影响，使用固定 commit 的 archive：

```bash
git -C <clean-git-repository> archive --format=tar \
  --prefix=benchcad-2-035f467/ \
  035f467142888edfd0bd7cd73906f9b155c8f43c \
  > work/benchcad-source/benchcad-2-035f467.tar
```

解压到 ignored 目录后，记录源仓库 URL、commit、archive 文件 SHA-256、文件数量、关键文件路径和实际运行目录。不要把 archive 或解压源码提交到项目 Git。

如果仍只能使用 API/raw 快照，必须记录完整的文件清单、每个文件的来源 commit/blob SHA（能获得时）、补充了哪些同 commit 文件，以及为什么不能建立完整 checkout；此结果只能标记 `reproducibility_partial`，不能写成完全可复现。

把快照证据追加到 `agent-work/data/DATA-003-single-family-audit/environment.md`，并在 `checkpoint.md` 写明结果。

## B. 几何/拓扑重复性签名

对已有两个合法案例的两次运行 STEP 做回读。不要只比较 STEP 文件 SHA-256。至少记录以下签名：

- solid 数量；
- shell 数量；
- face 数量；
- edge 数量；
- vertex 数量；
- `isValid()`；
- 体积；
- 包围盒尺寸；
- 必要时按固定精度量化后的面面积/边长度排序摘要。

比较时统一单位和精度，例如体积/长度保留 6 位小数或使用明确的绝对/相对误差阈值。若实体顺序不稳定，按实体签名排序后比较。不要声称“拓扑完全一致”，除非 B-Rep 计数和必要的归一化摘要都一致；若只有实体数、有效性、包围盒和体积一致，应写成“几何/实体级指标稳定，拓扑等价尚未完全证明”。

可以新增一个仅用于审计的脚本到 `work/benchcad-output/`，不要放入生产 `src/`。将摘要追加到 `agent-work/data/DATA-003-single-family-audit/run-log.md`，并在 `minimal-manifest.json` 增加 `repeatability` 字段，但保持其为审计草案，不升级为冻结 Schema。

## 三层交接检查（高风险任务，必须执行）

本任务涉及接口、数据来源或 CAD 执行链，必须执行 `docs/coordination/handoff-review-protocol.md` 中的 double check。

如果本任务是续任任务，开始实现前必须：

1. 阅读上一个 Agent 的 checkpoint、交接文档和提交；
2. 复跑至少一条上一个 Agent 声称通过的核心命令；
3. 检查一个正常案例和一个失败/拒绝案例；
4. 确认输入输出接口、版本、来源和已知限制与本任务一致。

如果交接记录与实际结果不一致，先记录 `review` 或 `blocked`，不要直接覆盖前一个 Agent 的成果。

完成交接前必须记录：修改内容、实际命令及结果、已确认内容、未解决问题和下一 Agent 的重点。`checkpoint.md` 中必须包含 `handoff_self_check` 和（如有前序任务）`handoff_successor_check`。续任复核是定向复核，不替代 Codex 中枢的最终独立审查。

## 交接格式

```text
task=DATA-003-R1
status=review | blocked | done
changed=agent-work/data/DATA-003-single-family-audit/...
source_snapshot=<full_checkout | git_archive | reproducibility_partial>
source_commit=035f467142888edfd0bd7cd73906f9b155c8f43c
verified=<命令和结果>
topology_signature=<比较了哪些指标和结果>
known_limits=<剩余限制>
next=<Codex 中枢下一步>
```

不要修改项目正式状态、任务表或 ADR；由 Codex 中枢审查后同步。
```
