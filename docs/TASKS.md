# SciVLABench task distribution

> Per-family task plan. Counts come from the per-family planning sheets under [`docs/`](docs/) (see file column). Subfamily-level task structure counts (`count`) exclude buffer tasks; HIL column counts human-agent-coordination tasks within the subfamily.

> The current implementation in this repository is a subset of the planned coverage above. Each entry below links to the planning sheet for full task names and natural-language instructions.

## Overview

| Operation family | Subfamilies | Tasks | HIL tasks | Planning sheet |
| --- | ---: | ---: | ---: | --- |
| Liquid Handling and Transfer (液体处理与转移) | 11 | 74 | 8 | [docs/任务表格LiquidHandling.xlsx](docs/任务表格LiquidHandling.xlsx) |
| Mixing and Agitation (混合与振荡) | 5 | 56 | 8 | [docs/任务表格MixingAgitation.xlsx](docs/任务表格MixingAgitation.xlsx) |
| Solid Handling and Weighing (固体处理与称量) | 2 | 56 | 0 | [docs/任务表格SolidHandling.xlsx](docs/任务表格SolidHandling.xlsx) |
| Thermal Control and Incubation (热控制与孵育) | 5 | 55 | 33 | [docs/任务表格.ThermalControl.xlsx](docs/任务表格.ThermalControl.xlsx) |
| Apparatus and Workspace Interaction (装置与工作区交互) | 6 | 64 | 0 | [docs/任务表格WorkspaceInteraction.xlsx](docs/任务表格WorkspaceInteraction.xlsx) |
| **Total** | **29** | **305** | **49** | |

## Liquid Handling and Transfer (液体处理与转移) — Liquid Handling and Transfer

- Planning sheet: [`docs/任务表格LiquidHandling.xlsx`](docs/任务表格LiquidHandling.xlsx)
- Subfamilies: **11**
- Tasks (planned, including buffer): **74**
- After removing buffer tasks: **74**
- Human-agent coordination tasks: **8**

| Subfamily | Tasks | Buffer | HIL |
| --- | ---: | ---: | ---: |
| 单次直接倾倒 / Single-stage Pouring | 8 | 0 | 0 |
| 移液枪转移 / Mechanical Pipette Transfer | 6 | 0 | 0 |
| 移液管转移 / Pipette Transfer | 6 | 0 | 0 |
| 两次接力倾倒 / Two-pour Relay | 4 | 0 | 0 |
| 三次接力倾倒 / Three-pour Relay | 6 | 0 | 0 |
| 双源汇聚倾倒 / Convergent Pouring | 6 | 0 | 0 |
| 倾倒与工具接力 / Pour–Tool Relay | 10 | 0 | 0 |
| 储液池多目标分装 / Reservoir Multi-target Distribution | 8 | 0 | 0 |
| 多来源有序添加 / Ordered Multi-source Addition | 8 | 0 | 0 |
| 人工触发流程 / Human-triggered Procedures | 8 | 0 | 8 |
| 并行样本处理 / Parallel Sample Handling | 4 | 0 | 0 |

**Tasks in this subfamily:**

### 单次直接倾倒 / Single-stage Pouring

- `pour_small_beaker_into_flask`
- `pour_small_beaker_into_medium_cylinder`
- `pour_flask_into_small_beaker`
- `pour_flask_into_medium_cylinder`
- `pour_medium_cylinder_into_small_beaker`
- `pour_tube_into_small_beaker`
- `pour_small_beaker_into_tube`

### 移液枪转移 / Mechanical Pipette Transfer

- `mechanical_pipette_large_beaker_to_tube_twice`
- `mechanical_pipette_small_beaker_to_flask_once`
- `mechanical_pipette_large_beaker_to_flask_twice`
- `mechanical_pipette_small_beaker_to_petridish_once`
- `mechanical_pipette_large_beaker_to_petridish_twice`

