# APP-003-LANGUAGE-MATRIX-20261115-01 checkpoint

- 日期：2026-11-15
- 状态：review
- 目标：基于既有失败路径及语言覆盖计划，形成下一轮全新中文语言样本设计；本轮只整理离线候选，不创建 batch、不运行 preflight、不调用模型/网络/CAD、不读取凭据或历史 raw 正文。
- 基线：`main=b791f52`（本地 ahead origin/main 1）；工作分支 `codex/APP-003-LANGUAGE-MATRIX-NEXT-DRAFT`。

## 产物

- `model-inputs.json`：10 条新候选输入，scope id `app003-product-language-next.v1`。
- `evaluator-labels.json`：独立 evaluator-only 标签；只供后续评审，不得进入模型侧流程。
- `scope.md`：目标、边界、接受标准、预算建议和后续 gate。
- 当前草案 SHA-256：inputs `66b61a476b16d79030bced380f1afbc4d907c05ec2aae984e4e1777dda5d26ed`；labels `9ca60bd3b91a260a8ad71bfd9c1433f8f0150260a0baf3935d51c8036726ee14`。

## 已核对

- 阅读 `AGENTS.md`、PROJECT_STATUS、PROJECT_PLAN、DECISIONS、WORKLOG、handoff review protocol 和 project memory playbook。
- 核对既有十条样本、产品 live 的 P1–P4、ADR-0024、`src/schema/set_screw_shaft_collar.py` 当前目录与 `second_screw` 严格阈值规则。
- 新样本以表达/语义现象为主，避免复制旧句子；范围仍是 DeepSeek `deepseek-flash`、C0、无检索和当前单一零件族。
- 旧 `product_language.v1` profile 固定绑定旧输入 hash；本候选没有复用授权、batch 或 preflight。

## 验证与限制

- `PYTHONPATH=src:. python3` JSON/ID顺序/数量/输入与labels物理分离校验通过；Schema 定向核对 N01=30 mm、N02=70 mm/单螺钉合法、N03=80 mm/单螺钉冲突拒绝、N10 派生 width=12 mm 均通过；`git diff --check` 通过。
- 已对照 schema 确认目录 30 mm、bore_d=70 的 second_screw=0、bore_d=80 的 second_screw=1、bore_d=12 的派生 width=12；此为规格静态核对，不是模型抽取或 CAD 测试。
- 尚未实施 profile/runner，也未运行测试或 preflight；本候选不构成冻结 scope、真实模型效果证据或执行授权。
- 历史 batch 保持只读；`FORMAL_EVALUATION_ALLOWED=False`。

## handoff_self_check

```text
changed=本目录新增 model-inputs.json、evaluator-labels.json、scope.md；PROJECT_STATUS/PROJECT_PLAN/WORKLOG 同步
commands=PYTHONPATH=src:. python3 JSON/ID/order/separation/hash validation PASS; schema rule checks N01/N02/N03/N10 PASS; git diff --check PASS
confirmed=候选 10 条输入与独立标签已形成；不复用旧授权 profile 或 batch；没有真实模型/CAD运行
unresolved=输入和标签仍待负责人/独立复核；尚未实现新 profile/runner
next_agent_focus=逐条检查标签是否符合现行 v5 contract 和 CAD-003规则；确认 N08/N09 物理配合口径；验证标签不进入任何模型可读路径；不执行 live
```

## Codex review pass

- 对草案做了第二轮口径检查，将 evaluator 标签拆为 `preferred_decision` 与 `acceptable_decisions`，避免把安全 `ask` 和最佳抽取混为一谈；负向样本仍必须在 CAD 前阻断。
- 自我更正样本允许 answer 或保守 ask；只有明确采用最终 12 mm 并经负责人确认时才允许构造。N08/N09 的轴径属于上下文事实，不伪装成 Schema 参数字段；N10 的宽度下限属于请求约束，解析出的 `width` 仍为目录派生。
- 本轮审查仅为同一 Codex 的复核精炼，不声称是独立审查。labels hash 已更新；其它范围和禁止项不变。

## Independent review refinement

