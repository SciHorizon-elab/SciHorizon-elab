# SkillLib 接口文档

本文档梳理 `scihorizon_elab.utils.skill_lib.SkillLib` 中所有静态方法的接口定义，包括方法名、入参、执行功能与返回值。

**源码位置**：`scihorizon_elab/utils/skill_lib.py`

---

## 总体约定

### 公共返回签名

除少数工具方法外，SkillLib 的"动作类"方法都返回统一四元组：

```python
observations, waypoints, stage_success, task_success = SkillLib.<method>(env, ...)
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `observations` | `list[dict]` | 仿真器在执行过程中产生的逐帧观察（含 RGB、深度、点云、机器人状态等） |
| `waypoints` | `list[np.ndarray]` | 与观察一一对应的动作轨迹点，每点是 `[x, y, z, roll, pitch, yaw, gripper1, gripper2]`（9 维） |
| `stage_success` | `bool` | 当前技能步骤是否成功完成 |
| `task_success` | `bool` | 整个任务是否完成（中间技能一般恒为 `False`） |

### 夹爪状态 `gripper_state`

- 形如 `np.array([finger1, finger2])`，单位 m
- 全开约 `0.04`，全闭约 `0.0`
- 传给方法时若为 `None`，会自动用 `SkillLib._get_gripper_state(env)` 选择（lock 模式下保持锁定的当前宽度，否则返回当前值）

### 工具调用模式

在 benchmark Series 文件中，技能以 `functools.partial` 形式组装：

```python
from functools import partial
from scihorizon_elab.utils.skill_lib import SkillLib

[
    partial(SkillLib.pick, target_entity_name="beaker_0"),
    partial(SkillLib.lift, lift_height=0.15),
    partial(SkillLib.place, target_container_name="large_beaker_0"),
    partial(SkillLib.drop),
]
```

合法的技能名由 [`skill_formatter.py`](../scihorizon_elab/pipeline/nodes/code_gen_skills/skill_formatter.py) 中的 `VALID_SKILLS` 白名单约束。

---

## 技能总览

按功能划分为六大类：

| 分类 | 技能 |
|---|---|
| 基础原语（8） | `step_trajectory`, `moveto`, `moveto_entity`, `lift`, `pull`, `push`, `move_offset`, `reset` |
| 抓取与放置（6） | `pick`, `place`, `drop`, `close_gripper`, `open_gripper`, `insert_to_entity` |
| 容器操作（6） | `open_door`, `close_door`, `open_drawer`, `open_laptop`, `unscrew_cap`, `press` |
| 倾倒与混合（4） | `pour`, `pour_to_entity`, `stir_entity_with_tool`, `shake` |
| 液体操作（2） | `aspirate`, `dispense` |
| 旋转与等待（4） | `flip`, `rotate`, `wait`, `wait_for` |
| 内部辅助（5） | `_get_gripper_state`, `_get_grasped_bbox_dz`, `_find_free_drop_position`, `_resolve_press_target`（共 4 个） |

> **说明**：`pour`、`push`、`move_offset`、`flip`、`open_laptop`、`reset` 当前**无外部调用方**，是孤儿/未启用技能（见末尾"孤儿技能与已知问题"）。

---

## 1. 基础原语

### 1.1 `step_trajectory`

```python
@staticmethod
def step_trajectory(env, points, quats, gripper_state, max_n_substep=1, tolerance=0.02)
```

**功能**：通用 step 循环。把 `points/quats` 描述的轨迹逐点用 IK 求 qpos，再驱动仿真器到达。是几乎所有"移动"类技能的底层支撑。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `points` | `np.ndarray (n, 3)` | 目标位置序列 |
| `quats` | `np.ndarray (n, 4)` | 目标姿态四元数序列 |
| `gripper_state` | `np.ndarray (2)` | 夹爪宽度 |
| `max_n_substep` | `int` | 每个轨迹点的最大子步数，默认 1 |
| `tolerance` | `float` | qpos 收敛容差（默认 0.02 rad） |

**返回**：`(observations, waypoints, stage_success, task_success)`，终点距离目标 < `tolerance` 时 `stage_success=True`，仿真触发 `timestep.last()` 时 `task_success=True`。

---

### 1.2 `moveto`

```python
@staticmethod
def moveto(env, target_pos, target_quat=None, target_velocity=0.05, gripper_state=None, **kwargs)
```

**功能**：RRT 运动规划 + 插值 + step_trajectory。从当前末端位置移动到 `target_pos`。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_pos` | `np.ndarray (3,)` 或 长度 3 的可迭代对象 | 目标世界坐标位置 |
| `target_quat` | `np.ndarray (4,)` 或 `None` | 目标姿态四元数；为 `None` 保持当前姿态 |
| `target_velocity` | `float` | 末端插值速度（默认 0.05 m/step） |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度，`None` 时由 `_get_gripper_state(env)` 自动选 |
| `**kwargs` | | 透传给 `step_trajectory`，如 `max_n_substep`、`tolerance` |

