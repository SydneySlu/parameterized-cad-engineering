# IR v0 反序列化语义检查

Draft 2020-12 JSON Schema 负责结构、常量、枚举、参数类型/值类型和 `status` 互斥关系。以下检查依赖数组中元素之间的关系，必须由 IR 反序列化器在 Schema 通过后执行；Schema 通过不等于语义检查通过。

## 稳定错误码

| 检查 | 错误码 | 规则 |
|---|---|---|
| 参数 ID | `IR_DUPLICATE_PARAMETER_ID` | 六个首族参数各出现一次；accepted IR 恰好六项。 |
| 节点 ID | `IR_DUPLICATE_NODE_ID` | `node_id` 在 IR 内唯一。 |
| 输出 ID | `IR_DUPLICATE_OUTPUT_ID` | 所有节点的 `output_id` 全局唯一。 |
| 约束 ID | `IR_DUPLICATE_CONSTRAINT_ID` | `constraint_id` 在 IR 内唯一。 |
| 序号 | `IR_ORDINAL_NOT_CONTIGUOUS` | accepted 节点的 ordinal 是 `0..N-1`，按数组排序后仍与数组顺序一致。 |
| 依赖 | `IR_DEPENDENCY_NOT_PREVIOUS` | `depends_on` 只能指向存在且 ordinal 更小的节点。 |
| 依赖图 | `IR_DEPENDENCY_CYCLE` | 节点依赖图必须无环。 |
| 引用 | `IR_REFERENCE_NOT_FOUND` | parameter/output/constraint/catalog/formula 引用目标必须存在。 |
| 条件 | `IR_CONDITION_PARAMETER_NOT_FOUND`、`IR_CONDITION_TYPE_MISMATCH` | `enabled_if.parameter_id` 必须是已有参数，`equals` 的 JSON 类型必须与参数 `type` 一致；`second_screw` 只能比较整数 0 或 1。 |
| 公式 | `IR_UNREGISTERED_FORMULA` | `formula_id` 必须来自 v0 注册表；递归检查所有 args。 |
| 执行入口 | `IR_EXECUTION_STRING_FORBIDDEN` | 不允许把 expression、placement 或 properties 字符串当作代码；节点 inputs 只能是五种结构化表达式。 |
| 首族包络 | `IR_FAMILY_MISMATCH`、`IR_SCHEMA_VERSION_MISMATCH`、`IR_SNAPSHOT_STATUS_UNSUPPORTED` | v0 首族必须分别为 `set_screw_shaft_collar`、`family.set_screw_shaft_collar.v0`、`set_screw_shaft_collar.v0`、`reproducibility_partial`。 |

## 最小算法

1. 先用 `ir-v0.schema.json` Draft 2020-12 校验；Schema 失败不得进入构造器。
2. 收集参数、节点、输出和约束 ID，按表中错误码检查唯一性。
3. 检查 `ordinal == range(len(nodes))`，再检查每个 dependency 的目标存在、目标 ordinal 更小；对图运行 DFS，发现回边即 `IR_DEPENDENCY_CYCLE`。
4. 递归遍历每个 node input 和 `enabled_if`：检查 parameter/output 引用目标、lookup/formula 注册表和单位；不解析自由字符串。
5. 检查 accepted 六参数的名称、类型、单位、`second_screw` 0/1、首族常量和 `snapshot_status`；rejected 只允许错误记录和空节点，不允许 `validation_result`。
6. 只有上述检查全部通过，适配器才可把 IR 交给 CAD-005；构造结果再由 CAD-006 写入 accepted IR 的 `validation_result`。

## 本轮反例结果

以下反例由临时 Python 检查脚本构造，不写入生产代码或仓库测试：

| 反例 | 预期结果 |
|---|---|
| accepted 同时添加顶层 `errors` | Draft 2020-12 拒绝（状态条件的 `not.required`）。 |
| rejected 同时添加 `validation_result` | Draft 2020-12 拒绝。 |
| 复制 `bore_d` 参数、节点 ID、输出 ID | Schema 对参数类型仍可通过时，语义检查分别返回 `IR_DUPLICATE_PARAMETER_ID`、`IR_DUPLICATE_NODE_ID`、`IR_DUPLICATE_OUTPUT_ID`。 |
| 删除 ordinal 1 或让依赖指向未来节点 | 语义检查返回 `IR_ORDINAL_NOT_CONTIGUOUS` 或 `IR_DEPENDENCY_NOT_PREVIOUS`。 |
| 公式改为 `eval` 或 `formula_id=python_eval` | Schema/语义检查返回 `IR_UNREGISTERED_FORMULA` 或 `IR_EXECUTION_STRING_FORBIDDEN`。 |
| `snapshot_status=reproducible` | Schema 拒绝；若未来 Schema 为兼容枚举，语义检查必须返回 `IR_SNAPSHOT_STATUS_UNSUPPORTED`。 |

这些检查不证明 CadQuery/OCP 结果有效，也不证明 STEP 字节哈希稳定；它们只保证 IR 输入图可安全、确定地交给白名单编译器。