### 移液管转移 / Pipette Transfer

- `pipette_large_beaker_to_tube_twice`
- `pipette_small_beaker_to_flask_once`
- `pipette_large_beaker_to_flask_twice`
- `pipette_small_beaker_to_petridish_once`
- `pipette_large_beaker_to_petridish_twice`

### 两次接力倾倒 / Two-pour Relay

- `relay_small_beaker_via_medium_cylinder_to_flask`
- `relay_flask_via_small_beaker_to_tube`
- `relay_tube_via_small_beaker_to_medium_cylinder`

### 三次接力倾倒 / Three-pour Relay

- `three_stage_tube_via_small_beaker_and_flask_to_medium_cylinder`
- `three_stage_flask_via_small_beaker_and_medium_cylinder_to_tube`
- `three_stage_medium_cylinder_via_flask_and_tube_to_petridish`
- `three_stage_tube_via_medium_cylinder_and_small_beaker_to_petridish`
- `three_stage_small_beaker_via_tube_and_flask_to_medium_cylinder`

### 双源汇聚倾倒 / Convergent Pouring

- `ordered_converge_two_tubes_into_small_beaker`
- `ordered_converge_medium_cylinder_and_tube_into_flask`
- `ordered_converge_small_beaker_and_medium_cylinder_into_petridish`
- `ordered_converge_two_flasks_into_medium_cylinder`
- `ordered_converge_small_beaker_and_tube_into_flask`

### 倾倒与工具接力 / Pour–Tool Relay

- `pour_tube_into_large_beaker_mechanical_pipette_large_beaker_to_flask`
- `pour_medium_cylinder_into_small_beaker_mechanical_pipette_small_beaker_to_tube`
- `pour_tube_into_large_beaker_pipette_large_beaker_to_medium_cylinder`
- `pour_flask_into_small_beaker_pipette_small_beaker_to_tube`
- `mechanical_pipette_large_beaker_to_flask_pour_flask_into_tube`
- `pour_flask_into_small_beaker_pipette_small_beaker_to_petridish`
- `pour_medium_cylinder_into_large_beaker_mechanical_pipette_large_beaker_to_petridish`
- `pipette_small_beaker_to_flask_pour_flask_into_medium_cylinder`
- `mechanical_pipette_large_beaker_to_medium_cylinder_pour_medium_cylinder_into_tube`

### 储液池多目标分装 / Reservoir Multi-target Distribution

- `pour_small_beaker_into_large_beaker_mechanical_pipette_large_beaker_to_tube_and_cylinder`
- `pour_cylinder_into_large_beaker_mechanical_pipette_large_beaker_to_two_tubes_and_flask`
- `pour_tube_into_large_beaker_mechanical_pipette_large_beaker_to_flask_cylinder_and_tube`
- `pour_flask_into_small_beaker_pipette_small_beaker_to_two_tubes`
- `pour_small_beaker_into_large_beaker_pipette_large_beaker_to_tube_and_cylinder`
- `pour_cylinder_into_large_beaker_pipette_large_beaker_to_two_tubes_and_flask`
- `pour_tube_into_large_beaker_pipette_large_beaker_to_flask_cylinder_and_tube`

### 多来源有序添加 / Ordered Multi-source Addition

- `ordered_addition_two_stage_mechanical_pipette_small_beaker_then_large_beaker_into_flask`
- `ordered_addition_two_stage_flask_then_pipette_small_beaker_into_large_beaker`
- `ordered_addition_two_stage_pipette_small_beaker_then_flask_into_large_beaker`
- `ordered_addition_three_stage_cylinder_then_mechanical_pipette_small_beaker_then_pipette_large_beaker_into_flask`
- `ordered_addition_three_stage_mechanical_pipette_small_beaker_then_flask_then_pipette_large_beaker_into_cylinder`
- `ordered_addition_three_stage_small_beaker_then_flask_then_mechanical_pipette_large_beaker_into_cylinder`
- `ordered_addition_three_stage_pipette_small_beaker_then_flask_then_mechanical_pipette_another_small_beaker_into_large_beaker`