**RRT 失败回退**：如果 RRT 找不到路径，自动回退为直线 `[start_pos, target_pos]`。

---

### 1.3 `moveto_entity`

```python
@staticmethod
def moveto_entity(env, target_entity_name, offset=None, gripper_state=None, **kwargs)
```

**功能**：移动到指定实体的"目标悬停位置"。**目标位置算法**：

```
target_pos = [entity_xpos[0], entity_xpos[1], entity_xpos[2] + grasped_dz + 0.08]
target_quat = euler_to_quaternion(-π, 0, 0)  # 强制竖直向下
```

其中 `grasped_dz` 是当前夹持物体 bbox 高度（无抓取物时为 0），加上 8 cm 安全余量。**目标姿态强制为竖直向下**（与 `dispense`、`insert_to_entity` 一致）。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_entity_name` | `str` | 实体名（从 `env.task.entities` 查） |
| `offset` | `Any` | **已废弃**，保留仅为向后兼容；传入会被忽略并打 warning |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |
| `**kwargs` | | 透传给 `moveto` |

**返回**：同 `moveto` 的四元组。

> **注意**：与 `dispense`、`aspirate`、`insert_to_entity` 内部 inline 的"hover 到目标上方"逻辑完全等价。如需自定义 hover 高度或非竖直姿态，请直接调用 `moveto`。

---

### 1.4 `lift`

```python
@staticmethod
def lift(env, target_pos=None, target_quat=None, gripper_state=None, lift_height=0.3, tolerance=0.02, **kwargs)
```

**功能**：从当前位置垂直向上（或向上移动到指定位置）。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_pos` | `np.ndarray (3)` 或 `None` | 显式目标位置；`None` 时按 `lift_height` 上抬 |
| `target_quat` | `np.ndarray (4)` 或 `None` | 目标姿态；`None` 时保持当前 |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |
| `lift_height` | `float` | 未指定 `target_pos` 时向上抬的距离（m，默认 0.3） |
| `tolerance` | `float` | 透传给 `step_trajectory` |
| `**kwargs` | | 透传给 `step_trajectory` |

**返回**：`(observations, waypoints, stage_success, task_success)`。

---

### 1.5 `pull`

```python
@staticmethod
def pull(env, target_pos=None, target_quat=None, gripper_state=None, pull_distance=0.3)
```

**功能**：把末端拉到 `target_pos`，缺省时按 `start_pos + [0, -pull_distance, 0]` 沿 −Y 轴拉。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_pos` | `np.ndarray (3)` 或 `None` | 目标位置 |
| `target_quat` | `np.ndarray (4)` 或 `None` | 目标姿态 |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |
| `pull_distance` | `float` | `target_pos=None` 时沿 −Y 拉的偏移（m） |

---

### 1.6 `push`

```python
@staticmethod
def push(env, target_pos=None, target_quat=None, gripper_state=None, push_distance=0.3)
```

**功能**：`pull` 的反向封装（内部调用 `SkillLib.pull(..., -push_distance)`）。⚠️ **当前全代码库无任何调用方**，可能是保留 API。

参数同 `pull`。

---

### 1.7 `move_offset`

```python
@staticmethod
def move_offset(env, offset, target_quat=None, gripper_state=None)
```

**功能**：相对当前末端位置偏移 `offset`。⚠️ **当前全代码库无调用方**，可直接用 `moveto(start + offset)` 替代。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `offset` | `np.ndarray (3)` 或长度 3 的可迭代对象 | 相对当前 EE 的位移 |
| `target_quat` | `np.ndarray (4)` 或 `None` | 目标姿态；`None` 时保持当前 |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |

---

### 1.8 `reset`

```python
@staticmethod
def reset(env, max_n_substep=200, tolerance=0.01)
```

**功能**：把机械臂驱动回 `env.task.robot.default_qpos` 定义的默认姿态。⚠️ **当前无外部调用方**，通常在 reset episode 内部被调用而非作为业务技能。

---

## 2. 抓取与放置

### 2.1 `pick`

```python
@staticmethod
def pick(env,
         target_entity_name,
         target_pos=None,
         target_quat=None,
         prepare_distance=-0.1,
         prepare_quat=None,
         prior_eulers=PRIOR_EULERS,
         specific_keypoint=None,
         target_velocity=0.05,
         motion_planning_kwargs=dict(),
         **kwargs)
