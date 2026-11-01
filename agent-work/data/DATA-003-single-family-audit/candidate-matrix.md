# DATA-003 候选族比较（审计材料/草案）

固定 commit：`035f467142888edfd0bd7cd73906f9b155c8f43c`。本表只比较候选，不替中枢冻结首族、第二族或回退族。

| 族 | 存在/注册 | 原生入口与 smoke 结果 | 参数结构 | 主要风险 | 当前建议角色 |
|---|---|---|---|---|---|
| `set_screw_shaft_collar` | 存在；目录和 family_id 一致；状态 `MERGED` | `build()` + `check()`；官方 validate PASS（3 difficulties × 1 seed）；合法/边界 STEP 导出和回读成功 | 15 个目录行；5 个连续/派生字段 + `second_screw` 特征；单位/耦合易解释 | 源码自述 M3–M8 tapped-hole 环形近似可能出现“构造成功但螺纹布尔不移除体积”；非法输入若忽略 check 仍可能构造 | 候选首族（未冻结）；最小纵向切片最清晰 |
| `slotted_din_rail` | 存在；目录名 `slotted_din_rail` 与 family_id `slotted_din_rail_th35_7_5` 不一致；状态 `MERGED` | 官方 validate PASS（3 × 1）；构造入口可执行 | 完整目录行选择器 + 9 个由行派生字段；slot_count/pitch/length 强耦合 | ID 不一致；`side_relief` 是比例特征；长 600 mm 几何虽通过最小验证，仍需 STEP/尺寸抽查 | 第二族候选；结构上与 collar 差异明显 |
| `speaker_pole_mount_socket` | 存在；目录和 family_id 一致；状态 `MERGED` | 官方 validate PASS（3 × 1）；构造入口可执行 | 供应商尺寸 choices + cup_outer_d 派生 + proportion bottom_radius | `standard: null`；部分来源是供应商/比例规则；第三方图纸许可需单独核验 | 回退/第二候选；适合检验 proportion 和固定孔阵列 |

## 选择门

- 不能把 `MERGED` 写成 `RELEASED` 或 release-qualified；当前 STATUS 明确是 0 release-qualified。
- 不能把目录名与 `family_id` 自动视为同一字段；`slotted_din_rail` 必须在草案 manifest 中同时保存 `directory_name` 和 `family_id`。
- 生成的 STEP/渲染资产只作为本地验证产物，许可证范围暂记 `license_scope_uncertain`。