### 人工触发流程 / Human-triggered Procedures

- `wait_then_mechanical_pipette_large_beaker_to_tube`
- `wait_then_pipette_small_beaker_to_flask`
- `pour_small_beaker_to_flask_wait_then_mechanical_pipette_large_beaker_to_same_flask`
- `pipette_small_beaker_to_flask_wait_then_pour_another_small_beaker_into_same_flask`
- `two_human_additions_small_beaker_and_large_beaker_to_flask`
- `build_large_beaker_reservoir_wait_then_pipette_to_two_tubes`
- `pour_flask_to_large_beaker_wait_then_mechanical_pipette_to_tube`

### 并行样本处理 / Parallel Sample Handling

- `parallel_mechanical_pipette_small_beaker_to_tube_then_pour_flask_to_medium_cylinder`
- `parallel_pour_flask_to_small_beaker_then_tube_to_medium_cylinder`
- `parallel_pipette_small_beaker_to_flask_then_mechanical_pipette_large_beaker_to_tube`

## Mixing and Agitation (混合与振荡) — Mixing and Agitation

- Planning sheet: [`docs/任务表格MixingAgitation.xlsx`](docs/任务表格MixingAgitation.xlsx)
- Subfamilies: **5**
- Tasks (planned, including buffer): **56**
- After removing buffer tasks: **56**
- Human-agent coordination tasks: **8**

| Subfamily | Tasks | Buffer | HIL |
| --- | ---: | ---: | ---: |
| 直接搅拌 / Direct Stirring | 8 | 0 | 0 |
| 振荡混合 / Shaking and Agitation | 12 | 0 | 0 |
| 倾倒混合 / Repeated-Pouring Mixing | 12 | 0 | 0 |
| 有序加液后混合 / Ordered Addition Followed by Mixing | 16 | 0 | 0 |
| 人工触发流程 / Human-Triggered Mixing Procedures | 8 | 0 | 8 |

**Tasks in this subfamily:**

### 直接搅拌 / Direct Stirring

- `stir_small_beaker_with_glass_rod`
- `stir_large_beaker_with_glass_rod`
- `stir_small_beaker_then_large_beaker`
- `stir_large_beaker_then_small_beaker`
- `stir_two_small_beakers_in_order`
- `stir_two_small_beakers_then_large_beaker`
- `stir_large_beaker_then_two_small_beakers`
- `stir_small_beaker_large_beaker_another_small_beaker`

### 振荡混合 / Shaking and Agitation

- `shake_flask`
- `shake_two_flasks_in_order`
- `shake_three_flasks_in_order`
- `retrieve_shake_and_return_tube`
- `retrieve_shake_two_tubes_in_order`
- `retrieve_shake_three_tubes_in_order`
- `shake_flask_then_tube`
- `shake_tube_then_flask`
- `shake_two_flasks_then_tube`
- `shake_tube_then_two_flasks`
- `shake_two_tubes_then_flask`
- `shake_flask_then_two_tubes`

### 倾倒混合 / Repeated-Pouring Mixing

- `pour_mix_small_beaker_and_flask_roundtrip`
- `pour_mix_flask_and_small_beaker_roundtrip`
- `pour_mix_small_beaker_and_medium_cylinder_roundtrip`
- `pour_mix_medium_cylinder_and_small_beaker_roundtrip`
- `pour_mix_tube_and_small_beaker_roundtrip`
- `pour_mix_small_beaker_and_tube_roundtrip`
- `pour_mix_small_beaker_and_flask_three_pours`
- `pour_mix_flask_and_small_beaker_three_pours`
- `pour_mix_cycle_small_beaker_flask_medium_cylinder`
- `pour_mix_cycle_flask_small_beaker_tube`
- `pour_mix_cycle_medium_cylinder_flask_small_beaker`
- `pour_mix_cycle_tube_small_beaker_flask`

