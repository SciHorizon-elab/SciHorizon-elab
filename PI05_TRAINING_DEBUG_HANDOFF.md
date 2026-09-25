# pi0.5 训练流程对比与数据异常排查 — 工作交接文档

> 给下一位 agent 接手用。请先读完"现状"再做任何动作。

---

## 0. TL;DR（先看这一段）

用户在仿真（SciHorizon-ELAB）里用 ~100 条轨迹训的 pi0.5 抓取放置任务只有 **40-50% 成功率**；在真机（arx openpi）相同难度任务有 **80-90%**。要让两边对齐，需要先排除"训练流程是否存在系统性 bug"。

当前**最值得怀疑的根因**：`convert_to_lerobot_pi.py` 里对 `state` 和 `action` 的 euler 序列各自独立做 unwrap（连续化），两者在 ±π 分支边界可能差出整圈 2π；随后 openpi 训练链里的 `DeltaActions`（`actions - state`）会把"±2π 的相对差"塞进训练 target，污染对应维度的分布——roll 这一维污染最严重。

但在动手改之前，必须**用数据证伪或证实**这个怀疑。我已经补齐了 scihorizon_elab 环境的依赖，下面是**接下来 agent 接手需要执行的具体验证步骤**。

---

## 1. 仓库与目录速览

两个 openpi 仓库都基于 openpi 但**是独立 fork**：

| 仓库 | 用途 | 关键路径 |
|---|---|---|
| `/mnt/t_52/qinmaokai/workspace/openpi` | arx 真机训练（80-90%） | `src/openpi/policies/arx_policy_multicam.py`、`examples/arx/*.sh` |
| `/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB` | elab 仿真项目 | `third_party/openpi/`（openpi fork）、`scripts/`（converter & trainer）、`scihorizon_elab/`（仿真 + 评测） |

SciHorizon-ELAB 关键文件：

- `scripts/convert_to_lerobot_pi.py` — HDF5 → LeRobot（含 euler unwrap）
- `scripts/model_train/train_pi.py` — 一键训练脚本（生成 → 转换 → norm_stats → 训练）
- `scripts/evaluate_policy.py` — 评测入口（连 openpi websocket 服务）
- `scihorizon_elab/benchmark/evaluation/model/policy/openpi.py` — 评测客户端，接收 obs → 发 websocket → 拿 action chunk
- `scihorizon_elab/simulation/envs/dm_env.py:_unwrap_ee_state` — 评测端 ee_state 的 unwrap（与 converter 同语义）
- `third_party/openpi/src/openpi/policies/vlabench_policy.py` — 仿真 policy 客户端 wrapper
- `third_party/openpi/src/openpi/training/config.py` — `pi05_ft_*` 系列 config 注册处
- `third_party/openpi/src/openpi/transforms.py` — `DeltaActions` / `AbsoluteActions`（**注意这里没有对 euler 做 ±π 归一化**）
- `third_party/openpi/assets/pi05_ft_*/<repo_id>/norm_stats.json` — 已存在的 norm_stats 文件

---

## 2. 已确认的事实（按时间顺序，不要再花时间重测）

### 2.1 训练流程上 arx vs elab 的差异

| 维度 | arx | elab |
|---|---|---|
| 输入图像来源 | 真实相机 | MuJoCo 渲染（`render_options`） |
| Action 表示 | **delta** (`actions - state`，前6维) | **delta**（2026-09-12 后；`DeltaActions` 由 config 工厂注入） |
| normalize 路径 | `<assets_base_dir>/<config>/<repo_id>/norm_stats.json` | 同 |
| 评测端 action 还原 | `AbsoluteActions` | `AbsoluteActions`（与训练对称） |

**重要纠正**：之前怀疑 elab "没做 deltapose" 是**错的**。config.py:387-392 通过 `Group.push` 把 `DeltaActions` 追加到 inputs 末尾、把 `AbsoluteActions` 插到 outputs 开头；与 arx `arx_policy_multicam.py:172` 等价。`compute_norm_stats.py` 也走同一条链，norm_stats 是在 delta 之后统计的。

### 2.2 norm_stats 里被观察到的异常特征（**待核实**）

