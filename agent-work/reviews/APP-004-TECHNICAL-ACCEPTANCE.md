# APP-004 技术验收与交付记录

- 日期：2026-11-15
- 验收人：Codex 中枢
- 验收基线：`main`，起始 HEAD=`6b90c1998134e1629102720a659fdeae2e027869`，起始工作区干净
- 固定环境：`work/benchcad-output/venv/bin/python`，Python 3.11.18；项目固定 CadQuery/OCP 环境
- 结论：**通过，限于单族轻量技术演示和已审查的受控运行范围**

## 验收范围

本次 APP-004 汇总并复核轻量版产品链路的交付证据：冻结单族输入，经 v5 抽取/决策契约、CAD-003 Schema、Typed CAD IR、白名单 CadQuery 编译、几何验证与 STEP 导出/回读，进入 C1/C2/C3 本地交互流程及受控 Product Live API/UI。验收以仓库中已归档的独立审查、任务 checkpoint、固定环境测试为证据；本轮额外重跑固定 CAD venv 下的完整 `tests/{llm,integration,demo,schema,cad_compilation}` 套件。

本次没有发起真实 provider 请求、创建或修改 live batch、运行 formal preflight，也没有把 synthetic fixture/mock 结果计作模型效果。语言样本下一轮 profile 按 ADR-0025 保持 offline-mock-only；`FORMAL_EVALUATION_ALLOWED=False` 未改变。

## 交付验收

| 验收项 | 证据 | 结论 |
|---|---|---|
| 单族确定性规则与构造链 | CAD-003 Schema 17 项、CAD 编译/几何/STEP 13 项；A2 里程碑 B 验收报告 | 通过 |
| 真实抽取连接与受控成功路径 | 已批准 A2 batch `app002-a2-smoke-20261112-04`：24 mm、80 mm 各生成并回读 STEP；80 mm 触发 `second_screw=1` | 在该批次和输入范围内通过 |
| 缺参和不支持行为在 CAD 前阻断 | A2 `ask` 输入无 CAD；C2/C3 ask-extra 空确认与 ask-missing 空 patch 阻断；unsupported/refuse 路径阻断 | 通过 |
| Schema 冲突与 CAD/STEP 失败 | 显式目录冲突在 Schema 阶段阻断；注入 STEP 导出异常时结果为 failed 且不发布 STEP/index/旧 run 文件 | 通过 |
| 本地产品确认与下载隔离 | C1/C2/C3 localhost/浏览器审查；确认前无 CAD，确认后 child run 独立；下载检查 run 状态、路径 containment、symlink 与 hash | 通过 |
| Product Live 确认 UI | FakeTransport/synthetic 模式浏览器验收：needs_confirmation、阻断、确认、下载、XSS 文本化与 reset | 通过，仅限离线/注入 transport 行为 |
| 新语言矩阵执行边界 | `APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE` Gate 3 精确限制为 FakeTransport；真实执行分支已删除，子类覆写 send 也被拒绝 | 离线隔离通过；不提供真实模型运行能力 |

主要证据文件包括 [A2 里程碑 B 验收](APP-002-A2-MILESTONE-B-ACCEPTANCE.md)、[C1 独立复核](APP-003-C1-codex-review.md)、[Product Live UI 独立复核](APP-003-LIVE-UI-codex-review.md)、[C2 checkpoint](../integration/APP-003-C2/checkpoint.md)、[C3 checkpoint](../integration/APP-003-C3/checkpoint.md)、[APP-003 live batch 独立复核](../integration/APP-003-LIVE-PREFLIGHT-20261114-02/independent-review.md) 和 [下一轮语言 profile checkpoint](../integration/APP-003-LANGUAGE-MATRIX-20261115-01/checkpoint.md)。各证据仅在其记录的基线、批准范围和环境内成立。

## 固定环境回归

在 APP-004 基线 `6b90c19` 使用 Python 3.11.18 固定 CAD venv 实际运行：

| 命令 | 结果 |
|---|---:|
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/llm -p 'test_*.py' -q` | **933 通过，8 个既有 skip（共运行 941 项）** |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/integration -p 'test_*.py' -q` | **527 通过** |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/demo -p 'test_*.py' -q` | **219 通过** |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/schema -p 'test_*.py' -q` | **17 通过** |
| `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q` | **13 通过** |

合计 **1,709 项通过、8 项 skip（共运行 1,717 项）**，无测试失败。LLM skip 属既有环境/外部 Ollama 条件测试；测试日志中的模拟失败诊断是测试断言输出，不代表套件失败。Demo/Live 测试伴有既有 socket/file `ResourceWarning`，CadQuery 依赖伴有上游弃用警告；进程退出码为 0。测试套件未调用真实模型服务；CAD/STEP 测试在临时目录执行。

## 已知限制与明确不作的结论

- **单族范围**：当前支持和验收的族是 `set_screw_shaft_collar`；不证明跨族 Schema、IR、几何或数据许可能力。
- **语言效果有限**：真实模型证据是多个明确授权的小批次。A2 有 3 条输入、2 条生成 STEP、1 条 ask；后续 Product Live 批次有 4 条请求，P1 在单独确认后成功生成 STEP，P2 ask、P3/P4 refuse 阻断。它们不是广泛语言覆盖、统计显著性或泛化证明。下一轮 N01–N10 profile 目前只允许 offline FakeTransport mock。
- **演示级运行**：本次没有做互联网部署、身份认证/多租户审查、并发/压力/长时稳定性测试或灾难恢复演练；不能据此宣称生产就绪。
- **几何用途**：STEP 回读、实体有效性和项目几何比较通过仅证明本项目定义的技术检查；STEP 通过不等于制造认证、强度/公差分析或实际适用性。
- **数据评估限制**：检索 split 仍为 `provisional_small_n`；生成 STEP 的第三方许可范围按 DATA-003 审查记录保留限制；held-out 检索收益仍 deferred/not measured。
- **正式执行 gate**：`FORMAL_EVALUATION_ALLOWED=False`。未来若要运行新的真实语言样本，必须先补齐允许 live 的独立实现/入口、冻结新 scope 与预算、完成正式 preflight，并由负责人在对话框明确批准具体 batch 执行；本报告和离线 profile 不授予此权限。

## APP-004 结论

在上述限定范围内，项目已具备可复现的单族参数化 CAD 技术演示：成功路径可追溯到 STEP，关键缺参/冲突/unsupported/失败路径按规则 fail-closed，用户确认与下载不跨 run 泄漏。APP-004 技术验收及交付记录完成。后续如继续推进，应先确定具体目标：产品稳定性/部署要求、更多语言效果证据，或跨族扩展；三者需要不同范围与验收，不应合成一个批次或任务。