- 日期：2026-11-15；状态继续为 `review`，本轮只修候选 scope/labels 口径，不冻结矩阵、不授权 preflight 或 live 请求。
- 输入：独立复核结论 `review`，要求修正 scope 中过期的 labels SHA、明确 evaluator 字段映射、分开安全可接受与当前 v5 策略通过，并特别核验 N04 的更正值和 N08/N09 的策略覆盖边界。
- 修改：`scope.md` 更新为 labels SHA-256 `9ca60bd3b91a260a8ad71bfd9c1433f8f0150260a0baf3935d51c8036726ee14`；`evaluator-labels.json` 声明单位化标签到 v5/Schema 字段的映射，并为每条输入分列安全决策/门与 v5 策略评估。N01/N02/N04/N10 的 `ask/refuse` 标为安全可阻断但属于 P1-1 over-refusal；N05–N07 标为部分强制（checker 只拒绝已识别 unsupported 后仍 answer，不保证识别本身）；N08/N09 明确标为当前策略未定义、不计策略分，同时仍要求 CAD 前安全阻断。N04 增加最终构造参数必须 `bore_d=12` 且排除 superseded `10` 的断言。
- 范围：没有修改输入、prompt、Schema、IR、provider、runner、profile、授权或历史批次；没有创建 batch、运行 preflight、调用模型/网络/CAD，也没有读取凭据或历史 raw 正文。`FORMAL_EVALUATION_ALLOWED=False` 未改变。
- 验证：JSON 解析、ID 顺序/数量、输入与 evaluator labels 文本隔离、v5 策略分类、字段映射、N04 正反值断言、scope hash 与文件 hash 一致性检查通过；`git diff --check` 通过。未运行测试套件或任何执行路径。
- 未解决：矩阵仍待独立复核和负责人接受；N08/N09 暴露的策略能力缺口不在本轮修补，需未来单独决策是否修改 v5 策略或将安全识别放在另一层。
- 下一步：独立复核更新后的 labels/scope 口径；复核通过且负责人接受后，才讨论新版本化 profile 与离线测试。

## Owner acceptance

- 日期：2026-11-15；项目负责人已接受本矩阵进入离线实现阶段。
- 接受对象：scope `app003-product-language-next.v1`；inputs SHA-256 `66b61a476b16d79030bced380f1afbc4d907c05ec2aae984e4e1777dda5d26ed`；evaluator labels SHA-256 `9ca60bd3b91a260a8ad71bfd9c1433f8f0150260a0baf3935d51c8036726ee14`。
- 允许范围：实现新的版本化 profile、离线 preflight/runner 接口和测试；保持 DeepSeek `deepseek-flash` / C0 / 无检索 / 单族范围，不改旧 profile、旧 batch、prompt、Schema、IR、provider 或全局 formal gate。
- 禁止事项：本阶段不创建 batch、不读取凭据、不运行 formal preflight、不调用模型/网络/CAD，不改变 `FORMAL_EVALUATION_ALLOWED=False`。真实执行需要另行 batch、preflight 和负责人授权。
- 下一步：交给实现 Agent 开始离线 profile/runner 工作；完成后由 Codex 中枢独立复核固定环境测试、标签隔离、预算与 fail-closed 边界。

## APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE implementation

- 日期：2026-11-15；分支 `cc/APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE`；状态：review（等待 Codex 中枢独立复核）。
- 任务 ID：APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE；基线 HEAD `5b64cfb`（codex/APP-003-LANGUAGE-MATRIX-NEXT-DRAFT）；已接受决策 ADR-0025。

### 新增文件

- `src/llm/product_language_next_authorization.py`：独立版本化 profile，绑定 scope `app003-product-language-next.v1`、N01–N10 10 条输入、inputs/labels 双 hash、provider/model/condition、budget 20×2；与旧 `product_language_authorization.py` 完全隔离，不共享常量或类。
- `src/integration/product_language_next_formal_runner.py`：离线 formal runner；读取 `agent-work/integration/APP-003-LANGUAGE-MATRIX-20261115-01/model-inputs.json`（新 JSON 结构：`{scope_id, inputs: [{input_id, condition, request_text}]}`）；从不打开 `evaluator-labels.json`；离线 preflight + FakeTransport mock runner；`FORMAL_EVALUATION_ALLOWED=False` 保持不变；无新通用 live 开关。
- `tests/integration/test_product_language_next_scope.py`：39 条 profile/authorization/binding/preflight 测试；evaluator-labels.json 隔离验证；budget 常量和 N 前缀 ID 断言。
- `tests/integration/test_product_language_next_formal_runner.py`：74 条 runner 测试；覆盖：approval gate / preflight fail-closed / FakeTransport answer/ask/refuse/unsupported/invalid JSON/transport error / retry 分类 / budget 常量 / summary 路径 hash 隔离 / N04 self-correction bore_d=12/10 断言 / N08/N09 无 policy_ok 字段 / N05–N07 unsupported blocking / 旧 profile 类型被 runner 拒绝。