### 有序加液后混合 / Ordered Addition Followed by Mixing

- `pour_flask_to_small_beaker_then_stir`
- `pour_tube_to_large_beaker_then_stir`
- `pipette_small_beaker_to_another_small_beaker_then_stir`
- `mechanical_pipette_large_beaker_to_small_beaker_then_stir`
- `pour_flask_and_pipette_large_beaker_to_small_beaker_then_stir`
- `pipette_small_beaker_and_pour_tube_to_large_beaker_then_stir`
- `mechanical_pipette_small_beaker_and_pour_flask_to_another_small_beaker_then_stir`
- `three_source_addition_to_large_beaker_then_stir`
- `pour_small_beaker_to_flask_then_shake`
- `pour_small_beaker_to_tube_then_shake`
- `pipette_small_beaker_to_flask_then_shake`
- `mechanical_pipette_large_beaker_to_tube_then_shake`
- `pour_small_beaker_and_pipette_large_beaker_to_flask_then_shake`
- `pipette_small_beaker_and_pour_flask_to_another_flask_then_shake`
- `mechanical_pipette_small_beaker_and_pour_flask_to_tube_then_shake`
- `three_source_addition_to_flask_then_shake`

### 人工触发流程 / Human-Triggered Mixing Procedures

- `wait_then_stir_small_beaker`
- `wait_then_stir_large_beaker`
- `wait_then_pipette_small_beaker_to_flask_and_shake`
- `wait_then_mechanical_pipette_large_beaker_to_tube_and_shake`
- `pour_flask_to_small_beaker_wait_then_stir`
- `pour_small_beaker_to_flask_wait_then_pipette_large_beaker_and_shake`
- `stir_small_beaker_wait_then_mechanical_pipette_large_beaker_to_flask_and_shake`
- `two_human_additions_stir_small_beaker_then_shake_tube`

## Solid Handling and Weighing (固体处理与称量) — Solid Handling and Weighing

- Planning sheet: [`docs/任务表格SolidHandling.xlsx`](docs/任务表格SolidHandling.xlsx)
- Subfamilies: **2**
- Tasks (planned, including buffer): **56**
- After removing buffer tasks: **52**
- Human-agent coordination tasks: **0**

| Subfamily | Tasks | Buffer | HIL |
| --- | ---: | ---: | ---: |
| 电子秤称量 / Electronic-Scale Weighing | 28 | 1 | 2 |
| 天平称量 / Balance-Pan Weighing | 28 | 1 | 2 |

**Tasks in this subfamily:**

### 电子秤称量 / Electronic-Scale Weighing

- `place_small_beaker_on_electronic_scale`
- `place_flask_on_electronic_scale`
- `place_weight_on_electronic_scale`
- `place_mineral_aragonite_on_electronic_scale`
- `place_mineral_calcite_blue_on_electronic_scale`
- `place_mineral_fluorite_on_electronic_scale`
- `place_mineral_halite_on_electronic_scale`
- `place_mineral_galena_pbs_on_electronic_scale`
- `place_conical_flask_on_electronic_scale`
- `place_small_beaker_on_electronic_scale_then_retrieve`
- `place_flask_on_electronic_scale_then_retrieve`
- `place_weight_on_electronic_scale_then_retrieve`
- `place_mineral_fluorite_on_electronic_scale_then_retrieve`
- `reweigh_small_beaker_on_electronic_scale`
- `reweigh_mineral_galena_pbs_on_electronic_scale`
- `weigh_small_beaker_then_flask_on_electronic_scale`
- `weigh_flask_then_small_beaker_on_electronic_scale`
- `weigh_aragonite_then_calcite_on_electronic_scale`
- `weigh_fluorite_then_halite_on_electronic_scale`
- `weigh_halite_then_galena_on_electronic_scale`
- `weigh_small_beaker_then_aragonite_on_electronic_scale`
- `weigh_galena_then_weight_on_electronic_scale`
- `weigh_weight_then_flask_on_electronic_scale`
- `weigh_aragonite_calcite_then_fluorite_on_electronic_scale`
- `weigh_halite_galena_then_weight_on_electronic_scale`
- `weigh_small_beaker_flask_then_aragonite_on_electronic_scale`
- `weigh_weight_fluorite_then_small_beaker_on_electronic_scale`
- `weigh_flask_conical_flask_then_halite_on_electronic_scale`