```

**功能**：通用抓取。流程：
1. 用 `find_keypoint_and_prepare_grasp` 自动搜索实体的合法抓取 keypoint（`target_pos/quat` 都为 `None` 时）；若指定则直接用。
2. RRT 规划到 `prepare_pos`（`key_pos + move_quat * prepare_distance`，默认沿准备方向退 10 cm）。
3. 沿路径移动到 key_pos，调用 `close_gripper` 完成抓取。
4. 设置 grasp_lock（mode 1/2），让后续技能中夹爪不会因重力松开。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_entity_name` | `str` | 目标实体名 |
| `target_pos` | `np.ndarray (3)` 或 `None` | 显式抓取点位置；`None` 则自动搜索 |
| `target_quat` | `np.ndarray (4)` 或 `None` | 显式抓取姿态；`None` 则自动搜索 |
| `prepare_distance` | `float` | 准备点相对抓取点沿"接近方向"的距离（默认 -0.1 m） |
| `prepare_quat` | `np.ndarray (4)` 或 `None` | 准备姿态；`None` 时用 `gripper_pcd` 推出 |
| `prior_eulers` | `list[list[float]]` | 自动搜索时尝试的欧拉角先验（模块顶部 `PRIOR_EULERS`，4 组） |
| `specific_keypoint` | `int` 或 `None` | 多抓取点实体（如抽屉）指定 keypoint id |
| `target_velocity` | `float` | 路径插值速度 |
| `motion_planning_kwargs` | `dict` | 透传给 RRT |
| `**kwargs` | | 透传给 `step_trajectory` |

**返回**：`stage_success = is_grasped(...)`，`task_success` 恒为 `False`（中间技能）。

**失败返回**：找不到合法 keypoint 时 `return None`（注意：不是元组）。

---

### 2.2 `place`

```python
@staticmethod
def place(env, target_container_name, target_pos=None, target_quat=None, motion_planning_kwargs=dict())
```

**功能**：把抓取物精确放入容器内部。两阶段路径：
1. RRT 到目标正上方（`max(start_z, target_z + 0.1)`）
2. 垂直下降到目标 `place_point`
3. 自动做高度补偿，让物体底部刚好在 `target_pos` Z
4. 松开夹爪 + lift 5cm 防撞

`place` 与 `drop` 区别：`place` 使用容器的 `place_point`，**不做 `ee_offset` 补偿**（精确放入）；`drop` 用 `ee_offset` 防止物体撞桌面。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_container_name` | `str` | 容器实体名（必须提供 `get_place_point`） |
| `target_pos` | `np.ndarray (3)` 或 `None` | 显式放置点；`None` 时随机选 `place_point` |
| `target_quat` | `np.ndarray (4)` 或 `None` | 目标姿态；`None` 时保持当前 |
| `motion_planning_kwargs` | `dict` | 透传给 RRT |

**返回**：松爪后仍有物体被夹持则 `stage_success=False`。

---

### 2.3 `drop`

```python
@staticmethod
def drop(env, target_surface_pos=None, target_quat=None, drop_height=0.05, motion_planning_kwargs=dict())
```

**功能**：把抓取物放到桌面/平面。`target_surface_pos=None` 时调用 `_find_free_drop_position` 在桌面 XY 范围 `[-0.25, 0.25]` 自动找最远离当前位置的空位。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_surface_pos` | `np.ndarray (3)` 或 `None` | 目标表面位置；`None` 自动寻位 |
| `target_quat` | `np.ndarray (4)` 或 `None` | 目标姿态 |
| `drop_height` | `float` | 物体底部距离表面的高度（m，默认 0.05） |
| `motion_planning_kwargs` | `dict` | 透传给 RRT |

**特殊行为**：使用 `ee_offset` 补偿夹爪几何，避免物体与桌面碰撞。

---

### 2.4 `close_gripper`

```python
@staticmethod
def close_gripper(env, repeat=1)
```

**功能**：分 10 步逐步闭合夹爪（从 0.04 线性收敛到 0），每步执行 `repeat` 次 env.step。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `repeat` | `int` | 每个张开/闭合步的 env.step 重复次数 |

**返回**：`(observations, waypoints, True, task_success)`，`stage_success` 恒为 `True`（此方法不检测抓取结果）。