### 验证

- `python3 -m py_compile` 四个新文件全部通过。
- `PYTHONPATH=src:. python3 -m unittest tests.integration.test_product_language_next_scope tests.integration.test_product_language_next_formal_runner`：**113/113 OK**，0 failures，0 errors。
- `git diff --check`：通过，无 trailing whitespace。
- 沙箱 Python 3.10.12（非固定 CAD venv Python 3.11.18）；固定 CAD venv 全量验证留给 Codex 中枢复核。

### 未运行

- 真实 DeepSeek HTTP 请求（`FORMAL_EVALUATION_ALLOWED=False`，无凭据加载）。
- 正式 preflight（无 batch 目录创建，无 BudgetLedger 初始化）。
- CAD/STEP/IR pipeline（runner 中明确禁止）。

### handoff_self_check

```text
changed=src/llm/product_language_next_authorization.py（新）；src/integration/product_language_next_formal_runner.py（新）；tests/integration/test_product_language_next_scope.py（新）；tests/integration/test_product_language_next_formal_runner.py（新）；checkpoint.md（追加本段）；docs/WORKLOG.md（追加记录）
commands=py_compile 4 files PASS; PYTHONPATH=src:. python3 -m unittest scope+runner tests 113/113 OK; git diff --check PASS
confirmed=新 profile 与旧 profile 隔离；evaluator-labels.json 未被读取；FORMAL_EVALUATION_ALLOWED=False 保持不变；未创建 batch/preflight/CAD/网络调用；N04 bore_d=12 断言通过；N08/N09 无 policy_ok 字段断言通过；N05-N07 unsupported blocking 断言通过
unresolved=固定 CAD venv Python 3.11.18 全量验证待 Codex 中枢复核；真实网络/preflight/CAD 执行未运行
next_agent_focus=Codex 中枢：在固定 CAD venv 下运行 113 条专项测试，验证 evaluator-labels 隔离、budget 常量、fail-closed 边界；复核通过后状态可改为 done
```

## ADR-0025 offline-gate fix (narrow patch)

- 日期：2026-11-15；分支 `cc/APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE`；基线提交 `aa1490b`；状态：review。
- 修复原因：Codex 中枢验收意见 — 原 runner 包含可执行真实请求的 formal 路径（`transport=None` → 凭据加载 → batch/ledger 创建 → DeepSeek 调用），该入口违反 ADR-0025 的离线阶段边界。

### 修改内容（窄修）

- `src/integration/product_language_next_formal_runner.py`：
  - 重写 `run_product_language_next_formal_batch`，在 Gate 3 对 `transport=None` 和任何非 `FakeTransport` 均抛出 `LanguageNextOfflineOnlyError`，拒绝发生在任何凭据读取、目录创建、BudgetLedger 初始化和网络 I/O 之前。
  - 完全删除真实 formal 执行路径：凭据加载（`load_deepseek_environment`）、`DeepSeekTransport` 构造、`BudgetAwareTransport`、`BudgetLedger` 初始化、正式 batch/raw 目录创建、`RetentionPolicy`、Adapter 实例化及其全部 I/O 路径。
  - 删除 `LanguageNextConfigurationError`（无 live 路径后不再需要）。
  - 文档字符串更新为明确的 "offline-mock-only" 语言，模块标题移除 "formal runner"。
  - 保留：FakeTransport mock 路径、preflight、`_SummaryWriter`、状态常量、所有已有的 fail-closed 行为。
- `tests/integration/test_product_language_next_formal_runner.py`：
  - 新增 `TestADR0025OfflineGate`（13 个测试）：`transport=None` 抛出 `LanguageNextOfflineOnlyError`；非 FakeTransport 也抛出；`transport=None` 时 `load_deepseek_environment`、`BudgetLedger`、`DeepSeekTransport`、`Path.mkdir`、`urlopen` 均未被调用；`LanguageNextOfflineOnlyError` 消息包含 "offline" 和 "ADR-0025"；Gate 1/Gate 2 在 Gate 3 之前触发；FakeTransport 仍正常接受。