### 天平称量 / Balance-Pan Weighing

- `place_small_beaker_on_balance_left_pan`
- `place_flask_on_balance_right_pan`
- `place_weight_on_balance_right_pan`
- `place_weight_on_balance_left_pan`
- `place_mineral_aragonite_on_balance_left_pan`
- `place_mineral_galena_pbs_on_balance_right_pan`
- `place_mineral_fluorite_on_balance_left_pan`
- `place_mineral_calcite_blue_on_balance_right_pan`
- `place_conical_flask_on_balance_left_pan`
- `place_weight_on_right_then_small_beaker_on_left`
- `place_small_beaker_on_left_then_weight_on_right`
- `place_weight_on_left_then_flask_on_right`
- `place_aragonite_on_left_then_calcite_on_right`
- `place_fluorite_on_left_then_halite_on_right`
- `place_galena_on_left_then_weight_on_right`
- `place_small_beaker_on_left_then_flask_on_right`
- `place_aragonite_on_left_then_small_beaker_on_right`
- `place_halite_on_right_then_galena_on_left`
- `place_weight_on_right_then_fluorite_on_left`
- `replace_aragonite_with_calcite_on_left_pan`
- `replace_flask_with_small_beaker_on_right_pan`
- `keep_weight_on_right_replace_aragonite_with_halite_on_left`
- `move_small_beaker_from_left_pan_to_right_pan`
- `move_weight_from_right_pan_to_left_pan`
- `move_fluorite_from_left_pan_to_right_pan`
- `move_calcite_from_right_pan_to_left_pan`
- `place_galena_on_left_and_weight_on_right_then_remove_galena`
- `remove_aragonite_and_calcite_from_both_pans`

## Thermal Control and Incubation (热控制与孵育) — Thermal Control and Incubation

- Planning sheet: [`docs/任务表格.ThermalControl.xlsx`](docs/任务表格.ThermalControl.xlsx)
- Subfamilies: **5**
- Tasks (planned, including buffer): **55**
- After removing buffer tasks: **47**
- Human-agent coordination tasks: **33**

| Subfamily | Tasks | Buffer | HIL |
| --- | ---: | ---: | ---: |
| 加热台处理 / Hot-Plate Heating | 13 | 2 | 2 |
| 水浴处理 / Water-Bath Incubation | 11 | 2 | 2 |
| 酒精灯加热 / Alcohol-Lamp Heating | 11 | 2 | 2 |
| 温度计操作 / Thermometer Insertion and Retrieval | 8 | 2 | 0 |
| 多设备热处理 / Multi-Device Thermal Procedures | 12 | 2 | 2 |

**Tasks in this subfamily:**

### 加热台处理 / Hot-Plate Heating

- `heat_small_beaker_on_heat_device_and_press`
- `heat_small_beaker_on_heat_device_and_wait`
- `heat_flask_on_heat_device_and_press`
- `heat_conical_flask_on_heat_device_and_wait`
- `heat_two_small_beakers_on_heat_device_in_order`
- `heat_two_flasks_on_heat_device_in_order`
- `heat_small_beaker_then_flask_on_heat_device`
- `heat_flask_then_small_beaker_on_heat_device`
- `heat_small_beaker_on_heat_device_then_retrieve`
- `heat_flask_on_heat_device_then_retrieve`
- `heat_small_beaker_on_heat_device_then_transfer`
- `heat_flask_on_heat_device_then_transfer`
- `heat_petri_dish_on_heat_device_and_wait`