> **Grasp Lock 联动**：`pick` 内部调用本方法完成后会设置 `_lock_gripper_state`，使后续 step 中夹爪保持当前宽度。

---

### 2.5 `open_gripper`

```python
@staticmethod
def open_gripper(env, repeat=1)
```

**功能**：分 10 步逐步张开夹爪。**成功后清除 Grasp Lock**（`_grasped_entity_info`、`_lock_gripper_state` 置 None；mode 2 时移除 weld 约束）。

`stage_success = not env.robot.get_ee_open_state(env.physics)`（注意 `get_ee_open_state` 实际返回"是否关闭"——名字与语义相反）。

---

### 2.6 `insert_to_entity`

```python
@staticmethod
def insert_to_entity(env, target_entity_name, insert_depth=0.05, gripper_state=None)
```

**功能**：把抓取物插入目标实体的"孔位"（place_point，group=2 site）。
1. 按"距夹持物 XY 最近 + 未被其他物体占据"选择孔位（4 cm 内、Z 低于孔位 + 5 cm 视为被占）
2. RRT 到孔位正上方 `bbox(dz) + 8 cm`，末端竖直向下
3. lift 下降到 `insert_point - [0,0,insert_depth]`
4. open_gripper
5. lift 15 cm 防撞

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_entity_name` | `str` | 目标实体（必须提供 `get_place_point`，如 `chemistry_tube_stand`） |
| `insert_depth` | `float` | 插入深度（m，默认 0.05） |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |

**返回**：`(observations, waypoints, True, task_success)`。

---

## 3. 容器操作

### 3.1 `open_door`

```python
@staticmethod
def open_door(env, target_container_name)
```

**功能**：开门。两阶段：
1. `pick(target_entity_name=..., specific_keypoint=0)` 抓门把手（keypoint 0 = door_handle_grasp）
2. 用 `target_container.get_open_trajectory(env)` 拿到预设圆弧轨迹，沿轨迹 step_trajectory，姿态全程保持 pick 后的朝向（不绕 world Z 旋转，避免 IK 奇异）

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_container_name` | `str` | 容器实体名（必须提供 `get_open_trajectory`、`is_open`、`door_joint`） |

**返回**：`stage_success = env.task.entities[name].is_open(...)`。

---

### 3.2 `close_door`

```python
@staticmethod
def close_door(env, target_container_name, gripper_state=np.zeros(2))
```

**功能**：关门的反向版本。`target_container.get_close_trajectory` 必须返回非空，否则直接返回 `stage_success=True`。⚠️ 当前无外部调用方。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_container_name` | `str` | 容器实体名 |
| `gripper_state` | `np.ndarray (2)` | 夹爪宽度（默认 `np.zeros(2)` 闭合） |

---

### 3.3 `open_drawer`

```python
@staticmethod
def open_drawer(env, target_container_name, pick_prior_eulers=[[-π/2, 0, 0]], drawer_id=0)
```

**功能**：开抽屉。两阶段：
1. `pick(...)` 抓抽屉把手（`specific_keypoint=drawer_id`）
2. `step_trajectory(target_container.get_slide_trajectory(...))` 滑出抽屉

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_container_name` | `str` | 抽屉实体名 |
| `pick_prior_eulers` | `list[list[float]]` | pick 的先验欧拉角（默认 `[[-π/2, 0, 0]]`） |
| `drawer_id` | `int` | 抽屉编号 0-2（自上而下） |

**返回**：`stage_success` 恒为 `True`（代码中有 `# TODO check the drawer state`）。

---

### 3.4 `open_laptop`

```python
@staticmethod
def open_laptop(env, target_entity_name)
```

**功能**：开笔记本电脑。⚠️ 当前无外部调用方（项目里没有 laptop 任务）。

`laptop.get_open_trajectory` + `laptop.screen_joint` 计算每步绕 hinge axis 旋转 0.04 rad 的姿态序列，step_trajectory 走完轨迹后 open_gripper，确认 `is_open`。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_entity_name` | `str` | 笔记本实体名 |

---

### 3.5 `unscrew_cap`

```python
@staticmethod
def unscrew_cap(env, target_entity_name,
                rotation_angle=-4*np.pi,
                target_q_velocity=np.pi/40,
                max_n_substep=30,
                tolerance=0.01,
                lift_height=0.03)