### 验证

- `py_compile` 两个修改文件 PASS。
- `PYTHONPATH=src:. python3 -m unittest` 新版 scope+runner 专项测试 **126/126 OK**（+13 ADR-0025 gate 测试）。
- 旧 scope + formal runner 回归 **226/226 OK**（含新版）。
- inputs SHA-256 `66b61a476b16d79030bced380f1afbc4d907c05ec2aae984e4e1777dda5d26ed` 和 labels SHA-256 `9ca60bd3b91a260a8ad71bfd9c1433f8f0150260a0baf3935d51c8036726ee14` 均未改变。
- `git diff --check` PASS。
- 沙箱 Python 3.10.12（非固定 CAD venv Python 3.11.18）；固定 CAD venv 全量验证留给 Codex 中枢。

### 未运行

- 真实 DeepSeek HTTP 请求（入口已封闭）。
- 正式 preflight（无 batch 目录创建，无 BudgetLedger 初始化）。
- CAD/STEP/IR pipeline。

### handoff_self_check

```text
changed=src/integration/product_language_next_formal_runner.py（formal 路径删除，Gate 3 新增 LanguageNextOfflineOnlyError 拒绝）；tests/integration/test_product_language_next_formal_runner.py（新增 TestADR0025OfflineGate 13 条测试）；checkpoint.md（追加本段）；docs/WORKLOG.md（追加记录）
commands=py_compile 2 changed files PASS; PYTHONPATH=src:. python3 -m unittest scope+runner 126/126 OK; old+new combined 226/226 OK; git diff --check PASS; SHA-256 constants verified unchanged
confirmed=transport=None 和非 FakeTransport 均被 Gate 3 拒绝；凭据/BudgetLedger/DeepSeekTransport/mkdir/urlopen 零调用断言通过；FakeTransport 正常案例（answer 10/10）和失败案例（error/blocked）均通过；旧实现未被修改
unresolved=固定 CAD venv Python 3.11.18 全量验证待 Codex 中枢复核；真实执行仍需新独立 scope/preflight/负责人授权
next_agent_focus=Codex 中枢：固定 CAD venv 下运行 126 条专项测试，验证 Gate 3 拒绝、evaluator-labels 隔离、budget 常量、fail-closed 边界；通过后可讨论状态改为 done
```

## FakeTransport subclass gate fix (narrow patch)

- 日期：2026-11-15；分支 `cc/APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE`；基线提交 `fcdd538`；状态：review。
- 修复原因：Codex 中枢复核发现 Gate 3 使用 `isinstance` 允许 FakeTransport 子类绕过离线门控并执行自定义 `send()` 10 次。

### 修改内容

- `src/integration/product_language_next_formal_runner.py`：Gate 3 由 `not isinstance(transport, FakeTransport)` 改为 `type(transport) is not FakeTransport`，拒绝 `None`、非 FakeTransport 和 FakeTransport 子类。
- `tests/integration/test_product_language_next_formal_runner.py`：新增 4 条子类回归测试（`TestADR0025OfflineGate` 新增 `test_fake_transport_subclass_raises_offline_only_error`，断言 send_call_count=0；`test_fake_transport_subclass_no_credentials_loaded`；`test_fake_transport_subclass_no_mkdir`；`test_offline_error_mentions_subclass`）。
- `docs/PROJECT_STATUS.md`：追加 APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE 条目，状态 review，说明真实执行仍须独立 scope/preflight/负责人授权。
- `docs/PROJECT_PLAN.md`：将矩阵任务行改为已完成 `[x]`，标注当前 review 状态。

### 验证

- `py_compile` 两个修改文件 PASS。
- `PYTHONPATH=src:. python3 -m unittest` 新版专项测试 **130/130 OK**（+4 子类 gate 测试）。
- 旧 scope + formal runner + product live + schema 合计 **209/209 OK**。
- inputs SHA-256 `66b61a476b16d79030bced380f1afbc4d907c05ec2aae984e4e1777dda5d26ed` 和 labels SHA-256 `9ca60bd3b91a260a8ad71bfd9c1433f8f0150260a0baf3935d51c8036726ee14` 未改变。
- `git diff --check` PASS。
- 沙箱 Python 3.10.12（非固定 CAD venv Python 3.11.18）；固定 CAD venv 全量验证留给 Codex 中枢。

