# 模型资产 XML 标准化规范（v1）

**日期**: 2026-08-21
**状态**: 已发布，供资产 PR review 与历史资产补齐使用

---

## Context

SciHorizon-ELAB 的仿真由两大类系统协同决定：
- **Python 侧**：entity 类（继承 `Entity`）通过**混入 (mixin)** 表达能力，运行时按特定名称查询 MJCF 元素；
- **XML 侧**：模型资产的 MJCF 文件按约定放置 site/geom/body/joint 元素。

两边约定不一致（例如 `GraspMixin` 找 `group=4` 的 site，而 `LiquidTransferMixin` 找名为 `aspirate_site` 的 site）会让某些 XML 在仿真时静默退化成"用 entity 中心点代替"，更严重的会在 `scihorizon_elab/simulation/entities/specific_entities/chemistry_container.py:32` 抛出 `ValueError`。

本规范的目标是：**让每个 mixin 在加载时就能找到它需要的 XML 元素，且这些元素的语义、命名、数值范围都受一份明确的文档约束**，方便后续资产补充和 PR review。

本规范**只写文档**，不引入运行时校验脚本。运行时已有的失败检查（如 `chemistry_container.py`）保留不动。

> **命名规范与代码同步现状**：本规范在文档层面提出新命名约定（`hinge` / `slide` / `boundpoint`），但**不修改 Python 代码**中的现有查找逻辑（`scihorizon_elab/simulation/entities/mixins.py:300` 的 `_hinge_joint_name="door"`、`scihorizon_elab/simulation/entities/mixins.py:386` 的 `"drawer" in body.name` 仍保留）。新命名作为"长期推荐"存在，资产层可在不破坏现有代码的前提下逐步迁移。

---

## 1. 全局通用要求（适用于所有模型 XML）

### 1.1 `<mujoco>` 根属性
- 必须有 `model="<实体名>"`（例：`alcohol_lamp`、`large_beaker`），与 `@register.add_entity` 注册的字符串一致。
- 推荐 `compiler angle="radian"`，避免度数/弧度混淆。

### 1.2 bbox 注释（**运行时被消费**）

XML 第二行（紧接 `<?xml ?>` 之后）必须有：

```xml
<!-- @bbox dx=<米> dy=<米> dz=<米> -->
```

三个值的含义：