从磁盘上已有的 elab norm_stats 看：

- `pi05_ft_place_beaker_v3` actions std：`[0.036, 0.028, 0.034, **2.08**, 0.014, 0.004, 0.49]`
- roll 维 q01 / q99 = **−6.283 / +6.278**（即 ±2π）
- `pi05_ft_place_beaker_v4`、`pi05_ft_pick_cylinder` 同样症状

arx 对照组：actions std `[0.015, 0.010, 0.012, 0.023, 0.049, 0.059, 1.69]`，roll q01/q99 = ±0.2。

**特征解读**：如果训练 target 的 delta 真的是"小增量 + 随机 ±2π 跳变"的双峰污染，z-score 归一化后 roll 维 std 会被拉大到 ~2 量级、q01/q99 打满 ±2π。这恰好是 elab 的形态。

### 2.3 unwrap 的双源不一致（**怀疑的机理**）

`scripts/convert_to_lerobot_pi.py:134, 146`：

```python
ee_euler_unwrapped = unwrap_euler_sequence(ee_euler)        # state 序列独立 unwrap
actions[:, 3:6] = unwrap_euler_sequence(actions[:, 3:6])    # action 序列独立 unwrap
```

state 和 action 两条序列**各自独立 unwrap**，基准可能差 2π：
- 倒置抓取姿态（机械臂 roll 钉在 ±π 分支边界），测量值和指令值各自越过 ±π 边界的帧不完全对齐
- 错位一次后，差会持续到 episode 末
- 之后训练链 `DeltaActions` 做 `actions - state` 时把 ±2π 塞进 target
- openpi 的 `DeltaActions`（`third_party/openpi/src/openpi/transforms.py:217-235`）**不做 [-π, π] 归一化**（注意另一份 `RLDSDeltaActions:284` 做了，但 LeRobot 链没用到）

---

## 3. 已完成：scihorizon_elab 环境依赖补齐

接手 agent **不要再装包**，下面的命令在我前面会话里已经跑过了：

```bash
# lerobot 0.1.0 复制（豆瓣源没拉到真包，最终从 pi_depth 拷）
SRC=/mnt/t_52/qinmaokai/miniconda3/envs/pi_depth/lib/python3.12/site-packages/lerobot
DST=/mnt/t_52/qinmaokai/miniconda3/envs/scihorizon_elab/lib/python3.10/site-packages/lerobot
rm -rf "$DST" && cp -a "$SRC" "$DST"

# 纯 Python 依赖（豆瓣源即可）
PY=/mnt/t_52/qinmaokai/miniconda3/envs/scihorizon_elab/bin
$PY/pip install --index-url https://pypi.doubanio.com/simple/ --no-deps \
  sentencepiece beartype tqdm_loggable pytest pluggy iniconfig uvloop

# tensorstore 必须用豆瓣源装匹配 py3.10 的 wheel（vlac_train 拷来的 .so 是 cpython-312）
$PY/pip install --index-url https://pypi.doubanio.com/simple/ --force-reinstall --no-deps tensorstore

# flax 必须降到 0.10.5（0.12 要求 jax>=0.8.1，scihorizon_elab 是 jax 0.6.1）
$PY/pip install --index-url https://pypi.doubanio.com/simple/ --no-deps "flax==0.10.5"

# jaxtyping / dataclasses-json（orbax-export 需要）
SRC=/mnt/t_71/huangfuxian/code/vlac-deploy/.conda/envs/vlac_train/lib/python3.12/site-packages
DST=/mnt/t_52/qinmaokai/miniconda3/envs/scihorizon_elab/lib/python3.10/site-packages
cp -a $SRC/dataclasses_json $SRC/jaxtyping $DST/
cp -a $SRC/dataclasses_json-*.dist-info $SRC/jaxtyping-*.dist-info $DST/

# datetime.UTC shim（py3.10 没有，openpi 在 download.py 用了它）
cat > $DST/sitecustomize.py <<'PY'
import datetime
if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc
PY
```

验证全部 openpi 模块 import：

