# 旋转表示改造(euler → rotvec)修复进度书

> **文档日期**: 2026-09-24
> **分支**: `rotvec-representation`(基于 master)
> **状态**: 代码改造**步骤 1-11 已全部完成并验证**,步骤 12-14(数据重生成 → 重训 → 评测)**未开始**
> **接手人须知**: 本文档是唯一权威进度记录。接手前请通读"背景"和"未完成工作"两节,不要凭代码状态猜测。

---

## 1. 背景:为什么要做这次改造

### 1.1 问题现象

在 SciHorizon-ELAB 上用 `scripts/model_train/train_pi.py` 训练的 pi05 模型,任务成功率仅 **29.1%**,远低于预期。

### 1.2 根因分析(已确证)

对比 dev_3 上 flexiv 数据管线(`/data/qinmaokai/workspace/openpi/examples/arx/convert_to_lerobot.py`)与 SciHorizon-ELAB 管线后,定位到**旋转表示的 ±π 跳变污染**:

1. **euler 角的多值性**:H5 原始数据 `ee_state` 存 `[pos3, quat4(wxyz), gripper1]`。旧的 `convert_to_lerobot_pi.py` 把 quat 转成 euler(xyz)后,机械臂 roll 物理上钉在 ±π 边界(倒置抓取姿态)时,euler 会在 +π 和 -π 之间随机取值,相邻帧产生**假的 ±2π 跳变**。实测 100 条轨迹共 106 次跳变。

2. **跳变污染训练 target**:openpi 的 `DeltaActions` transform 计算 `actions - state` 得到 delta 旋转。当 state/action euler 恰好落在边界两侧时,delta 出现 ±6.28(整圆)的假旋转量,模型学到的是噪声。

3. **第一版 unwrap 修复失败**:曾在 `dm_env.py` 加了逐帧 unwrap 状态机(`_euler_offset`/`_prev_raw_euler`),并在 `convert_to_lerobot_pi.py` 加了 `unwrap_euler_sequence`。但 unwrap 只能处理单向穿越;实测发现**多方向振荡**(跳变方向来回变)时 unwrap 错位,unwrap 后 `max|delta|` 仍有 4.86 rad > π。**第一版修复代码已在本次改造中删除。**

4. **状态与 action 跳变位置不对齐**:state 的 euler(2 处跳变)与 action 的 euler(8 处跳变,其中 6 处为精确 ±2π)由不同代码路径产生,跳变帧不重合,DeltaActions 的减法无法消去跳变。

### 1.3 方案选型

**全链路切换到 rotvec(axis-angle)表示 + RLDS delta wrap**:

- **pi05_base 预训练原生使用 axis-angle delta**:PI 官方 libero 评测代码(`examples/libero/main.py`)用 `_quat2axisangle` 直出 delta rotvec 喂给 robosuite。换 rotvec 与预训练分布对齐,比 quaternion 更优。
- **rotvec 无 ±π 多值问题**:SO(3) → rotvec 是半径 π 实心球的唯一映射(唯一例外:球面上 `+π·n̂` ≡ `-π·n̂`,物理同旋)。
- **wrap 是强制的,不是可选的**:绝对 rotvec 仍会在 180° 边界出现 ±2π 翻转(`+π·n̂` 与 `-π·n̂` 两侧取值)。因此训练端必须用 `RLDSDeltaActions`(对 `actions[..., 3:6]` 做 `(d+π)%(2π)-π` wrap),真实单步 delta < 0.3 rad 时精确恢复真实旋转增量。openpi 已有该 transform(`transforms.py:260 RLDSDeltaActions`, `transforms.py:290 RLDSAbsoluteActions`),只需在 config 里换用。

### 1.4 约定(重要)

- **quat 约定: wxyz**(H5 的 ee_state[3:7]、`scihorizon_elab/utils/utils.py` 全部函数、MuJoCo)。scipy 的 `R.from_quat` 要 xyzw,所有转换函数内部做重排,**外部接口一律 wxyz**。
- **新的 7 维格式**: `[pos3, rotvec3, gripper1]`,替代原 `[pos3, euler3(unwrap后), gripper1]`。
- **H5 原始数据不变**:仍是 8 维 quat 格式;转换发生在 convert 脚本和 env 输出侧。

---

## 2. 已完成的工作(步骤 1-11,已验证)

### 2.1 核心转换函数(新增)

`scihorizon_elab/utils/utils.py` 新增两个函数(wxyz 约定):

