# APP-002-INTEGRATION-A2-SCOPE — CC 工作 prompt

你是 APP-002-INTEGRATION-A2-SCOPE 的执行 CC。A1 已在 `main` 合入 `d6faf70`，固定环境的合成 envelope→STEP 闭环已经通过。现在只准备真实模型整链的受控入口和 scope，不执行 live 模型请求。

开始前必须阅读 `AGENTS.md`、`docs/PROJECT_STATUS.md`、`docs/PROJECT_PLAN.md`、`docs/DECISIONS.md`、`docs/WORKLOG.md`、A1 checkpoint、交接协议和项目记忆手册。确认仓库根目录、分支、HEAD 和工作区；不得覆盖未合并工作。

## 目标

把 A1 的入口扩展设计为可审查的“v5 真实模型→Schema→IR→CadQuery→几何验证→STEP”受控路径，并形成下一轮授权材料。当前不得调用 DeepSeek/Ollama、不得访问网络、不得读取 `.env` 或 API key、不得创建正式 batch。

## 不变量

- v5 prompt、`app001-io.v1`、CAD-003 Schema、Typed CAD IR v0、CadQuery 编译器和几何/STEP 验证器保持不变。
- `FORMAL_EVALUATION_ALLOWED=False` 保持不变；不得复用旧 v4/v5 Schema-only runner 的授权或旧 batch。
- 模型只返回受约束 envelope；不得生成或执行任意 Python。
- ask/refuse、missing、unsupported、Schema/IR/CAD/STEP 任一失败必须停止构造并返回可定位错误；不得返回其他 run 的旧 STEP。
- 每次运行必须关联 request、model response 元数据、参数/来源、IR、验证结果、STEP 和 hash；raw 只允许写入新的、明确授权的 `batch/raw/`。
- 历史批次只读，不读取历史 raw 正文，不移动、改写或混合统计。

## 工作内容

1. 核对现有 `src/llm/adapter.py`、parser、contract、providers、runrecord 和 `src/integration/pipeline.py` 的接口，列出真实模型接入所需的最小连接层，不重复实现 A1 后端。
2. 设计一个独立 A2 入口或 profile：明确输入清单、provider/model、解码参数、重试/预算口径、batch/raw/证据目录、身份记录、错误码和退出码。默认先沿用已审查的 DeepSeek `deepseek-flash`；Ollama 不擅自加入本 scope。
3. 为入口增加**离线** preflight 和 mock 测试，验证：输入与 evaluator 标签隔离、prompt/schema/version/hash 锚定、预算在每次 HTTP 前预留、batch/raw 路径隔离、正式 gate 关闭时零副作用、成功后只接收当前 run 的 STEP。
4. 给出一份待负责人批准的最小真实整链 scope 草案。建议候选为 3 条代表性需求：普通合法孔径 24 mm、第二螺钉边界孔径 80 mm、缺少 bore_d 的追问路径；这只是草案，不是授权。明确它们不是完整效果评测，也不代表泛化结论。
5. 更新 A2 checkpoint、`PROJECT_STATUS`、`PROJECT_PLAN` 和追加 `WORKLOG`，如发现需要改变已冻结架构/协议，先停在 review 并提出 ADR，不静默修改。

## 禁止事项

不得启用 `FORMAL_EVALUATION_ALLOWED`，不得发送任何 HTTP/模型请求，不得读取密钥或 `.env` 值，不得创建正式 batch，不得修改 prompt、Schema、IR 语义、旧 runner、历史批次或把合成 fixture 当作真实模型证据。

## 交付与验收

- 提交一个窄范围 commit，工作区干净；不 push、不合并 main。
- 报告实际修改文件、接口核对、离线测试命令和结果、正常/失败案例、未运行项和待授权内容。
- 只有 Codex 中枢独立复核通过、scope/预算/batch/授权模板获负责人批准后，才可进入 live preflight；本任务本身不跨过该 gate。