```bash
PYTHONPATH=/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/third_party/openpi/src \
  /mnt/t_52/qinmaokai/miniconda3/envs/scihorizon_elab/bin/python -c "
import openpi.transforms, openpi.models.model, openpi.shared.normalize, openpi.training.config, openpi.training.data_loader
print('all ok')"
```

应该输出 `all ok`。

**仍未验证**：compute_norm_stats.py 端到端跑通（要做 norm_stats 时再确认一次 import）。`scripts/convert_to_lerobot_pi.py` 不依赖 openpi（已验证可 import）。

---

## 4. 接手 agent 的任务清单

按下面顺序执行，**每一步都要报告结果**，不要跳过：

### Step 1：把现有 HDF5 走完整流程重新生成一份 norm_stats

**目标**：在干净的环境下，复现 `pi05_ft_pick_cylinder` 那个 norm_stats 的生成过程，看 roll 维 q01/q99 是否再次出现 ±2π。

- HDF5 数据位置：`/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/dataset/autogen_tasks/`（约 30 个任务，每个任务一个或多个 `data_*.hdf5`）
- 推荐选 `1_pour_beaker_into_beaker` 或 `4_relay_beaker_via_flask_to_cylinder`（液处理、抓取倾倒，最接近用户场景）
- 跑：
  ```bash
  PYTHONPATH=/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/third_party/openpi/src \
  HF_HOME=/mnt/t_52/qinmaokai/cache/huggingface \
  HF_LEROBOT_HOME=/mnt/t_52/qinmaokai/cache/huggingface/lerobot \
    /mnt/t_52/qinmaokai/miniconda3/envs/scihorizon_elab/bin/python \
    /mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/scripts/convert_to_lerobot_pi.py \
    --dataset-name <新名字，比如 debug_pick_cylinder_test> \
    --dataset-path /mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/dataset/autogen_tasks \
    --task-list <选定的任务名> \
    --max-files 50 \
    --resolution 480
  ```
- 然后：
  ```bash
  PYTHONPATH=/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/third_party/openpi/src \
    /mnt/t_52/qinmaokai/miniconda3/envs/scihorizon_elab/bin/python \
    /mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/third_party/openpi/scripts/compute_norm_stats.py \
    --config-name=pi05_ft_pick_cylinder
  ```
- 看输出 norm_stats.json 的 actions.std[3] 和 actions.q01[3] / q99[3]：

| 结果 | 含义 | 接下来 |
|---|---|---|
| std[3] ~ 1.5~2.1、q01/q99 = ±2π | 假设得到证实，**继续 Step 2** | 改 converter 的 unwrap |
| std[3] ~ 0.01~0.06、q01/q99 = ±0.2 | 假设证伪，磁盘上那份旧 norm_stats 可能因为别的原因污染（比如旧版代码） | 检查 git history，定位污染源 |
| 中间值 | 可能是采样数不够或任务不典型 | 加更多任务对比 |

### Step 2（如果 Step 1 证实了假设）：写一个最小修复并离线验证

**目标**：在不改 openpi 源码的前提下，证明"统一 unwrap 基准"能把 roll 维 ±2π 污染消掉。

最小修复思路（写到 `scripts/convert_to_lerobot_pi.py` 里）：

```python
# 旧：state 和 action 各自独立 unwrap
ee_euler_unwrapped = unwrap_euler_sequence(ee_euler)
actions[:, 3:6] = unwrap_euler_sequence(actions[:, 3:6])

# 新：先 unwrap state，把"逐帧累计偏移"应用到 action（action ≈ 下一帧位姿）
ee_euler_unwrapped, offset_per_step = unwrap_euler_sequence_with_offsets(ee_euler)
# 把同一份 offset 序列加到 action euler 上（动作和测量同源，但落后 1 帧）
actions[:, 3:6] = actions[:, 3:6] + offset_per_step
```

外加兜底：在 `transforms.py` 里给 `DeltaActions.__call__` 的输出补一道 `(x+π) % 2π − π`（仅 3:6 维）。但这是 openpi 源码改动，**先报告再做**。

验证脚本（独立小文件，不动 openpi 源码）：

