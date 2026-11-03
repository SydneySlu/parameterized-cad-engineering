# RET-003 C1 诊断环境不匹配报告

状态：`blocked`
日期：2026-11-03
阶段：M0 环境与接口确认

## 环境门检查结果

### 协议要求的固定环境

根据 `agent-work/reviews/RET-003-codex-review.md` 和项目历史验证基线：

- Python: 3.11.18
- 操作系统: macOS arm64
- 关键依赖: CadQuery 2.3.0, OCP 7.9.3.0, NumPy 1.26.4

### 当前实际环境

```bash
$ python3 --version
Python 3.10.12

$ uname -sm
Linux aarch64
```

项目 venv 配置的 Python 3.11 路径：
```
work/benchcad-output/venv/bin/python -> /opt/homebrew/opt/python@3.11/bin/python3.11
```

该路径在当前 Linux 环境中不存在（macOS Homebrew 特定路径）。

### 环境不匹配项

| 项目 | 要求 | 实际 | 匹配 |
|---|---|---|---|
| Python 版本 | 3.11.18 | 3.10.12 | ❌ |
| 操作系统 | macOS | Linux | ❌ |
| CPU 架构 | arm64 | aarch64 | ✓ (等价) |

## M0 环境门决策

根据修正 Prompt 的 M0 阶段要求：

> 先记录实际 Python/OS/架构；环境不符即停止，不生成正式 JSON/报告。

**决定：停止执行，不生成正式结果**

### 原因

1. Python 版本差异（3.10.12 vs 3.11.18）可能导致：
   - 标准库行为差异
   - 第三方依赖兼容性问题
   - 数值计算精度变化
   - JSON 序列化顺序不同

2. 操作系统差异（Linux vs macOS）可能导致：
   - 文件系统路径分隔符差异
   - 浮点运算实现不同
   - 依赖库编译版本不同
   - CadQuery/OCP 几何计算结果偏差

3. RET-001/RET-002 的验证基线固定在 Python 3.11.18 / macOS arm64：
   - Manifest 几何测量来自该环境
   - RET-002 canonical SHA-256 在该环境生成
   - 环境变化可能导致距离/排序结果不可比较

## 阻塞项

**当前环境无法满足 RET-003 C1 正式结果生成的环境要求。**

需要：
- 访问配置了 Python 3.11.18 的 macOS arm64 环境
- 该环境已安装项目依赖（CadQuery 2.3.0, OCP 7.9.3.0, NumPy 1.26.4）
- 或项目负责人确认可在当前环境执行并接受结果差异风险

## 可选路径

### 选项 A：等待正确环境

保持 `blocked` 状态，等待在 macOS arm64 + Python 3.11.18 环境中重新执行。

### 选项 B：降级为探索性诊断

如果项目负责人接受环境差异风险，可以：
1. 在 JSON/报告中明确标注 `environment_status: "non_baseline_exploratory"`
2. 所有结果标记为"非正式、仅供参考"
3. 不能用于任何项目结论或与 RET-002 基线的正式比较
4. 仍需在正确环境重新生成正式结果

### 选项 C：环境重定义

如果项目决策层正式修订环境基线为 Python 3.10.12 / Linux aarch64，需要：
1. 重新运行 RET-001 完整验证（660 项）
2. 重新运行 RET-002 所有测试和 smoke
3. 重新生成 RET-002 canonical SHA-256 基线
4. 在 `docs/DECISIONS.md` 记录环境变更决策
5. 经 Codex 中枢审查批准后，才能作为新的固定基线

## 下一步

CC Agent 在 M0 阶段停止，记录环境不匹配，更新 checkpoint/handoff 标记 `blocked`，交 Codex 中枢决策。

不执行后续 M1-M5 阶段；不修改脚本、不生成 JSON/报告、不提交。