### handoff_self_check

```text
changed=src/integration/product_language_next_formal_runner.py（isinstance → type(...) is 精确检查）；tests/integration/test_product_language_next_formal_runner.py（+4 子类 gate 测试）；docs/PROJECT_STATUS.md（追加 APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE review 状态条目）；docs/PROJECT_PLAN.md（矩阵任务行改为 [x] review）；checkpoint.md（追加本段）；docs/WORKLOG.md（追加记录）
commands=py_compile 2 changed files PASS; PYTHONPATH=src:. python3 -m unittest next scope+runner 130/130 OK; old+live+schema combined 209/209 OK; git diff --check PASS; SHA-256 constants verified unchanged
confirmed=FakeTransport 子类 send() 零调用断言通过；transport=None 和非 FakeTransport 仍被正确拒绝；FakeTransport 正常案例 10/10 answer 通过；旧实现未被修改
unresolved=固定 CAD venv Python 3.11.18 全量验证待 Codex 中枢复核；真实执行仍需新独立 scope/preflight/负责人授权
next_agent_focus=Codex 中枢：固定 CAD venv 下运行 130 条专项测试，重点验证 Gate 3 子类拒绝、zero send call count、evaluator-labels 隔离；通过后可讨论状态改为 done
```


## Codex 中枢独立复核（f279bc8）

- 日期：2026-11-15；基线分支 `cc/APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE`，HEAD=`f279bc80dd95fa9c02bc10493122ca3d306cdfef`；main=`b791f526bedf7bf93c235929611d9873151ad639`；工作区干净。
- 复核结论：窄修独立复核通过；任务保持 `review`，等待按流程合入。Gate 3 精确拒绝 FakeTransport 子类，覆写 `send()` 的子类被拒绝且零调用；`transport=None` 和普通非 FakeTransport 也被拒绝。
- 固定 CAD venv Python 3.11.18 实测：`tests.integration.test_product_language_next_scope tests.integration.test_product_language_next_formal_runner` 130/130；旧 `tests.integration.test_product_language_scope tests.integration.test_product_language_formal_runner` 100/100；`tests.integration.test_product_live` 109/109；Schema 17/17。修改文件 `py_compile`、`git diff --check main..HEAD`、`git show --check HEAD` 均通过。
- hash：inputs=`66b61a476b16d79030bced380f1afbc4d907c05ec2aae984e4e1777dda5d26ed`；labels=`9ca60bd3b91a260a8ad71bfd9c1433f8f0150260a0baf3935d51c8036726ee14`。
- 边界：未读取凭据或 labels 内容；未创建 batch、未运行正式 preflight、未调用模型/网络/CAD；`FORMAL_EVALUATION_ALLOWED=False` 保持。Product Live 回归有既存 socket `ResourceWarning`，测试通过。
- 下一步：等待合入；合入后在 main 基线复验必要专项。真实执行仍需新的独立 scope、preflight 与负责人授权。

## Merge and closeout

- 日期：2026-11-15；任务状态：`done`。
- 合并：负责人将 `cc/APP-003-LANGUAGE-SAMPLE-NEXT-PROFILE` 快进合入 `main`；最终 HEAD=`334723bcdcc083d0efdebb9c0464390ce18b0a89`，并推送至 `origin/main`。合入后 `main` 与 `origin/main` 一致，工作区干净。
- 合入后复验：固定 CAD venv Python 3.11.18 执行 `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_language_next_scope tests.integration.test_product_language_next_formal_runner -q`，130/130 通过。
- 独立复核既有定向回归：新 profile/runner 130/130、旧 language scope/runner 100/100、Product Live 109/109、Schema 17/17；`py_compile`、`git diff --check main..HEAD`、`git show --check` 均通过。Product Live 存在既有 socket `ResourceWarning`，不影响测试通过。
- 收束边界：离线 profile/runner 工作单元完成；未创建 batch、未读取凭据或 evaluator labels 内容、未调用模型/网络/CAD/STEP；`FORMAL_EVALUATION_ALLOWED=False` 保持。未来真实请求须新建独立 scope 和 batch，完成适用 preflight 并取得负责人明确授权。
- 下一步：如负责人继续扩展语言样本的真实效果证据，先提出独立假设与新 scope；本实现本身不授权创建 batch 或发起请求。