```

**功能**：拧开瓶盖。流程：
1. `pick(target_entity_name=..., prior_eulers=[[π, 0, 0]])` 抓瓶盖
2. 直接修改腕关节 qpos[-1] 旋转 `rotation_angle` 弧度（默认 -4π = 两圈顺时针），瓶盖 hinge joint 被物理被动跟随
3. lift `lift_height` 让 slide joint 自动上升
4. open_gripper

成功判定：`slide_joint.qpos` 相对初始值增大 > 0.003 m。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_entity_name` | `str` | 瓶盖/瓶身复合实体名 |
| `rotation_angle` | `float` | 总旋转角度（弧度），正=逆时针 |
| `target_q_velocity` | `float` | 角速度（弧度/步） |
| `max_n_substep` | `int` | 每步最大子步数 |
| `tolerance` | `float` | qpos 容差 |
| `lift_height` | `float` | 拧完后末端额外上提距离（m） |

---

### 3.6 `press`

```python
@staticmethod
def press(env, target_pos, target_quat=None, move_vector=[0, 0, 0.1], max_n_substep=100)
```

**功能**：按压按钮。流程：
1. `_resolve_press_target(env, target_pos)` 把字符串实体名解析为世界坐标（优先用 `get_start_button_pos`，否则 `get_xpos`）
2. moveto 到 `target_pos + move_vector`（准备点，默认正上方 10 cm）
3. 用 10 步线性闭合夹爪（模拟按压）
4. moveto 到 `target_pos`（实际按下）

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_pos` | `str` 或 `np.ndarray (3,)` | 实体名（如 `"heat_device_0"`）或坐标 |
| `target_quat` | `np.ndarray (4)` 或 `None` | 姿态 |
| `move_vector` | `list/np.ndarray (3,)` | 准备点相对按下点的偏移（默认 `[0,0,0.1]`） |
| `max_n_substep` | `int` | 透传给 moveto |

---

## 4. 倾倒与混合

### 4.1 `pour`

```python
@staticmethod
def pour(env, target_delta_qpos=np.pi, target_q_velocity=np.pi/40, n_repeat_step=2, tolerance=0.01)
```

**功能**：原地倾倒（不指定目标容器）。直接驱动腕关节 qpos[-1] 以角速度旋转总角度 `target_delta_qpos`。⚠️ **当前无外部调用方**，被 `pour_to_entity` 与 `rotate` 替代。

---

### 4.2 `pour_to_entity`

```python
@staticmethod
def pour_to_entity(env,
                   target_container_name,
                   tilt_angle=np.pi*2/3,
                   tilt_velocity=np.pi/80,
                   n_repeat_step=6,
                   lift_before=0.2,
                   wait_time=10)
```

**功能**：倾倒到指定容器上方。流程：
1. lift 上抬 `lift_before`（默认 20 cm）避免碰撞
2. moveto 到容器正上方 +40 cm
3. 用 IK 逐步倾斜末端（绕 Y 轴 tilt_velocity/步），并保持末端位置不变；记录每步 qpos
4. `wait(wait_time)`（默认 10 步）让液体流出
5. **逆向回放**倾倒过程的 qpos（对称回正，无 IK 跳变）

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_container_name` | `str` | 目标容器实体名 |
| `tilt_angle` | `float` | 总倾斜角度（弧度，默认 2π/3 ≈ 120°） |
| `tilt_velocity` | `float` | 每步倾斜角速度（弧度） |
| `n_repeat_step` | `int` | 每个动作步的 env.step 重复次数 |
| `lift_before` | `float` | 倾倒前抬高距离（m） |
| `wait_time` | `int` | 倾倒后等待步数 |

**返回**：`stage_success` 恒为 `True`，`task_success` 在 `timestep.last()` 时变 `True`。

---

### 4.3 `stir_entity_with_tool`

```python
@staticmethod
def stir_entity_with_tool(env, target_container_name,
                          stir_radius=0.01, stir_duration=2, insert_ratio=2/3)
```

**功能**：用夹持的搅拌工具搅动容器。流程：
1. 取容器 `place_point` 作圆心，读 `top_site`/`bottom_site` 算容器内部高度
2. 计算插入深度 `bottom_z + internal_height * insert_ratio`（默认容器高度的 2/3）
3. 计算工具底部到 grasp keypoint 的 Z 偏移 `tool_offset_z`
4. moveto 到 hover（圆心上方 25 cm + tool_offset_z），竖直向下姿态
5. lift 下降到插入深度
6. 每步 10°（36 步一圈），共 `stir_duration` 圈，沿 `stir_radius` 圆周运动

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_container_name` | `str` | 容器实体（需要 `top_site`、`bottom_site`、`get_place_point`） |
| `stir_radius` | `float` | 圆周半径（m，默认 0.01） |
| `stir_duration` | `int` | 搅拌圈数（默认 2 圈） |
| `insert_ratio` | `float` | 插入深度相对容器内部高度的比例（默认 2/3） |

---

### 4.4 `shake`

```python
@staticmethod
def shake(env, n_shakes=3, shake_angle=0.5, steps_per_swing=5,
          gripper_state=None, max_n_substep=10, pos_tolerance=0.005)
