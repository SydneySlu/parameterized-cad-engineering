# APP-001 v4 决策修正候选中枢审查

日期：2026-11-07  
候选提交：`d8961ac`  
审查范围：ADR-0017、v4 candidate prompt/spec、离线测试；不激活、不调用模型。

## 结论

候选在当前阶段通过，建议将 ADR-0017 保持为 `proposed`，允许继续做激活前准备；不建议现在把它标记为 accepted/implemented，也不建议据此启动新批次。

候选只新增三类与 v3 正式批次直接对应的规则：

1. `1.6 cm` 精确换算为 `16 mm` 后命中冻结目录时，不因来源单位而拒绝或追问，并保留原始单位证据。
2. A08 中用户明确的 `bore_d=24 mm` 优先于不可信 retrieval example，不因参考值 20 单独制造追问。
3. unsupported 请求使用稳定规范名 `anodizing`，但 evidence quote 保留用户原文“阳极氧化”。

v3 的目录、安全 gate、主张保留、CAD-003 最终校验和构造边界均保留。生产激活副本、`contract.py`、`parser.py`、`prompt_loader.py`、`adapter.py`、`runner.py`、冻结 acceptance-set 和旧批次均未改；分支与 `main` 的代码差异只有候选测试文件，没有生产代码导入 v4。

## 证据和验证

- v4 候选专项：8/8 通过。
- v3 候选回归：55/55 通过。
- parser 回归：41/41 通过。
- 候选提交前的 LLM 全量：584 通过、8 个既有 FUSE skip；Schema 17/17 通过。
- `py_compile` 与 `git diff --check` 通过。
- active v3 prompt hash 未变；acceptance-set hash 仍为 `ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf`。

## 尚需补强的点

### 1. 目录拒绝措辞存在继承的歧义

候选沿用了 v3 的 `refuse` 条款“bore_d falls outside the catalog range”，而 decision gate 同时正确要求“必须是 15 个离散 selector”。因此 `75 mm` 这种范围内但不在目录中的值在整体语义上会拒绝，但激活前应把该条明确改成“不是 15 个 selector（包括范围内的 75 mm）”，避免模型只读取范围条款。

### 2. 离线测试验证的是文案，不是规则执行

8 项测试确认新增说明、版本隔离、冻结 hash 和安全边界存在；它们没有实现单位换算或 unsupported alias 的可执行 checker，也没有证明模型会遵循 prompt。激活前可补纯函数 fixture checker，至少验证 `1.6 cm -> 16 mm`、`bore_d=24` 覆盖 retrieval 值、`anodized -> anodizing`，并验证 A04/A05/A07/A09 仍禁止 `answer`。这不需要网络或密钥。

### 3. 规范标签是输出策略变化

`anodizing` 规范化不改变 envelope 键集或 parser，但会改变 unsupported 标签的字符串值。激活时必须把该变化写进 v4 manifest/评分说明；历史 v3 的 `anodized` 记录不能回写成 `anodizing`。

## 对 ADR-0017 的建议

建议接受其“候选准备范围”表述，但保留以下状态边界：

- ADR-0017 仍为 `proposed`，生产继续 `app001-extraction.v3`。
- 先补目录措辞和离线 checker，再做独立 v4 activation review。
- 激活后若验证模型效果，使用新的唯一 batch ID，重新取得正式运行授权；不得重写或混合 v3 批次。
- 继续禁用 C2、IR、CAD、geometry、STEP。

本审查没有发现需要回滚 v3 或修改现有正式批次的理由。
