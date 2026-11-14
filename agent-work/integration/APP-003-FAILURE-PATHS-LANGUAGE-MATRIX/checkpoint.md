# APP-003-FAILURE-PATHS-LANGUAGE-MATRIX checkpoint

- 日期：2026-11-14
- 状态：review
- 分支：`codex/APP-003-FAILURE-PATHS-LANGUAGE-MATRIX`
- 基线：`main=5d46abf`
- 目标：先收束产品失败路径，再准备下一轮窄范围语言样本；本轮不运行真实模型、不创建 batch、不读取密钥或旧 raw 正文。

## 已完成

1. 固定 CAD venv Python 3.11.18 基线：Product Live 107 项、Product Live UI 36 项、C1/C2/C3 183 项、pipeline/schema-to-IR 81 项通过。
2. 离线复现同一 frozen `input_id` 重复 create 的跨 run 隔离缺陷：首次确认成功后，第二次抽取仍得到相同 `logical_run_id`；`get()` 返回第一次的 confirmed state，下载 API 也返回第一次的 STEP。
3. 给服务层每次 create 分配独立 UUID run identity，并补回归测试：第二次创建获得独立状态，不得得到旧 STEP；首次已确认 run 的状态及下载仍保持可用。
4. 增加 HTTP 级重复创建回归：第二次 run GET 状态为 needs_confirmation、下载 403；首次 run 仍成功下载其原 STEP。
5. 建立 `failure-paths-and-language-matrix.md`，列出失败路径现状、测试覆盖/缺口及 10 条下一轮语言样本草案。样本/标签分离，候选 scope 仅 DeepSeek、C0、无检索，未冻结且不授权执行。

## 验证

- `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_live.TestProductLiveServiceUnit.test_repeated_input_creates_isolated_run_and_never_returns_old_step -v`：通过。
- `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.integration.test_product_live -q`：109 项通过（含 HTTP 重复创建回归）。
- `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest tests.demo.test_product_live_ui tests.demo.test_product_flow tests.demo.test_product_ui tests.demo.test_demo_handler tests.integration.test_pipeline tests.integration.test_schema_to_ir -q`：300 项通过。
- `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/schema -p 'test_*.py' -q`：17 项通过。
- `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m unittest discover -s tests/cad_compilation -p 'test_*.py' -q`：13 项通过。
- `PYTHONPATH=src:. work/benchcad-output/venv/bin/python -m py_compile src/integration/product_live_runner.py tests/integration/test_product_live.py`：通过。
- `git diff --check`：通过。
- 测试输出存在项目既有 HTTP socket `ResourceWarning`；无失败。

## 未完成 / 下一步

- 检查 run identity 改变对正式 batch summary keys、history/API 和离线 UI 调用方的兼容性；当前服务是离线注入入口，正式 runner 的冻结逻辑 ID 未改。
- 对代码改动及语言矩阵草案进行独立复核；完成后再决定收束或窄修。
- 语言矩阵只是设计草案，需独立审查并由负责人批准后才可冻结 scope；真实调用仍需新 batch、预算、preflight 和单独执行授权。

## handoff_self_check

```text
changed=ProductLiveService 每次 create 使用独立 UUID logical_run_id；新增相同 input 重复创建后隔离旧 STEP 回归；新增失败路径/语言矩阵草案
commands=Python 3.11.18 targeted regression 1/1; Product Live 109/109; UI+C1/C2/C3+pipeline/schema-to-IR 300/300; Schema 17/17; CAD compilation 13/13; py_compile; git diff --check
confirmed=此前同一 input_id 重复创建会 GET/下载返回旧 confirmed run 的 STEP；修复后不同 logical_run_id，第二次未确认状态无 STEP，首个 run 仍独立可下载
unresolved=独立复核；语言样本待审阅/批准；没有 live 请求
next_agent_focus=核查 UUID identity 在 state/HTTP confirm/get/download 的一致性与兼容性；评估测试矩阵缺口及 10 条语言草案的标签/预期行为，提出必要窄修
```