- `dx` —— 物体在 X 方向占地宽度（米），用于 [entity_loader.py](../scihorizon_elab/pipeline/nodes/code_gen_skills/entity_loader.py) 第 206 行 `_read_bbox_from_xml_comment` 读取，驱动桌面布局算法（CP-SAT / MaxRects）。
- `dy` —— 物体在 Y 方向占地深度（米），同上。
- `dz` —— 物体在 Z 方向高度（米），用于 [skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 3822 行 `_get_grasped_bbox_dz`，驱动 `insert_to_entity` / `aspirate` 的悬停高度计算。

取值范围：[entity_loader.py](../scihorizon_elab/pipeline/nodes/code_gen_skills/entity_loader.py) 第 224-225 行校验为 `[0.01, 0.50]` m；大件（drying_box）超出上限仍可被消费。

### 1.3 site group 与 class 的项目语义

> **关于 `group=1`**：这是 MuJoCo 的**视觉/物理默认分组**。项目中的 `place_sites` / `key_sites` / `grasp_sites`（[entity.py](../scihorizon_elab/simulation/entities/entity.py) 第 113-144 行）只查 `group==2/3/4`，从不查 `group=1`。**业务语义由 group 2/3/4 承载**；geom 的 `class="visual"` 会设 geom `group="2"`，但这是 geom 视觉组，不影响 site 的语义 group，两套体系不冲突。

| class          | site group | 默认 rgba     | 运行时用途                                                                                |
| -------------- | ---------- | ------------- | ----------------------------------------------------------------------------------------- |
| `boundpoint`   | `3`        | `1 0 0 1`     | `key_sites()`：通用安全边界 / contain AABB（8 个角点覆盖物体最小包围盒）。见 §1.4。         |
| `placepoint`   | `2`        | `0 0 1 0`     | `place_sites()`：放置/插入/搅拌目标点                                                       |
| `grasppoint`   | `4`        | `0 0 1 1`     | `grasp_sites()`：抓取点                                                                     |

> 即便不使用 site group 机制，**实际访问也是按 group 进行**（参考 [entity.py](../scihorizon_elab/simulation/entities/entity.py) 第 113-144 行），所以 site 必须**同时具备正确的 group 与 class**。
>
> **强制要求**：site 标签上必须**显式**写 `group="N"`（N=2/3/4），不依赖 `<default class="X">` 的隐式继承。原因：MJCF 的 default class 继承在嵌套多 default（多个同名 default 块）下行为不一致；显式 group 保证运行时 `place_sites()` / `key_sites()` / `grasp_sites()` 一定能查到。

### 1.4 通用 bound：8 个 boundpoint（**所有模型必填**）

**所有模型资产**必须在 `<worldbody>` 中定义 **8 个 `<site class="boundpoint" group="3">`**，构成物体的最小轴对齐包围盒 (AABB)：

- 4 个底部角点：`bnd_p0` / `bnd_px` / `bnd_py` / `bnd_pxy`，z 相同（物体底部高度）；
- 4 个顶部角点：`bnd_pz` / `bnd_pxz` / `bnd_pyz` / `bnd_pxyz`，z 相同（物体顶部高度）；
- 8 个点要构成真实包围盒（用长=dx、宽=dy 的矩形框住模型），而非物体几何的精确轮廓；
- 命名建议（与 §1.2 的 `dx` / `dy` / `dz` 对齐）：
  - `bnd_p0 = (xmin, ymin, zmin)`
  - `bnd_pxyz = (xmax, ymax, zmax)`
  - `bnd_px / bnd_py / bnd_pxy` 位于底面，`bnd_pz / bnd_pxz / bnd_pyz` 位于顶面。

**消费方**：

- [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 65 行 `ContainerMixin.contain` 用这些点算 min/max AABB；
- [entity.py](../scihorizon_elab/simulation/entities/entity.py) 第 124 行 `key_sites()` 把它们作为安全边界；
- 布局算法的 collision buffer 也将消费这些点。

> **历史命名**：之前某些 XML（如 `large_beaker.xml`、`drying_box.xml`）使用 `keypoint` class 表达类似语义。新资产请直接使用 `boundpoint`，历史资产可在下次刷新时一并迁移。

### 1.5 visual / collision 默认 class

`<default class="visual">`：

```xml
<geom group="2" type="mesh" contype="0" conaffinity="0" density="50"/>
```

避免被 collision 接触计算命中。

`<default class="collision">`：

```xml
<geom group="3" type="mesh" density="50" friction="1.5 0.1 0.1" solimp="0.9 0.95 0.001" solref="0.02 1"/>
```

与 robot 默认接触参数一致。

---

## 2. 按 mixin 的必需元素清单

下表是 **"类包含某 mixin ⇒ XML 必须满足"** 的强制映射。"默认 class" 已在 §1.3 给出。

| Mixin                    | Python 引用点                                                                                                                                                  | XML 必需元素                                                                                                                                                                                                                                                                                | 命名约定                                                                                                                                                              |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **GraspMixin**           | [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 21 行 `is_grasped` / `get_grasped_keypoints`                                                                                | **有且仅有 1 个** `<site group="4" class="grasppoint">`，位于物体**中部**（推荐 z ≈ 物体总高度的一半）                                                                                                                                                                                       | 推荐 `<site class="grasppoint" name="grasppoint"/>`                                                                                                                  |
| **ContainerMixin**       | [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 49 行 `get_place_points` / `contain`                                                                                                  | 至少 1 个 `<site group="2" class="placepoint">`                                                                                                                                                                                                                                              | `name="placepoint"` 或 `place_c`                                                                                                                                       |
| **SurfaceMixin**         | [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 80 行 `contain` / `get_place_points`                                                                                                   | 至少 1 个 `<site group="2" class="placepoint">`（用于"被放置"语义；如缺失 `get_place_points` 会用 entity 中心兜底）                                                                                                                                                                            | `name="placepoint"`                                                                                                                                                   |
| **LiquidDisplayMixin**   | [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) ��� 117 行 `set_solution_rgba` / `fill_solution`                                                                                            | 必须有 `<geom name="solution" type="cylinder">`（默认 type=cylinder, size=[radius, halfheight]），且 `pos.z + size[1]` 即液面（[skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 4200-4205 行 `aspirate()` 消费）                                                                                                                                  | `name="solution"` 固定。推荐 `material` 设为透明（rgba a=0），运行时按 solute 重新染色                                                                                |
| **LiquidTransferMixin**  | [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 232 行 `get_aspirate_site`                                                                                                            | 必须有 `<site name="aspirate_site">`（滴管针尖）。若缺失则 fallback 到 `<site name="bottom_site">`，仍缺失则 [skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 4215 行报错                                                                                                              | `name="aspirate_site"` 是首选；`name="bottom_site"` 仅为兜底                                                                                                          |
| **HingeMixin**           | [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 294 行 `is_open` / `is_closed` / `get_open_trajectory`                                                                                    | 必须有 `<joint type="hinge">`，其 `name` 推荐包含 `"hinge"`（**长期推荐**，覆盖 laptop 屏、门、瓶盖等）；**当前代码向后兼容**仍按 `"door"` 查找（见 [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 300 行 `_hinge_joint_name="door"`），所以也可以用 `"door"`。至少 1 个 `<site group="4" class="grasppoint">` 作为把手 | 推荐 hinge joint：`name="*hinge*"`；grasp point：`name="door_handle_grasp"` / `screen_handle_grasp"` 等                                                                                |
| **SlideMixin**           | [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 371 行 `slide_rails`                                                                                                                                                            | 必须有可滑动 body：推荐 `<body>` 包含 `"slide"` 子串（**长期推荐**，覆盖抽屉、滑盖、滑板等）；**当前代码向后兼容**仍按 `"drawer"` 查找（见 [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 386 行）。每个滑动 body 内 `<joint type="slide">` + 至少 1 个 `<site group="4" class="grasppoint">` 作为把手 | 推荐 slide body：`name="slide_top"` / `slide_middle"` / `slide_bottom"`；slide joint：`name="*_slide"`                                                                       |
| **ButtonMixin**          | [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 440 行 `is_activate`                                                                                                                                                            | 必须有 `<geom name="start_button">` + 一个被识别为"按钮"的 material（name 含 `"button"`，或 `r>0.4 & g<0.2 & b<0.2`，参考 [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 472-493 行）                                                                                                | geom：`name="start_button"`；material：`name="button_vcol_mat"` 或 `button_*_mat`（[drying_box.py](../scihorizon_elab/simulation/entities/specific_entities/drying_box.py) 第 23 行即如此）                                                                |
| **FlameDisplayMixin**    | [alcohol_lamp.py](../scihorizon_elab/simulation/entities/specific_entities/alcohol_lamp.py) 第 23 行 `set_flame_state`                                                                                                                                       | 必须有至少 1 个 `<geom>`，其 `name` 含 `"flame"`。默认 rgba alpha=0（熄灭），调用 `set_flame_state(lit=True)` 时 alpha 变 1                                                                                                                                                                         | 火焰 geom：`name="flame_outer"` + `name="flame_inner"`（双层效果）；推荐 `class="visual"`                                                                                |

### 2.1 命名 site 的语义扩展

以下命名 site 被运行时通过 name 查找，不依赖 group。

| site name         | 消费方                                                                                                                                          | 含义                                                                                              | 是否必需                                                                                                |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `top_site`        | [skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 1808 行 `stir_entity_with_tool`（计算搅拌容器内高度）                                              | 物体**顶部中心**（容器上沿 / 工具顶端）                                                            | **可交互物体必填**（含 LiquidDisplayMixin / LiquidTransferMixin / SurfaceMixin / HingeMixin 的实体）       |
| `bottom_site`     | [skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 1809 行 `stir_entity_with_tool`；[mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 265 行 `get_aspirate_site` 兜底 | 物体**底部中心**（容器底 / 工具底 / 针尖位置）                                                       | 同上                                                                                                    |

> **关于 aspirate_site 的 group**：现有实现 [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 274-280 行仅按 `name` 查找 `aspirate_site`，不查 group；不需要也不建议设置 group。让它继续保持"专属 name"的语义，避免与 placepoint (group=2) 产生歧义。

---

## 3. 实体类 ↔ mixin 组合速查表

| 实体类 (Python class)      | 必含 mixin                                          | 额外 XML 必填项                                                                                  |
| -------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `Entity`（基类）            | —                                                   | `<!-- @bbox ... -->`；8 个 `boundpoint`（§1.4）                                                |
| `CommonGraspedEntity`      | GraspMixin                                          | grasppoint site                                                                                  |
| `Container`                | ContainerMixin                                      | placepoint                                                                                       |
| `ChemistryContainer`       | ContainerMixin + LiquidDisplayMixin + GraspMixin    | grasppoint + placepoint + solution geom                                                          |
| `ChemistryTube`            | (CommonGraspedEntity) + LiquidDisplayMixin          | grasppoint + solution geom + top_site + bottom_site                                              |
| `Laptop`                   | GraspMixin + HingeMixin                             | grasppoint + hinge joint + top_site + bottom_site                                                 |
| `Table`                    | SurfaceMixin                                        | placepoint + top_site + bottom_site                                                              |
| `FlatContainer`            | SurfaceMixin                                        | placepoint + top_site + bottom_site                                                              |
| `ContainerWithDoor`        | ContainerMixin + HingeMixin                         | placepoint + hinge joint + grasppoint (door handle) + top_site + bottom_site                    |
| `DryingBox`                | ContainerMixin + HingeMixin + ButtonMixin           | placepoint + hinge joint + grasppoint (door handle) + start_button geom + button mat + top_site + bottom_site |
| `ContainerWithDrawer`      | ContainerMixin + SlideMixin + GraspMixin            | placepoint + slide body + slide joint + grasppoint (per rail) + top_site + bottom_site           |
| `ContainerWithCap`         | ContainerMixin + HingeMixin + SlideMixin + GraspMixin| placepoint + hinge joint (cap) + slide joint (cap) + grasppoint (cap) + top_site + bottom_site   |
| `HeatDevice`               | SurfaceMixin + ButtonMixin                          | placepoint + start_button geom + button mat + top_site + bottom_site                             |
| `Pipette` / `Dropper`      | (CommonGraspedEntity) + LiquidTransferMixin         | grasppoint + aspirate_site + top_site + bottom_site                                              |
| `AlcoholLamp`              | (CommonGraspedEntity) + FlameDisplayMixin           | grasppoint + flame geom (flame_outer + flame_inner)                                              |
| `TubeStand` / `PipetteStand` | —                                                  | 仅基础视觉/碰撞几何；用作子实体父容器。需要 bbox + 8 个 boundpoint                                  |

> `mixins.py` 中的 ButtonMixin `_button_material_name` 在 `DryingBox` 覆写为 `"button_vcol_mat"`（[drying_box.py](../scihorizon_elab/simulation/entities/specific_entities/drying_box.py) 第 23 行），其它子类未覆写，依赖默认解析。
>
> **grasppoint 数量例外**：HingeMixin / SlideMixin 类可能有多个 grasppoint —— 例如 ContainerWithDrawer 每个 drawer body 内需要 1 个 grasppoint（共 N 个，对应 N 条滑轨）；ContainerWithDoor / ContainerWithCap 的"把手"上也需要 1 个 grasppoint。规则是：**单个可抓取部件配 1 个 grasppoint**，而非"整个 entity 只能 1 个"。

---

## 4. 当前缺口审计（截至规范发布日）

通过 `grep -L "@bbox"` 与各 XML 元素对比，发现以下缺口：

### 4.1 缺 `<!-- @bbox ... -->` 注释

- `scihorizon_elab/simulation/assets/obj/drawer/drawer.xml`（ContainerWithDrawer）
- `scihorizon_elab/simulation/assets/obj/table/table.xml`（Table）
- `scihorizon_elab/simulation/assets/obj/centrifuge/centrifuge.xml`（按命名推断）
- `scihorizon_elab/simulation/assets/obj/lab_equipment/petri_dish.xml`（按命名推断）

不补齐则运行时 layout 算法只能 fallback 到 `DEFAULT_BBOX=(0.10, 0.10)`。

### 4.2 缺 8 个 boundpoint / keypoint（按 §1.4 通用要求）

- `scihorizon_elab/simulation/assets/obj/drawer/drawer.xml`：每个 drawer body 内已有 2 个 keypoint（group=3），但**整个 cabinet 的 AABB 没有被 8 个角点完整覆盖**，且 `boundpoint` 命名缺失。
- `scihorizon_elab/simulation/assets/obj/table/table.xml`：**完全没有** keypoint/boundpoint，`SurfaceMixin.contain()` 会因 `key_sites()` 空导致 `np.array([]).min()` 抛 IndexError。**必须修复**。
- `scihorizon_elab/simulation/assets/obj/hot_plate/hot_plate/hot_plate.xml`：已有 4 个 `class="keypoint"`（仅 XY 平面，4 角），缺顶部 4 个点（AABB 不完整）。
- `scihorizon_elab/simulation/assets/obj/beaker_large/large_beaker/large_beaker.xml`：没有 keypoint/boundpoint（`ContainerMixin.contain()` 会因 key_sites 空退化为圆柱近似判定）。
- `scihorizon_elab/simulation/assets/obj/alcohol_lamp/alcohol_lamp.xml`：没有 keypoint/boundpoint。

> 完整审计需要在仓库根运行一遍带 mixin 反查的脚本（本规范只点明已知缺口，未做逐文件深审）。

### 4.3 缺 top_site / bottom_site（按 §2.1）

- `scihorizon_elab/simulation/assets/obj/table/table.xml`：仅有 `<site name="top_site">`（巧合命名但 group=2 而非 §2.1 默认），缺 `bottom_site`。
- `scihorizon_elab/simulation/assets/obj/drawer/drawer.xml`：每个 drawer body 内已有 `top_site` / `bottom_site`，但 cabinet 整体缺。
- 多数容器缺 `top_site` / `bottom_site`：`alcohol_lamp` / `large_beaker` / `drying_box` / `hot_plate` / `cylinder_*` / `flask` / `funnel` / `petri_dish` 等。

---

## 5. 工作流（开发者添加新资产时遵循）

1. **确认类归属**：选 mixin 组合 → 查 §3 得到必填项；
2. **建模导出**：从 `.obj` / `.glb` → 生成 visual mesh + collision mesh；
3. **写 XML**：
   - 文件首 `<?xml ?>` 后紧跟 `<!-- @bbox dx=... dy=... dz=... -->`；
   - 在 `<default>` 内包含 visual / collision / boundpoint / placepoint / grasppoint 四类（用 §1.3 的格式）；
   - 添加 §1.4 规定的 **8 个 boundpoint**；
   - 按 §3 给该类列出的"额外必填项"逐一添加 site / geom / joint；
   - 如含 LiquidDisplayMixin / LiquidTransferMixin / SurfaceMixin / HingeMixin，按 §2.1 添加 `top_site` + `bottom_site`；
4. **本地自检 grep 命令清单**：
   - `grep "@bbox" <your>.xml` 存在；
   - `grep 'class="boundpoint"' | wc -l` ≥ 8；
   - `grep -cE '^      <site class="grasppoint"' <your>.xml` **== 1**（若 GraspMixin，有且仅有 1 个 site 级 grasppoint）；
   - `grep 'class="placepoint"' | wc -l` ≥ 1（若 ContainerMixin / SurfaceMixin）；
   - `grep 'name="solution"'` ≥ 1（若 LiquidDisplayMixin）；
   - `grep 'name="aspirate_site"'` ≥ 1（若 LiquidTransferMixin；缺则 fallback 到 `bottom_site`）；
   - `grep 'name="top_site"'` 与 `grep 'name="bottom_site"'` 各 ≥ 1（若含可交互 mixin）；
   - `grep 'type="hinge"'` ≥ 1（若 HingeMixin；name 推荐含 `"hinge"`）；
   - `grep 'type="slide"'` ≥ 1（若 SlideMixin；body name 推荐含 `"slide"`）；
   - `grep 'name="start_button"'` ≥ 1（若 ButtonMixin）；
   - `grep 'name="flame_"'` ≥ 1（若 FlameDisplayMixin）。
5. **提交**：在 PR 描述中列出该资产包含的 mixin 与 XML 满足项，便于 reviewer 反向核对。

---

## 6. 运行时消费路径一览（便于确认"为什么必填"）

- `<!-- @bbox dx dy dz -->` →
  - [entity_loader.py](../scihorizon_elab/pipeline/nodes/code_gen_skills/entity_loader.py) 第 206 行读 `dx` / `dy` 用于桌面布局
  - [skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 3822 行 `_get_grasped_bbox_dz` 读 `dz` 用于 `insert_to_entity` / `aspirate`
- `site group=3 (boundpoint / keypoint)` → [entity.py](../scihorizon_elab/simulation/entities/entity.py) 第 124 行 `key_sites` → [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 65 行 `ContainerMixin.contain` 计算 AABB；未来用作通用安全边界
- `site group=2 (placepoint)` → [entity.py](../scihorizon_elab/simulation/entities/entity.py) 第 113 行 `place_sites` → [chemistry_container.py](../scihorizon_elab/simulation/entities/specific_entities/chemistry_container.py) 第 32 行 `get_place_point` 缺则 raise
- `site group=4 (grasppoint)` → [entity.py](../scihorizon_elab/simulation/entities/entity.py) 第 135 行 `grasp_sites` → [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 21 行 `GraspMixin.is_grasped` / `get_grasped_keypoints`
- `site name="top_site" / name="bottom_site"` → [skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 1808-1810 行 `stir_entity_with_tool` 计算容器内高度；`bottom_site` 还用作 `LiquidTransferMixin.get_aspirate_site` 兜底
- `geom name="solution"` → [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 149 行 `LiquidDisplayMixin.set_solution_rgba`；[skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 4200 行 `aspirate()` 计算液面
- `site name="aspirate_site"` → [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 265 行 `get_aspirate_site` → [skill_lib.py](../scihorizon_elab/utils/skill_lib.py) 第 4215 行
- `joint type="hinge" name="*door*"` → [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 300 行 `HingeMixin._hinge_joint_name`（建议新资产用 `"*hinge*"` 但代码暂不要求）
- `body name="*drawer*"` → [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 386 行 `SlideMixin._build` 自动收集 `slide_rails`（建议新资产用 `"*slide*"` 但代码暂不要求）
- `geom name="start_button"` → [mixins.py](../scihorizon_elab/simulation/entities/mixins.py) 第 454 行 `ButtonMixin.start_button`
- `geom name="flame_*"` → [alcohol_lamp.py](../scihorizon_elab/simulation/entities/specific_entities/alcohol_lamp.py) 第 33-34 行 `set_flame_state`

---

## 7. 关键参考文件

- [scihorizon_elab/simulation/entities/entity.py](../scihorizon_elab/simulation/entities/entity.py) — `Entity` 基类与 `place_sites` / `key_sites` / `grasp_sites`
- [scihorizon_elab/simulation/entities/mixins.py](../scihorizon_elab/simulation/entities/mixins.py) — 8 个 mixin 的完整实现
- [scihorizon_elab/simulation/entities/specific_entities/](../scihorizon_elab/simulation/entities/specific_entities/) — 各具体实体类
- [scihorizon_elab/utils/skill_lib.py](../scihorizon_elab/utils/skill_lib.py) — 仿真 skill，运行时消费 site/geom
- [scihorizon_elab/pipeline/nodes/code_gen_skills/entity_loader.py](../scihorizon_elab/pipeline/nodes/code_gen_skills/entity_loader.py) — 桌面布局���法，运行时消费 bbox
- [scihorizon_elab/simulation/assets/obj/](../scihorizon_elab/simulation/assets/obj/) — 全部模型资产

---

## 8. 不在本规范范围内

- **运行时校验脚本**：只写文档，不引入；
- **新增资产端到端工作流（从 glb 导出的全流程）**：未要求；
- **CI 集成**：未要求；
- **历史 40 个 XML 的完整审计报告**：本规范仅列出已知明显缺口（§4），未做逐文件深审；
- **代码侧 `mixins.py` 的命名迁移**（`_hinge_joint_name` 从 `"door"` 改 `"hinge"`、SlideMixin 从 `"drawer"` 改 `"slide"`）：本次仅在文档层面提出推荐，不改 Python 代码。