```

**功能**：在当前位置摇晃夹持物。绕 Y 轴交替 +`shake_angle` ↔ -`shake_angle`，每段 `steps_per_swing` 步插值。每步用**当前真实位置**重新解算 IK 避免漂移。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `n_shakes` | `int` | 摇摆往返次数 |
| `shake_angle` | `float` | 摇摆幅度（弧度，默认 0.5 ≈ 28°） |
| `steps_per_swing` | `int` | 每段摇摆的插值步数 |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |
| `max_n_substep` | `int` | 每个姿态点的最大执行步数 |
| `pos_tolerance` | `float` | 位置容差（m，默认 5 mm） |

---

## 5. 液体操作

### 5.1 `aspirate`

```python
@staticmethod
def aspirate(env, source_container_name,
             dwell_steps=20, descend_below_surface=0.02, gripper_state=None)
```

**功能**：吸取溶液。流程：
1. 从源容器的 `solution` geom（cylinder）算出液面 Z = `geom_z + halfheight`
2. 取夹持工具的 `aspirate_site`，计算 `tool_z_offset = aspirate_site_z - ee_z`
3. moveto 到容器 placepoint 正上方 `bbox(dz) + 8 cm`，竖直向下
4. lift 下降使 aspirate_site 到液面下 `descend_below_surface`（默认 2 cm）
5. **固定 qpos** 静止 `dwell_steps` 步（默认 20 步 ≈ 2 s）模拟吸取
6. 记录溶液信息到工具实体（`tool.store_solution(solution, solution_rgba)`）
7. lift 抬回 hover 高度

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `source_container_name` | `str` | 源容器实体名（必须有 `solution` geom） |
| `dwell_steps` | `int` | 液面下静止步数 |
| `descend_below_surface` | `float` | aspirate_site 低于液面的深度（m） |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |

**返回**：`stage_success=True`，`task_success=False`（中间技能）。

**异常**：源容器无 `solution` geom、夹爪空、工具无 `aspirate_site` 时抛 `ValueError`。

---

### 5.2 `dispense`

```python
@staticmethod
def dispense(env, target_container_name, dwell_steps=20, gripper_state=None)
```

**功能**：点样到目标容器上方。流程：
1. 取目标 placepoint（必须存在，否则失败）
2. 校验夹持物为带 `aspirate_site` 的工具
3. moveto 到 placepoint 正上方 `bbox(dz) + 8 cm`，竖直向下
4. lift 下降使 aspirate_site 到 placepoint 下方 1 cm
5. 固定 qpos 静止 `dwell_steps` 步（默认 ≈ 2 s）
6. lift 抬回 hover 高度

**注意**：实际溶液颜色转移由 `DispenseCondition` 在判定条件满足时调用 `solution_reaction` 完成（本函数不直接 set rgba）。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `target_container_name` | `str` | 目标容器实体名（必须有 place_point） |
| `dwell_steps` | `int` | 静置步数 |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |

---

## 6. 旋转与等待

### 6.1 `flip`

```python
@staticmethod
def flip(env, gripper_state=None, target_q_velocity=π/40, max_n_substep=30, tolerance=0.01)
```

**功能**：原地翻转（绕腕关节旋转 π 弧度）。⚠️ **当前无外部调用方**，被 `rotate(rotation_angle=π)` 替代。

---

### 6.2 `rotate`

```python
@staticmethod
def rotate(env, rotation_angle=π/2,
           gripper_state=None, target_q_velocity=π/40,
           max_n_substep=30, tolerance=0.01)
```

**功能**：通过驱动腕关节 qpos[-1] 旋转夹持物（与 `unscrew_cap` 第 2 步相同的机制）。

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `rotation_angle` | `float` | 旋转角度（弧度），正=逆时针，默认 π/2 |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |
| `target_q_velocity` | `float` | 角速度（弧度/步） |
| `max_n_substep` | `int` | 每步最大子步数 |
| `tolerance` | `float` | qpos 容差 |

**成功判定**：`|final_qpos[-1] - (initial_qpos[-1] + rotation_angle)| < 10 * tolerance`。

---

### 6.3 `wait`

```python
@staticmethod
def wait(env, wait_time=100, gripper_state=None)
```

**功能**：机械臂保持当前 qpos 静止 `wait_time` 步。

---

### 6.4 `wait_for`

```python
@staticmethod
def wait_for(env,
             wait_duration=2.0,
             entity_name=None,
             change_type=None,
             solution=None,
             color=None,
             gripper_state=None)