### 水浴处理 / Water-Bath Incubation

- `wait_add_water_then_place_small_beaker`
- `wait_add_water_then_place_flask`
- `incubate_small_beaker_in_water_bath`
- `incubate_flask_in_water_bath`
- `incubate_two_small_beakers_in_water_bath`
- `incubate_two_flasks_in_water_bath`
- `incubate_small_beaker_then_retrieve`
- `incubate_flask_then_retrieve`
- `incubate_small_beaker_then_transfer`
- `incubate_flask_then_transfer`
- `incubate_small_beaker_then_stir`

### 酒精灯加热 / Alcohol-Lamp Heating

- `insert_thermometer_into_small_beaker`
- `insert_thermometer_into_flask`
- `insert_thermometer_into_large_beaker`
- `insert_thermometer_into_two_small_beakers`
- `insert_thermometer_into_small_beaker_then_flask`
- `insert_thermometer_into_two_flasks`
- `insert_thermometer_into_small_beaker_then_retrieve`
- `insert_thermometer_into_large_beaker_then_retrieve`

### 温度计操作 / Thermometer Insertion and Retrieval

- `wait_light_then_pick_small_beaker`
- `wait_light_then_pick_flask`
- `pick_small_beaker_over_alcohol_flame`
- `pick_flask_over_alcohol_flame`
- `heat_two_small_beakers_over_alcohol_flame`
- `heat_two_flasks_over_alcohol_flame`
- `heat_small_beaker_then_flask_over_alcohol_flame`
- `heat_flask_then_small_beaker_over_alcohol_flame`
- `heat_small_beaker_over_alcohol_flame`
- `heat_tube_over_alcohol_flame_then_return`
- `heat_small_beaker_flask_then_small_beaker_over_alcohol_flame`

### 多设备热处理 / Multi-Device Thermal Procedures

- `heat_device_small_beaker_then_insert_thermometer`
- `water_bath_small_beaker_then_insert_thermometer`
- `alcohol_lamp_small_beaker_then_insert_thermometer`
- `insert_thermometer_then_heat_device_small_beaker`
- `insert_thermometer_then_water_bath_small_beaker`
- `heat_device_then_water_bath_small_beaker`
- `water_bath_then_heat_device_small_beaker`
- `heat_device_small_beaker_and_water_bath_flask`
- `heat_device_small_beaker_and_alcohol_lamp_flask`
- `finish_heat_device_small_beaker_then_alcohol_heat_flask`
- `heat_device_small_beaker_then_stir`
- `heat_device_then_water_bath_then_thermometer`

## Apparatus and Workspace Interaction (装置与工作区交互) — Apparatus and Workspace Interaction

- Planning sheet: [`docs/任务表格WorkspaceInteraction.xlsx`](docs/任务表格WorkspaceInteraction.xlsx)
- Subfamilies: **6**
- Tasks (planned, including buffer): **64**
- After removing buffer tasks: **58**
- Human-agent coordination tasks: **0**

| Subfamily | Tasks | Buffer | HIL |
| --- | ---: | ---: | ---: |
| 垫子区域放置 / Square-Mat Placement | 16 | 1 | 1 |
| 收纳篮放置 / Basket Storage | 9 | 1 | 1 |
| 试管架插入 / Tube-Rack Insertion | 12 | 1 | 1 |
| 抽屉存取 / Drawer Access | 8 | 1 | 1 |
| 烘干箱装载 / Drying-Oven Loading | 9 | 1 | 1 |
| 综合整理 / Multi-Apparatus Organization | 10 | 1 | 1 |

**Tasks in this subfamily:**

### 垫子区域放置 / Square-Mat Placement

