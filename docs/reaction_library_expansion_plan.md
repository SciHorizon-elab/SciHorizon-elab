# 化学反应库扩充计划说明书

> 关联:[release_alignment_checklist.md](release_alignment_checklist.md) 第 3 条
> 状态:✅ 方案已确定,本文为可执行细化
> 目标分支:`upload`(遵循清单 #2 约定:每个问题独立成提交)
> 涉及文件:`scihorizon_elab/simulation/entities/specific_entities/solute_reaction.py`

---

## 1. 背景与问题

rebuttal 中声称系统包含 "hundreds of encoded reactions",但仓库现状:

| 数据结构 | 现状 | 目标 |
|---|---|---|
| `REACTIONS` | **5 条**(Cu(OH)₂ / Fe(OH)₃ / AgCl / BaSO₄×2) | **≥ 100 条** |
| `SOLUTE2RGBA` | 22 条(6 有色溶质 + 11 无色 + 5 产物) | 覆盖全部新反应的反应物与产物,约 80 条 |

问题本质是**论文口径与代码事实不符**,属发布对齐问题,不是功能缺陷。

## 2. 现状盘点与兼容性约束

### 2.1 模块结构([solute_reaction.py](../scihorizon_elab/simulation/entities/specific_entities/solute_reaction.py))

- `SOLUTE2RGBA`:物质名 → `[r,g,b,a]`,渲染颜色的**唯一权威来源**(优先级高于 LLM 推断色)
- `REACTIONS`:`frozenset({A, B}) → 产物名`,顺序无关
- `lookup_reaction(solutes_a, solutes_b)`:交叉乘积中**第一对命中**即反应;反应物移除、产物加入,返回单一产物名
- `resolve_color_from_solutes` / `alpha_over` / `mix_rgba` / `resolve_substance_name`:颜色合成与名字清洗

### 2.2 消费方(均不改)

| 调用方 | 位置 | 用途 |
|---|---|---|
| `DispenseCondition._transfer_solution` | [condition.py:341](../scihorizon_elab/simulation/conditions/condition.py#L341) | 移液时查反应、决定目标容器颜色 |
| `PourIntoCondition._transfer_solution` | [condition.py:1474](../scihorizon_elab/simulation/conditions/condition.py#L1474) | 倾倒时同上 |
| `LiquidDisplayMixin` | [mixins.py:114](../scihorizon_elab/simulation/entities/mixins.py#L114) | 初始化溶质、`set_solution_rgba` / `fill_solution` 颜色解析 |

### 2.3 硬性兼容约束

1. **API 零变更**:只扩 `REACTIONS` / `SOLUTE2RGBA` 两个数据结构,所有函数签名与语义不动 → `condition.py` / `mixins.py` / `skill_lib.py` 零改动。
2. **视觉回归零容忍**:现有 5 条反应、现有 22 条颜色值必须**逐位不变**(演示视频/评测日志依赖这些颜色,如 CuSO₄ 蓝 `[0, 0.45, 1, 0.4]`)。
3. **单产物语义保持**:值仍是一个产物名(可溶副产物从溶质列表消失,是既有简化,不在本次范围)。
4. **first-match-wins 保持**:扩表后一次混合可能命中多组反应,仍按现状"第一对命中",不改 `lookup_reaction`。
5. LLM 端(analyzer / skill_planner 提示词)只引用化学式作**示例**而非封闭词表,扩表无需同步提示词;表外物质名自然走 `mix_rgba` 兜底。

## 3. 目标与验收标准

- [ ] `REACTIONS` ≥ 100 条,全部为中学/大一教材口径的复分解、中和、沉淀反应,可逐条对答化学正确性
- [ ] `SOLUTE2RGBA` 覆盖所有新反应的反应物与产物(结构断言保证,无查表缺口)
- [ ] 原 5 条反应键值对、原 22 条颜色值不变(测试断言)
- [ ] 新增单元测试全绿;20 条经典反应人工抽查通过并留痕
- [ ] 生成脚本与审计清单入库(可复现、可核查)
- [ ] 独立提交推送 `upload`
- [ ] ⚠️ 仓库外:论文措辞 "hundreds of encoded reactions" → **"100+ encoded reactions"**(作者侧修改,本计划只提醒)

## 4. 化学设计规范(本计划的核心)

### 4.1 反应物全集(均可作初始溶质,全部入 `SOLUTE2RGBA`)

**酸(3)**:HCl、H₂SO₄、HNO₃ —— 无色 `[1,1,1,0.3]`

**碱(4)**:NaOH、KOH、Ba(OH)₂、Ca(OH)₂ —— 无色(石灰水澄清)

**可溶盐(按阳离子)**:

| 阳离子 | 盐 | 颜色 |
|---|---|---|
| Na⁺ / K⁺ / NH₄⁺ | NaCl, Na₂SO₄, Na₂CO₃, NaNO₃ / KCl, K₂SO₄, K₂CO₃, KNO₃ / NH₄Cl, (NH₄)₂SO₄, (NH₄)₂CO₃, NH₄NO₃ | 无色 |
| Ba²⁺ | BaCl₂, Ba(NO₃)₂ | 无色 |
| Ca²⁺ | CaCl₂, Ca(NO₃)₂ | 无色 |
| Mg²⁺ | MgCl₂, Mg(NO₃)₂, MgSO₄ | 无色 |
| Al³⁺ | AlCl₃, Al(NO₃)₃, Al₂(SO₄)₃ | 无色 |
| Zn²⁺ | ZnCl₂, Zn(NO₃)₂, ZnSO₄ | 无色 |
| Fe²⁺ | FeCl₂, Fe(NO₃)₂, FeSO₄ | **浅绿** `[0.72, 0.9, 0.72, 0.4]` |
| Fe³⁺ | FeCl₃(已有), Fe(NO₃)₃, Fe₂(SO₄)₃ | **黄棕** 同 FeCl₃ `[0.6475, 0.5686, 0.023, 0.4]` |
| Cu²⁺ | CuCl₂(已有,绿), Cu(NO₃)₂, CuSO₄(已有,蓝) | Cu(NO₃)₂ 蓝,同 CuSO₄ |
| Ag⁺ | AgNO₃(已有) | 无色 |
| Pb²⁺ | Pb(NO₃)₂(已有) | 无色 |

### 4.2 产物全集(新增入 `SOLUTE2RGBA`)

| 产物 | 颜色 | RGBA |
|---|---|---|
| AgCl, BaSO₄(已有), PbSO₄, CaSO₄, BaCO₃, CaCO₃, MgCO₃, ZnCO₃, PbCO₃, Mg(OH)₂, Al(OH)₃, Zn(OH)₂, Pb(OH)₂ | 白色沉淀 | `[1,1,1,0.7]` |
| Ag₂CO₃ | 淡黄沉淀 | `[0.95, 0.92, 0.72, 0.7]` |
| Fe(OH)₂ | 灰白→灰绿沉淀 | `[0.85, 0.90, 0.82, 0.5]` |
| Cu(OH)₂(已有), Fe(OH)₃(已有) | 蓝 / 红褐 | 不变 |
| 中和与酸+碳酸盐的可溶盐(NaCl, KNO₃ 等) | 可溶无色 | `[1,1,1,0.3]` |

颜色规范沿用现有约定:**可溶无色 α=0.3;白色沉淀 α=0.7;有色溶质 α=0.4;有色沉淀 α=0.5**。

### 4.3 反应类型与驱动力规则(生成脚本的判定逻辑)

复分解反应发生条件:生成物中有**沉淀**、**气体**或**水**。脚本按离子互换 + 溶解性表判定:

| 类型 | 规则 | 例 | 产物记录 |
|---|---|---|---|
| ① 氯化物沉淀 | 任意可溶 Cl⁻ 源 × AgNO₃ | HCl/NaCl/…/CuCl₂ + AgNO₃ → **AgCl**↓ | AgCl |
| ② 硫酸钡沉淀 | 任意可溶 SO₄²⁻ 源 × BaCl₂/Ba(NO₃)₂/Ba(OH)₂ | CuSO₄ + BaCl₂ → **BaSO₄**↓ | BaSO₄ |
| ③ 硫酸铅沉淀 | SO₄²⁻ 源 × Pb(NO₃)₂ | Pb(NO₃)₂ + Na₂SO₄ → **PbSO₄**↓ | PbSO₄ |
| ④ 硫酸钙(微溶) | CaCl₂/Ca(NO₃)₂ × Na₂SO₄/K₂SO₄/H₂SO₄ | CaCl₂ + Na₂SO₄ → **CaSO₄**↓(白浑) | CaSO₄ |
| ⑤ 碳酸盐沉淀 | Na₂CO₃/K₂CO₃/(NH₄)₂CO₃ × Ca/Ba/Mg/Zn/Pb 盐、AgNO₃ | Na₂CO₃ + BaCl₂ → **BaCO₃**↓ | 对应碳酸盐 |
| ⑥ 酸 + 碳酸盐(气体) | HCl/H₂SO₄/HNO₃ × 可溶碳酸盐 | Na₂CO₃ + 2HCl → 2NaCl + H₂O + **CO₂**↑ | 盐(CO₂ 逸出,溶液呈盐色) |
| ⑦ 中和(水) | 3 酸 × NaOH/KOH/Ba(OH)₂/Ca(OH)₂ | NaOH + HCl → NaCl + H₂O | 盐 |
| ⑧ 难溶氢氧化物 | NaOH/KOH/Ba(OH)₂/Ca(OH)₂ × Mg/Al/Zn/Fe²⁺/Fe³⁺/Cu/Pb 盐 | FeCl₃ + 3NaOH → **Fe(OH)₃**↓ + 3NaCl | 对应氢氧化物 |
| ⑨ 铵盐 + 强碱(气体) | 4 种铵盐 × 4 种碱 | NH₄Cl + NaOH → NaCl + **NH₃**↑ + H₂O | 盐(NH₃ 逸出) |

### 4.4 化学排除清单(刻意不收,防止教材口径硬伤)

- **Ag₂SO₄、PbCl₂**:微溶程度介于两可,教材通常不判沉淀 → 不作为目标产物(PbCl₂ 也不作反应物)
- **CuCO₃、FeCO₃、Fe₂(CO₃)₃**:不稳定(实际得碱式盐/水解),教材回避 → 不收
- **可溶 × 可溶且无沉淀/气体/水**(如 NaCl + KNO₃):不反应 → 严禁入表(结构性校验兜底)
- 两酸之间、两碱之间:不反应
- AgNO₃ + NaOH:生成 AgOH 立即分解为 Ag₂O(棕黑),教材口径复杂 → 不收
- 温度/浓度条件反应(如 KNO₃ + NH₄Cl 需蒸发结晶):不属复分解,不收

### 4.5 双沉淀择色规则(必要的裁决)

个别组合两个产物都不溶,如 `Ba(OH)₂ + CuSO₄ → Cu(OH)₂↓ + BaSO₄↓`。单产物 API 下裁决规则:**优先记录有色沉淀**(视觉显著性:蓝 > 白),两者皆白时按固定阳离子优先级取一个。裁决结果逐条写进审计清单,抽查时重点看这些行。

### 4.6 预计规模(脚本参数化,目标 100–130 条)

| 类型 | 理论条数 |
|---|---|
| ① AgCl | 12 |
| ② BaSO₄ | 30 |
| ③ PbSO₄ | 10 |
| ④ CaSO₄ | 6 |
| ⑤ 碳酸盐沉淀 | 42 |
| ⑥ 酸 + 碳酸盐 | 9 |
| ⑦ 中和 | 12 |
| ⑧ 氢氧化物沉淀 | 76 |
| ⑨ 铵盐 + 碱 | 16 |
| **合计** | **213 → 按教材经典度筛选至 100–130** |

筛选原则:⑧ 中 Fe²⁺/Zn²⁺/Pb²⁺ 与 KOH/Ba(OH)₂/Ca(OH)₂ 的冷门组合、⑤ 中 MgCO₃ 边缘条目优先裁减;① ② ⑤ ⑥ ⑦ 全收。**下限 100,即论文口径 "100+" 的直接依据**;脚本 `TARGET` 参数可调。

## 5. 实施步骤

| 步骤 | 内容 | 产物 |
|---|---|---|
| **S0 前置** | 在 `upload` 分支 `git merge master`,并入 6D 提交(清单 #2 既定动作) | 干净基线 |
| **S1 生成脚本** | 新建 `scripts/gen_reaction_table.py`:内置 §4 全部规则(物质全集、溶解性表、驱动力判定、排除清单、择色规则、颜色表);自校验(无自配对、无全溶无驱动力条目、产物/反应物颜色全覆盖、原 5 条保留)通过后才输出;输出确定性排序(diff 友好、可重复生成) | 脚本入库 |
| **S2 生成与替换** | 运行脚本,替换 `solute_reaction.py` 中 `REACTIONS` 与 `SOLUTE2RGBA` 两个块(标注 `# 自动生成区 BEGIN/END — 由 scripts/gen_reaction_table.py 生成,勿手改`);其余函数与文档字符串不动;现有条目被脚本原值吸收(回归由测试保证) | 扩充后的 `solute_reaction.py` |
| **S3 审计清单** | 脚本同时输出 `docs/reaction_table_audit.md`:全部反应按类型分组、配平方程式、产物颜色、双沉淀裁决标记 | 人工抽查底稿 |
| **S4 单元测试** | 新建 `scihorizon_elab/simulation/tests/test_solute_reaction.py`(沿用 `pipeline/tests/` 的包内测试惯例):① 结构断言 ≥100、颜色表全覆盖、frozenset 对称、无自配对;② 20 条经典反应逐条断言(§7);③ 原 5 条与原 22 色值回归;④ `resolve_color_from_solutes` / `resolve_substance_name` 行为回归 | pytest 全绿 |
| **S5 人工抽查** | 对照审计清单抽查 20 条(优先:双沉淀裁决行、微溶 CaSO₄/MgCO₃ 行、⑥⑨ 气体行、全部有色产物行),在 audit 文件勾选留痕 | 抽查记录 |
| **S6 提交** | 独立提交(建议信息:`reaction lib: expand REACTIONS to 100+ textbook reactions with synced SOLUTE2RGBA (checklist #3)`),推送 `upload`;更新清单 #3 状态为 ✨ 已修复 | 单一提交 |

## 6. 明确不做(范围外)

- 不改 `lookup_reaction` 多步/多产物支持,不改 `condition.py` / `mixins.py`
- 不加氧化还原、络合、温度驱动反应(超教材范围)
- 不动 pipeline 提示词与 skill 库
- 不在本次处理清单 #1、#2 的其余事项

## 7. 人工抽查 20 条候选(同时固化为测试用例)

AgCl 组:HCl+AgNO₃、CuCl₂+AgNO₃ · BaSO₄ 组:CuSO₄+BaCl₂(原条目)、H₂SO₄+Ba(OH)₂(双沉淀裁决,取 BaSO₄) · 碳酸盐:Na₂CO₃+CaCl₂、K₂CO₃+BaCl₂、(NH₄)₂CO₃+Pb(NO₃)₂、Na₂CO₃+AgNO₃(淡黄) · 酸+碳酸盐:Na₂CO₃+HCl、K₂CO₃+H₂SO₄ · 中和:NaOH+HCl、Ca(OH)₂+HNO₃ · 氢氧化物:FeCl₃+NaOH(原)、Cu(NO₃)₂+KOH、MgSO₄+NaOH、AlCl₃+NaOH、FeSO₄+NaOH(灰绿)、ZnSO₄+NaOH、Pb(NO₃)₂+NaOH · 铵盐:NH₄Cl+NaOH · 双沉淀:Ba(OH)₂+CuSO₄(取蓝色 Cu(OH)₂)

## 8. 风险与已知简化(发布说明中如实呈现)

| 风险/简化 | 处理 |
|---|---|
| 可溶副产物从溶质列表消失(单产物 API) | 既有行为,保持;文档注明"记录显著产物" |
| 双沉淀只显一色 | §4.5 择色规则 + 审计留痕 |
| Zn(OH)₂ 两性(过量 NaOH 溶解)、Fe(OH)₂ 易氧化 | 简化为即时沉淀、初生色;注释说明 |
| CaSO₄、MgCO₃ 微溶 | 按教材"白色浑浊"口径收,抽查确认 |
| first-match-wins:混合命中多组时只反应一对 | 既有行为;扩表后概率上升但语义不变 |
| 表外物质名(LLM 生成) | 现有 fallback 混合色机制天然兜底 |

## 9. 工作量估计

脚本 S1 0.5 天 · 生成与替换 S2–S3 0.25 天 · 测试 S4 0.25 天 · 抽查与文档 S5 0.25 天 → **合计约 1–1.5 人日**。