```

**功能**：等待一段时间后自动应用环境变化（用于人机协同任务，如"等待人工添加液体"）。以 10 fps 计算步数。

`change_type` 取值：

| 类型 | 所需额外参数 | 行为 |
|---|---|---|
| `"add_solution"` | `solution="CuSO4"` 等 | 添加溶液（实体需有 `set_solution_rgba(physics, solution)`） |
| `"change_color"` | `color=[r,g,b,a]` | 改实体颜色（优先 `set_solution_rgba`，否则遍历 geom 设 rgba） |
| `"solution_change_color"` | `color=[r,g,b,a]` | 同上 |
| `"Light_the_alcohol_lamp"` | 无 | 调 `set_flame_state(lit=True)` 点燃酒精灯 |

| 参数 | 类型 | 说明 |
|---|---|---|
| `env` | `LM4ManipEnv` | 仿真环境 |
| `wait_duration` | `float` | 等待秒数（默认 2.0） |
| `entity_name` | `str` 或 `None` | 目标实体名 |
| `change_type` | `str` 或 `None` | 变化类型 |
| `solution` | `str` 或 `None` | 溶液名 |
| `color` | `list/np.ndarray (4,)` 或 `None` | RGBA 颜色 |
| `gripper_state` | `np.ndarray (2)` 或 `None` | 夹爪宽度 |

---

## 7. 内部辅助方法（不直接调用）

下划线开头的方法设计为 SkillLib 内部使用，部分被外部代码引用。

### 7.1 `_get_gripper_state`

```python
@staticmethod
def _get_gripper_state(env, gripper_state=None)
```

**功能**：选取夹爪宽度。
- 显式传入 → 用传入值
- 否则取 `env._lock_gripper_state`（grasp_lock 模式下保持当前宽度）
- 否则返回 `np.zeros(2)`（默认关闭）

被几乎所有"动作类"方法内部调用。

### 7.2 `_get_grasped_bbox_dz`

```python
@staticmethod
def _get_grasped_bbox_dz(grasped_objs, default_dz=0.15)
```

**功能**：从被抓物体 XML 顶部注释 `<!-- @bbox dx=... dy=... dz=... -->` 读出 `dz`（物体高度）。读不到时返回 `default_dz`（默认 0.15 m）。

被 `dispense`、`aspirate`、`insert_to_entity` 内部计算 hover 高度时调用。

### 7.3 `_find_free_drop_position`

```python
@staticmethod
def _find_free_drop_position(env, grasped_entity, drop_height=0.05)
```

**功能**：在桌面 XY 范围 `[-0.25, 0.25]` 网格搜索空位放置物体。筛选条件：距其他物体 > 10 cm、距自身当前位置 > 15 cm。结果按"距自身最远"排序，返回首个候选 `(x, y, z)`。无空位返回 `None`。

被 `drop(target_surface_pos=None)` 内部调用。

### 7.4 `_resolve_press_target`

```python
@staticmethod
def _resolve_press_target(env, target)
```

**功能**：把 `press()` 的 `target_pos` 入参规范化：
- `np.ndarray/list/tuple` 长度 3 → 原样转 `np.array`
- `str` → 查 `env.task.entities[name]`：
  - 实体有 `get_start_button_pos(physics)` 且返回非空 → 用该坐标
  - 否则 fallback 到 `entity.get_xpos(physics)`

被 `press()` 内部调用。

---

## 8. 孤儿技能与已知问题

### 8.1 孤儿技能（已定义但全代码库无调用方）

| 技能 | 建议 |
|---|---|
| `pour` | 与 `rotate` 几乎完全一致（仅默认角度不同）；可删除 |
| `push` | 是 `pull` 的 1 行 wrapper；可删除 |
| `move_offset` | 是 `moveto` 的 1 行 wrapper；可删除 |
| `flip` | 与 `rotate(rotation_angle=π)` 等价；可删除 |
| `open_laptop` | 项目中无 laptop 任务；可删除 |
| `reset` | 通常在 episode 循环中调用而非业务技能；保留或删除均可 |
| `close_door` | 有完整实现但与 `open_door` 没有任务方；按需保留 |

### 8.2 缺失的方法（白名单与外部代码在用但 SkillLib 没实现）

| 方法 | 影响 |
|---|---|
| **`gently_pick`** | 10 个 benchmark 文件 + `skill_formatter.py` 白名单在调用，运行时会 `AttributeError`。签名形如 `gently_pick(target_entity_name, prior_eulers=[[-π, 0, 0]], extra_close_ratio=0.2, n_close_steps=20, contact_dist_threshold=0.005, hold_steps=5)`，需要补实现 |

### 8.3 调试残留

- 文件中包含约 **130 个 `print(...)` 调用**（多为 `[xxx] DEBUG ...` 风格），分布在 `pick`、`place`、`lift`、`dispense`、`aspirate`、`close_gripper`、`open_door` 等技能中。
- `pick`（行 307）和 `close_gripper`（行 1184）有函数内 `import mujoco as mj`，可挪到模块顶部。
- 发现 5 行被注释掉的代码（`pick` 中两段）与 8 行 `# DEBUG: ...` 注释。