- `place_small_beaker_on_green_square_mat`
- `place_flask_on_yellow_square_mat`
- `place_petri_dish_on_purple_square_mat`
- `place_small_beaker_on_yellow_square_mat`
- `place_flask_on_purple_square_mat`
- `place_petri_dish_on_green_square_mat`
- `place_medium_cylinder_on_green_square_mat`
- `place_two_small_beakers_on_green_and_yellow_mats`
- `place_small_beaker_on_green_and_flask_on_yellow`
- `place_flask_on_yellow_and_petri_dish_on_purple`
- `place_petri_dish_on_purple_and_small_beaker_on_green`
- `place_small_beaker_on_yellow_and_flask_on_purple`
- `place_beaker_flask_and_petri_on_three_square_mats`
- `place_flask_on_yellow_square_mat_then_retrieve`
- `move_small_beaker_from_green_mat_to_purple_mat`
- `move_petri_dish_from_purple_mat_to_yellow_mat`

### 收纳篮放置 / Basket Storage

- `place_small_beaker_into_basket`
- `place_flask_into_basket`
- `place_conical_flask_into_basket`
- `place_two_small_beakers_into_basket`
- `place_two_flasks_into_basket`
- `place_small_beaker_then_flask_into_basket`
- `place_flask_then_small_beaker_into_basket`
- `place_small_beaker_into_basket_then_retrieve`
- `place_flask_into_basket_then_retrieve`

### 试管架插入 / Tube-Rack Insertion

- `insert_tube_into_rack`
- `insert_glass_rod_into_rack`
- `insert_mechanical_pipette_into_rack`
- `insert_two_tubes_into_rack`
- `insert_three_tubes_into_rack`
- `insert_tube_then_glass_rod_into_rack`
- `insert_glass_rod_then_mechanical_pipette_into_rack`
- `insert_mechanical_pipette_then_tube_into_rack`
- `insert_tube_glass_rod_and_mechanical_pipette_into_rack`
- `retrieve_tube_from_rack`
- `retrieve_glass_rod_from_rack`
- `retrieve_mechanical_pipette_from_rack`

### 抽屉存取 / Drawer Access

- `open_drawer_and_place_petri_dish`
- `open_drawer_and_place_pipette`
- `open_drawer_and_place_thermometer`
- `open_drawer_and_place_two_petri_dishes`
- `open_drawer_and_place_petri_dish_then_pipette`
- `open_drawer_and_retrieve_petri_dish`
- `open_drawer_and_retrieve_pipette`
- `open_drawer_exchange_petri_dish_for_pipette`

### 烘干箱装载 / Drying-Oven Loading

- `open_oven_and_place_petri_dish`
- `open_oven_and_place_small_beaker`
- `open_oven_and_place_flask`
- `open_oven_place_petri_dish_and_close`
- `open_oven_place_small_beaker_and_close`
- `open_oven_place_flask_and_close`
- `open_oven_and_place_petri_dish_then_small_beaker`
- `open_oven_and_retrieve_petri_dish`
- `open_oven_retrieve_small_beaker_and_close`

### 综合整理 / Multi-Apparatus Organization

- `place_small_beaker_on_green_mat_then_flask_into_basket`
- `place_flask_into_basket_then_petri_dish_on_purple_mat`
- `insert_tube_into_rack_then_place_small_beaker_on_yellow_mat`
- `place_small_beaker_into_basket_then_insert_glass_rod`
- `insert_mechanical_pipette_into_rack_then_place_flask_into_basket`
- `open_drawer_place_petri_then_insert_tube_into_rack`
- `open_oven_place_petri_close_then_place_small_beaker_on_green_mat`
- `open_oven_retrieve_petri_place_on_purple_mat_and_close`
- `open_drawer_retrieve_pipette_then_place_on_yellow_mat`
- `insert_tube_and_glass_rod_then_place_beaker_into_basket`