```python
def quaternion_to_rotvec(quat):          # (w,x,y,z) → scipy(x,y,z,w) → as_rotvec()
def rotvec_to_quaternion(rotvec):        # as_quat()(x,y,z,w) → 重排回 (w,x,y,z)
```

冒烟验证:200 随机 quat 往返误差 < 1e-9;180° 边界行为正确。

### 2.2 数据生成端(轨迹生成)

- **`scihorizon_elab/utils/skill_lib.py`** — 20 处 waypoint 拼接:`quaternion_to_euler(env.robot.get_end_effector_quat(env.physics))` → `quaternion_to_rotvec(...)`。生成的 H5 `trajectory` 从 `[pos3, euler3, gripper]` 变为 `[pos3, rotvec3, gripper]`。
  - **有意保留** line 1075 `current_euler = quaternion_to_euler(current_quat)`:局部变量,用于倒水任务的姿态判定,不在 waypoint 数据流。
  - **有意保留** `euler_to_quaternion(-π, 0, 0)` 等 6 处:构造"末端竖直向下"等目标 quat 的常量,输入是常数不是 ee_state。

### 2.3 env 输出端(评测时 obs)

- **`scihorizon_elab/simulation/envs/dm_env.py`**:
  - **删除**了 `__init__`/`_reset_impl` 里的 `_euler_offset`/`_prev_raw_euler` unwrap 状态机(第一版失败的修复)。
  - `_unwrap_ee_state`(名字沿用,语义已变):现在直接 `quaternion_to_rotvec` 输出 `[pos3, rotvec3, gripper1]`,无任何状态、无 unwrap。
  - **保留** `set_xquat_by_name`(line ~232):场景搭建时 euler 常量 → quat,一次性设置,不在数据流。

### 2.4 训练配置(必改项)

- **`third_party/openpi/src/openpi/training/config.py`** — 两处(L ~393 `LeRobotVLABenchDataConfig` 和 L ~437 `AlignedLeRobotVLABenchDataConfig`):
  - `DeltaActions/AbsoluteActions` → **`RLDSDeltaActions/RLDSAbsoluteActions`**(带详细注释说明 wrap 必要性)。
  - ⚠️ 这是**训练正确性的关键**:数据是绝对 rotvec,没有 wrap 就会在 180° 边界重现假 delta。

### 2.5 数据转换端(4 个脚本)

所有脚本统一模式:`quat2euler` → `quat2rotvec`(wxyz 重排 + `as_rotvec()`);**删除** `unwrap_euler_sequence` 定义与全部调用;state/action 的 3:6 维存绝对 rotvec,wrap 交给训练 transform。

| 文件 | 改动 |
|---|---|
| `scripts/convert_to_lerobot_pi.py` | quat2rotvec 直出;删 unwrap;加 `assert ee_state.shape[1] == 7` |
| `scripts/convert_to_lerobot_act.py` | 同上(供 ACT 训练的转换) |
| `scihorizon_elab/utils/multithread_rlds_builder.py` | 同上(RLDS/TFDS 构建路径,被 `scripts/convert_to_rlds.py` 引用;**原计划漏列,closure audit 补上**) |

### 2.6 评测端

- **`scihorizon_elab/benchmark/evaluation/evaluator/base.py`**:
  - import 增加 `quaternion_to_rotvec, rotvec_to_quaternion`。
  - obs 侧 `last_action` 初始化:8 维兼容分支 `quaternion_to_euler` → `quaternion_to_rotvec`;7 维分支注释更新。
  - action 侧:`pos, rotvec, gripper_state = agent.predict(...)`,`quat = rotvec_to_quaternion(rotvec)` 后走 IK `get_qpos_from_ee_pos(pos, quat)`(quat wxyz,与 MuJoCo 一致)。

- **6 个 policy 文件**(`scihorizon_elab/benchmark/evaluation/model/policy/`):obs 输入侧和 action 输出侧全部改为 rotvec 语义:
  - `openpi.py`(L ~87 双分支:8 维 quat→rotvec / 7 维直出)、`gr00t.py`、`act.py`、`dp.py`、`openvla.py`(delta 累加 `target_rotvec = rotvec + delta_rotvec`)、`base.py`(RandomPolicy 同款,并修正 7 维分支 `[3:]` → `[3:6]` 的旧 bug——原代码会把 gripper 混进旋转量)。
  - ⚠️ **历史教训**:中途一个并行 agent 的改名补丁只落地了一半,留下 3 处 NameError(gr00t.py:149 引用已改名的 `ee_euler`;base.py/openvla.py 的 8 维分支赋 `rotvec` 但下游用 `euler`)。已全部修复。**接手后若再批量改名,必须 grep 验证每个赋值点的所有引用点。**