建议后续统一替换为 `logger.debug(...)`（模块顶部已 `import logging; logger = logging.getLogger(__name__)`，但**全文件未用过 logger**）。

---

## 9. 与 skill_formatter 白名单的对应

`pipeline/nodes/code_gen_skills/skill_formatter.py` 中 `VALID_SKILLS` 白名单共 28 个技能，与 SkillLib 实际可用技能对照：

| 白名单 | SkillLib | 状态 |
|---|---|---|
| pick | ✅ | OK |
| **gently_pick** | ❌ | **缺失**（运行时 AttributeError） |
| place | ✅ | OK |
| drop | ✅ | OK |
| lift | ✅ | OK |
| moveto | ✅ | OK |
| moveto_entity | ✅ | OK |
| pour | ✅ | 但无外部调用（孤儿） |
| pour_to_entity | ✅ | OK |
| push | ✅ | 但无外部调用（孤儿） |
| press | ✅ | OK |
| flip | ✅ | 但无外部调用（孤儿） |
| wait | ✅ | OK |
| rotate | ✅ | OK |
| open_gripper | ✅ | OK |
| close_gripper | ✅ | OK |
| open_door | ✅ | OK |
| close_door | ✅ | 但无外部调用（孤儿） |
| open_drawer | ✅ | OK |
| open_laptop | ✅ | 但无外部调用（孤儿） |
| move_offset | ✅ | 但无外部调用（孤儿） |
| reset | ✅ | 但无外部调用（孤儿） |
| shake | ✅ | OK |
| insert_to_entity | ✅ | OK |
| stir_entity_with_tool | ✅ | OK |
| wait_for | ✅ | OK |
| unscrew_cap | ✅ | OK |
| aspirate | ✅ | OK |
| dispense | ✅ | OK |

---

## 10. 调用链关系图

```
外部 benchmark:
    partial(SkillLib.xxx, ...) → SkillLib.xxx()

SkillLib 主要调用关系:

step_trajectory (底层核心)
    ↑
    ├── moveto ──────────→ rrt_motion_planning
    │       ↑
    │       ├── moveto_entity
    │       ├── pour_to_entity (Step 1, 2)
    │       ├── stir_entity_with_tool (Step 1: hover)
    │       ├── aspirate (Step 3: hover)
    │       └── dispense (Step 3: hover)
    │
    ├── pick ──→ rrt_motion_planning
    │              ↑
    │              └── open_door (Step 1)
    │              └── open_drawer (Step 1)
    │              └── unscrew_cap (Step 1)
    │              └── insert_to_entity (Step 1: hover, 走 lift)
    │
    ├── place ──→ rrt_motion_planning
    │              └── 内部 close_gripper → open_gripper → lift
    │
    ├── drop ──→ _find_free_drop_position
    │
    ├── lift (垂直移动)
    │      ↑
    │      ├── aspirate (Step 4, Step 7: 上下)
    │      ├── dispense (Step 4, Step 6: 上下)
    │      ├── insert_to_entity (Step 2, Step 4: 下降 + 抬升)
    │      ├── stir_entity_with_tool (Step 2: 垂直下降)
    │      └── place (lift 5cm 防撞)
    │
    ├── pull ──→ push
    │
    └── move_offset ──→ moveto

lock 机制:
    pick → close_gripper → 设置 env._lock_gripper_state
    open_gripper → 清除 env._lock_gripper_state
    所有需要夹爪保持宽度的技能 → _get_gripper_state(env)
```