1. 用 numpy 复制 `unwrap_euler_sequence` 和 `DeltaActions` 两个函数
2. 读 HDF5 → 模拟转换链 → 算 delta → 统计 std / q01 / q99
3. 对比"旧 unwrap" vs "新 unwrap（统一基准）" vs "新 unwrap + 兜底归一化" 三组结果
4. 把结果以表格形式贴出来

### Step 3：判断是否值得动手改

只有当 Step 2 证明"修复后 std 降到 0.01~0.06 量级、q01/q99 收敛到 ±0.2 以内"时才继续：

- 在 `convert_to_lerobot_pi.py` 中实现 Step 2 的修复
- 重转一份 lerobot 数据集
- 重算 norm_stats
- 用新数据集训一个 pick_cylinder config（小步数，比如 5000 步）做对照
- 评测端成功率如果显著上升（>60%），就可以进 fix-up 阶段

### Step 4：处理次要问题（**全部可并行，但优先级低**）

这些是之前分析里说过的次要问题，只有当 Step 3 修完后才有意义：

- `pi05_ft_pick_cylinder` 默认 `num_train_steps=100000, batch_size=7` ≈ 20+ epochs over 100 trajectories，**过拟合风险大**。建议压到 3k~5k + 加 EMA
- `peak_lr == decay_lr` 等于不衰减，应改成 `peak_lr=5e-5, decay_lr=5e-6`
- env 端 `_unwrap_ee_state` 与 converter 端 unwrap 是两份独立代码（语义相同），改 converter 时**必须**同步改 env 端，否则会出现"训练和推理分布错位"——更隐蔽的 bug

---

## 5. 不要做的事

- **不要尝试生成新轨迹**。本机没有 VLABench，跑不了 `scripts/trajectory_generation.py`。HDF5 数据足以验证；新轨迹等你下次在那台能跑 VLABench 的机器上做。
- **不要改 openpi 源码的 `transforms.py`**。除非 Step 2 明确证明问题在那里。先做 Step 1、Step 2，再决定。
- **不要修改 `config.py`** 加新 config 或新 config_name。现有的 `pi05_ft_pick_cylinder` 够用，改名会破坏 cache。
- **不要做实际训练**。验证脚本只到"生成 norm_stats + 看 std/q01/q99"为止。训练在那个用 VLABench 的机器上做（你的实验记录里说之前 40-50% 是在那里跑的）。

---

## 6. 关键文件快速跳转

- 怀疑根源（converter）：`/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/scripts/convert_to_lerobot_pi.py:15-33, 134, 146`
- 训练链 delta 实现：`/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/third_party/openpi/src/openpi/transforms.py:217-235`
- norm_stats 计算入口：`/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/third_party/openpi/scripts/compute_norm_stats.py`
- 一键训练脚本：`/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/scripts/model_train/train_pi.py`
- env 端 unwrap（与 converter 同步）：`/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/scihorizon_elab/simulation/envs/dm_env.py:270-286`
- 评测端 action 消费：`/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/scihorizon_elab/benchmark/evaluation/model/policy/openpi.py:113-124`
- 旧 norm_stats 文件（污染证据）：`/mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/third_party/openpi/assets/pi05_ft_pick_cylinder/pick_cylinder_mid_pour_object_series/norm_stats.json`
- arx 对照（无污染）：`/mnt/t_42/huangfuxian/openpi_assets/pi05_arx_deltapose_tube_color_main_wrist_goal_base/tube_color_main_wrist_goal_lerobot/norm_stats.json`

---

## 7. 当前时间线参考

- 2026-09-12：`DeltaActions` 进 elab `config.py`（commit `ea73891` "同步third party"）
- 2026-09-12：`pi05_ft_pick_cylinder` norm_stats 重算（mtime 09-13 15:27，仍显示污染）
- 2026-09-16：用户提问"pi0.5 仿真 40-50% vs arx 80-90%"的根因
- 2026-09-17：补齐 scihorizon_elab 环境的 openpi 依赖

如果用户之前跑的 40-50% 实验**在 2026-09-12 之前**（DeltaActions 进入 config 之前），那是另一层问题（绝对位姿当 target）。这点要从用户那边确认时间，没确认前不要下结论。