- **`third_party/openpi/examples/vlabench/eval.py`**(openpi 客户端评测入口):
  - obs 侧 `ee_euler = quaternion_to_euler(quat)` → `ee_rotvec = quaternion_to_rotvec(quat)`(import 自 `scihorizon_elab.utils.utils`,注意原来是从 `VLABench.utils.utils` import 的)。
  - action 侧返回 `target_rotvec`,由 evaluator/base.py 的 `rotvec_to_quaternion` 消费。

- **`third_party/openpi/src/openpi/policies/vlabench_policy.py`**:声明的 `quat2euler` 帮助函数改为 `quat2rotvec`(与训练 transform 端一致)。

### 2.7 GT 回放 / 数据增强工具

- `scripts/gt_replay/lerobot_gt_replay.py`:IK 前转换 `euler_to_quaternion(*euler_local)` → `rotvec_to_quaternion(rotvec_local)`(读 LeRobot 数据现在是 rotvec 格式)。
- `scripts/gt_replay/gt_replay_test.py`:同款。
- `scripts/trajectory_augmentation.py`:同款(该文件 `euler_to_quaternion` 来自 `benchmark.tasks import *` 星号导入,已补显式 import `rotvec_to_quaternion`)。

### 2.8 Closure audit(全仓扫描结论)

`grep -rn "quaternion_to_euler(\|euler_to_quaternion(\|quat2euler(\|as_euler("` 扫描 `scihorizon_elab/ scripts/ third_party/openpi/{src,policies,examples/vlabench}` 后,**数据流上已清零**。保留项逐一核实过、均不在 ee_state/waypoint 数据流:

| 位置 | 保留理由 |
|---|---|
| `utils/utils.py:36,51`(函数定义本身) | euler 函数仍被场景/任务初始化使用 |
| `utils/utils.py:140-181 find_keypoint_and_prepare_grasp` | `prior_euler` 是外部先验常量(抓取姿态候选),函数内转 quat 用于碰撞检查,输入非 ee_state |
| `skill_lib.py:199,1830,1914,2141,2267` | `euler_to_quaternion(-π,0,0)` 等构造"竖直向下"目标 quat 常量 |
| `skill_lib.py:1075` | 倒水判定局部变量 |
| `skill_lib.py:1084` | 上述判定内的逐步 quat 推进 |
| `simulation/entities/{scene,entity}.py` | 物体随机初始化姿态(euler 常量 × 随机采样 → quat),与 ee_state 无关 |
| `simulation/conditions/condition.py:872,942,963` | 成功条件判定(物理 quat → euler 比较角度),不是观测/动作数据流 |
| `benchmark/tasks/autogen_tasks/primitive/*.py` 等 | 场景初始化 euler 常量 |
| `utils/interface.py:193,201` | legacy 接口,主流程未使用 |

### 2.9 端到端冒烟测试(已通过,2026-09-24,T_194)

测试脚本模拟完整数据流 `H5 quat(wxyz) → quat2rotvec → 绝对 rotvec → delta+wrap → 还原 → rotvec_to_quaternion → quat(wxyz)`:

- utils 往返 200 随机样本误差 < 1e-9 ✅
- convert 脚本的 `quat2rotvec` 与 utils 版本数值一致 ✅
- **关键对照**:构造穿越 180° 边界的轨迹(rotvec x 从 0.99π 走到 1.01π),RLDS wrap 后 20 帧 delta 全部均匀(= 真实步长 0.003142)✅;**同轨迹走旧 euler 管线,20 帧 delta 里 1 帧 ±2π 假跳变**——复现并量化了根因。
- evaluator 侧 `rotvec_to_quaternion` 输出 wxyz 确认 ✅

### 2.10 Git 状态(文档写作时)

- 已提交:`2597859 rotvec fixing`(12 文件:+386/-74)——utils.py / skill_lib.py / dm_env.py / config.py / evaluator/base.py / 6 policy / 计划书。
- **未提交(14 文件,+73/-107)**:convert_to_lerobot_{pi,act}.py / multithread_rlds_builder.py / gt_replay 两个 / trajectory_augmentation.py / eval.py / vlabench_policy.py —— **随本文档一并提交**(见 §4)。
- 全部改动 vs master:**20 文件,+459/-181**。

### 2.11 已验证不改动

`scripts/model_train/train_pi.py`(训练入口,本身不含 euler 逻辑)、`condition.py`(成功判定)、`interface.py`(legacy)。

---

## 3. 未完成的工作(按顺序执行)

### ⚠️ 步骤 12:全量轨迹重生成(必须最先做,旧数据全部作废)

**旧 H5 数据是 euler 表示,与新代码不兼容,不能复用。** 必须用当前分支代码重新生成:

```bash
# 在新服务器上,确认分支 rotvec-representation 已检出
# 具体参数以 docs/旋转表示改造计划书.md 和既有 SOP 为准
bash scripts/generate_trajectories.sh --task <task_name> --num 200 --gpus 0,1,2,3,4,5,6
```

生成后**校验新数据**(建议写个一次性脚本):

1. 从新 H5 读 `trajectory`,检查 `actions[:, 3:6]` 的范数:单步 `|delta rotvec|`(相邻帧 wrap 后)应全部 < π,真实任务应 < 0.5 rad;
2. `|rotvec|` 的绝对范数应 ≤ π(允许 1e-6 误差);
3. 对照旧数据确认 `ee_state` 在 H5 里仍是 8 维 quat(H5 格式没变,变的是 convert 后的格式)。

> 已有诊断脚本可改造复用:曾用 `check_euler_unwrap.py` / `diag_delta_distribution.py` 检查 euler 跳变,改成 rotvec 版本(检查 wrap 后 max|delta| 从 4.86 → < 0.5,|delta|>π 帧数 → 0)即可。

### 步骤 13:重新转换 + 清 norm_stats + 重训

1. 用新 H5 跑 `scripts/convert_to_lerobot_pi.py` 生成 LeRobot 数据集;
2. **删除旧 norm_stats**:旧数据统计量基于 euler(数值范围与 rotvec 不同),必须删除让 `train_pi.py` 重新计算。路径模式:`assets/<config>/<asset>/norm_stats.json`(在 openpi 侧的 assets 目录,按训练 config 名找);
3. 用 `scripts/model_train/train_pi.py` 重训(pi05,从 pi05_base finetune)。

### 步骤 14:评测验证

1. **先单 episode 冒烟**:`third_party/openpi/examples/vlabench/eval.py` 跑 1-2 个 episode,肉眼看视频——重点看有没有**90° 级别的姿态错误**(quat wxyz/xyzw 约定搞反的典型症状)。若出现,优先排查 `rotvec_to_quaternion` 的输出约定;
2. 正常的话跑批量评测,对比旧 29.1% 基线;
3. 可选:对比新旧训练 loss 曲线/动作直方图(旧数据 delta 有 ±2π 假峰,新数据应无)。

### 排障提示(给未来的自己)

- **评测若出现 90° 姿态错误** → 查 wxyz/xyzw:`utils.py` 两个新函数外部接口均为 wxyz;scipy 调用点必须重排。
- **评测若 delta 恢复错误、姿态漂移** → 查训练 config 是否真的用了 `RLDSDeltaActions`(grep `config.py`)。
- **evaluator/policy 报 NameError** → grep `euler`,大概率是又有一处改名只改了一半。
- **成功判定失灵** → `condition.py` 用的是物理 quat,不应受影响;若确有影响,查 `condition.py:872,942,963` 的比较逻辑(保留未改,理论上不涉及)。

---

## 4. 本次提交内容

随本文档一起提交的 14 个文件(未提交 → 本次 commit):

- `docs/rotvec改造进度书.md`(本文档)
- `scripts/convert_to_lerobot_pi.py` / `scripts/convert_to_lerobot_act.py`
- `scihorizon_elab/utils/multithread_rlds_builder.py`
- `scripts/gt_replay/lerobot_gt_replay.py` / `scripts/gt_replay/gt_replay_test.py`
- `scripts/trajectory_augmentation.py`
- `third_party/openpi/examples/vlabench/eval.py`
- `third_party/openpi/src/openpi/policies/vlabench_policy.py`
- `scihorizon_elab/benchmark/evaluation/model/policy/{act,base,dp,gr00t,openpi,openvla}.py`(6 个,修复并行 agent 留下的 3 处 NameError + 补齐输出侧改名)

推送目标:`git@github.com:kaikai-2022/SciHorizon-ELAB.git`,分支 `rotvec-representation`(新远端分支)。

> **换服务器接手**:直接 `git clone` + `git checkout rotvec-representation` 即可拿到全部代码改动,无需迁移 T_194 的任何本地文件。旧训练产物(数据集/norm_stats/checkpoint)不要复用。
