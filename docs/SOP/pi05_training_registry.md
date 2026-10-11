# 训练注册表（持续维护）

> **目的**：记录每次训练的完整配置 + 评测结果，沉淀"任务 × 配置 → 成功率"的最优参数经验。
>
> **维护约定**：
> - **一行 = 一次训练**；同 run 的多个 checkpoint 各占一行（配置全同、仅步数不同，评测过的中间 ckpt 也要记入）
> - 每启动一次训练就新增一行；每次评测更新对应行的"成功率"格
> - 训练中途未跑完的 run 不入主表
> - 不确定的字段写 `TBD`，不瞎填
> - 评测代码有行为变更时在备注注明
>
> **epoch 计算口径**：
> - ACT: `steps × batch_size / total_frames`（lerobot 默认；ACT 训练日志中 `epch:` 字段就是该值）
> - pi0.5: `steps × batch_size / num_samples`（其中 num_samples = frames - (action_horizon - 1) = frames - 9，action_horizon=10）
> - xlsx 中的 loss/成功率/训练时长 优先于之前表格中的值；xlsx 未覆盖的字段仍标 TBD

---

## 任务短名映射

| 任务全名 | 短名 |
|---|---|
| place_beaker_1 | beaker1 |
| place_beaker_2 | beaker2 |
| place_beaker_3 | beaker3 |

---

## 主表

| ���型名 | 任务 | 日期 | 模型基座 | 训练轨迹数 | 图像分辨率 | 训练范式 | 微调方式 | GlobalBatch | steps | epoch | warmup 步数 | LR | EMA | Loss | 显卡配置 | 成功率 | 训练时长 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| act_beaker1_25k | beaker1 | 08-10 | ResNet18-IN | 50eps | 256×256 | 预训初 | 全参 | 128 | 25k | 530.59 | 0 | 1.0E-05 恒定 | 无 | 0.0248 | 1×A800 | 40% (4/10) | ~1.5h | LR恒定无scheduler；小随机范围+有随机扰动；存在unwrap问题 |
| act_beaker1_50k | beaker1 | 08-10 | ResNet18-IN | 50eps | 256×256 | 预训初 | 全参 | 128 | 50k | 1061.18 | 0 | 1.0E-05 恒定 | 无 | 0.0168 | 1×A800 | 80% (8/10) | 3h04m | LR恒定无scheduler；小随机范围+有随机扰动；存在unwrap问题 |
| act_beaker2_25k | beaker2 | 08-10 | ResNet18-IN | 50eps | 256×256 | 预训初 | 全参 | 128 | 25k | 493.14 | 0 | 1.0E-05 恒定 | 无 | 0.0232 | 1×A800 | 40% (4/10) | ~1.5h | LR恒定无scheduler；大随机范围+有随机扰动；存在unwrap问题 |
| act_beaker2_50k | beaker2 | 08-10 | ResNet18-IN | 50eps | 256×256 | 预训初 | 全参 | 128 | 50k | 986.28 | 0 | 1.0E-05 恒定 | 无 | 0.0172 | 1×A800 | 40% (4/10) | 3h05m | LR恒定无scheduler；大随机范围+有随机扰动；存在unwrap问题 |
| act_beaker3_25k | beaker3 | 08-10 | ResNet18-IN | 51eps | 256×256 | 预训初 | 全参 | 128 | 25k | 516.13 | 0 | 1.0E-05 恒定 | 无 | 0.0237 | 1×A800 | 50% (4/10) | ~1.5h | LR恒定无scheduler；小随机范围+无随机扰动；存在unwrap问题 |
| act_beaker3_50k | beaker3 | 08-10 | ResNet18-IN | 51eps | 256×256 | 预训初 | 全参 | 128 | 50k | 1032.26 | 0 | 1.0E-05 恒定 | 无 | 0.0135 | 1×A800 | **90% (9/10)** | 3h05m | 当前最优 ACT；LR恒定无scheduler；小随机范围+无随机扰动；存在unwrap问题 |
| pi05_beaker3_v3_20k | beaker3 | 08-26 | pi05_base | 105eps | 480×480 | LoRA | r16/r32 | 128 | 20k | 201.37 | 1k | 5.00E-05 峰值 | 无 | 6.5088 | 8×A800 | **66.7% (20/30)** | 2h2m | 数据已做 euler unwrap 修复；无 EMA；LR cosine（peak 后≈恒定）；评测端 unwrap 三版本对照（无 60.0% / policy端 73.3% / env端 66.7%，p>0.15不显著）；失败主因=夹碰杯口；无 DR。注：此处 66.7% 为 env端 30ep 单轮口径，未合并 50ep (58.0%) |
| pi05_beaker3_v4_10k | beaker3 | 08-27 | pi05_base | 105eps | 224×224 | LoRA | r16/r32 | 256 | 10k | 201.37 | 1k | 5.00E-05 峰值 | 0.999 | 0.576 | 4×A800 | 63.3% (19/30) | ~4.5h | v4甜点步数；数据预缩224；LR cosine；EMA 0.999 对齐官方 |
| pi05_beaker3_v4_20k | beaker3 | 08-27 | pi05_base | 105eps | 224×224 | LoRA | r16/r32 | 256 | 20k | 402.74 | 1k | 5.00E-05 峰值 | 0.999 | 0.4204 | 4×A800 | 43.3% (13/30) | ~9h | 较10k反降20pp；首次评测遇 server keepalive hang（NaN），重启后复测有效 |
| pi05_beaker3_v4_30k | beaker3 | 08-27 | pi05_base | 105eps | 224×224 | LoRA | r16/r32 | 256 | 30k | 604.11 | 1k | 5.00E-05 峰值 | 0.999 | 0.0454 | 4×A800 | 23.3% (7/30) | 13h43m | v4最差；10k→20k→30k 单调下降；EMA0.999+b256+小数据越训越差 |
| pi05_beaker3_v5_10k | beaker3 | 08-28 | pi05_base | 105eps | 224×224 | LoRA | r16/r32 | 128 | 10k | 100.68 | 1k | 5.00E-05 峰值 | 无 | 4.018 | 4×A800 | 50.0% (15/30) | ~2.6h | v5 = v4 配置去掉 EMA，b256→b128（其他同v4）；loss仍高 |
| pi05_beaker3_v5_20k | beaker3 | 08-28 | pi05_base | 105eps | 224×224 | LoRA | r16/r32 | 128 | 20k | 201.37 | 1k | 5.00E-05 峰值 | 无 | 2.107 | 4×A800 | 43.3% (13/30) | ~5.2h | 较10k反降 |
| pi05_beaker3_v5_30k | beaker3 | 08-28 | pi05_base | 105eps | 224×224 | LoRA | r16/r32 | 128 | 30k | 302.05 | 1k | 5.00E-05 峰值 | 无 | 0.84 | 4×A800 | 3.3% (1/30) | 7h43m | v5最差；loss虽降至0.84但成功率崩至3.3%，疑似过拟合 |

---

## 参考对照行（不计入训练统计）

| 模型名 | 任务 | 日期 | 模型基座 | 训练轨迹数 | 图像分辨率 | 训练范式 | 微调方式 | GlobalBatch | steps | epoch | warmup 步数 | LR | EMA | Loss | 显卡配置 | 成功率 | 训练时长 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| pi05_libero | LIBERO-Spatial | —— | pi05_base | 1,693 eps (273,465帧, 40任务) | 224×224 | 行为克隆+Flow Matching | 全参数微调 | 256 | 30k | TBD（需 action_horizon 数据） | 10k | 保持5.00E-05 | 0.999 | 未披露 | —— | 98.8% | —— | 官方 checkpoint；action horizon=10，AdamW，梯度裁剪1.0；官方未公布最终loss/卡数/时长 |

---

## 评测明细表

> 同一 checkpoint 换评测代码/口径重测时记录于此，主表只放最终采用口径。

| 模型名 | 评测口径 | n | 成功率 | 备注 |
|---|---|---|---|---|
| pi05_beaker3_v3_20k | 早期试跑（小样本） | 10 | 80% | |
| pi05_beaker3_v3_20k | 无unwrap | 30 | 60.0% | unwrap 对照实验 |
| pi05_beaker3_v3_20k | policy端unwrap | 30 | 73.3% | unwrap 对照实验 |
| pi05_beaker3_v3_20k | env端unwrap | 30 | 66.7% | unwrap 对照实验（主表采纳） |
| pi05_beaker3_v3_20k | env端unwrap | 50 | 58.0% | 与30ep合并得61.3%(49/80) |
| pi05_beaker3_v3_20k | 早期测试（test_log） | 5 | 0% | n=5 太低不参考 |
| pi05_beaker3_v3_20k | 早期测试2 | 5 | 0% | n=5 太低不参考 |
| pi05_beaker3_v4_20k | 首次遇server hang（NaN） | 30 | NaN | server重启后复测有效，不入主表 |
| dp_beaker3_50k | DP v1 | 10 | 0% | DP config v1 |
| dp_beaker3_50k | DP v2 | 10 | 20% | DP config v2 |
| dp_beaker3_50k | DP v3 | 10 | 20% | DP config v3 |

---

## Checkpoint 路径索引

| 模型名 | 路径 |
|---|---|
| act_beaker1_25k | `lerobot/outputs/train/2026-08-10/act_place_beaker_1/checkpoints/025000/pretrained_model` |
| act_beaker1_50k | `lerobot/outputs/train/2026-08-10/act_place_beaker_1/checkpoints/050000/pretrained_model` |
| act_beaker2_25k | `lerobot/outputs/train/2026-08-10/act_place_beaker_2/checkpoints/025000/pretrained_model` |
| act_beaker2_50k | `lerobot/outputs/train/2026-08-10/act_place_beaker_2/checkpoints/050000/pretrained_model` |
| act_beaker3_25k | `lerobot/outputs/train/2026-08-10/act_place_beaker_3/checkpoints/025000/pretrained_model` |
| act_beaker3_50k | `lerobot/outputs/train/2026-08-10/act_place_beaker_3/checkpoints/050000/pretrained_model` |
| pi05_beaker3_v3_20k | `third_party/openpi/checkpoints/pi05_ft_place_beaker_3_v3/pi05_ft_place_beaker_3_v3_20k_b128/19999` |
| pi05_beaker3_v3_10k | `third_party/openpi/checkpoints/pi05_ft_place_beaker_3_v3/pi05_ft_place_beaker_3_v3_20k_b128/10000`（未评测） |
| pi05_beaker3_v4_10k | `third_party/openpi/checkpoints/pi05_ft_place_beaker_3_v4/pi05_ft_place_beaker_3_v4_30k_b256_ema/10000` |
| pi05_beaker3_v4_20k | `third_party/openpi/checkpoints/pi05_ft_place_beaker_3_v4/pi05_ft_place_beaker_3_v4_30k_b256_ema/20000` |
| pi05_beaker3_v4_30k | `third_party/openpi/checkpoints/pi05_ft_place_beaker_3_v4/pi05_ft_place_beaker_3_v4_30k_b256_ema/29999` |

---

## 阶段结论

1. **当前 ACT 最优**：act_beaker3_50k = 90% (n=10, epoch=1032)
2. **当前 pi0.5 最优**：pi05_beaker3_v3_20k = 66.7% (n=30, epoch=201.37)；多轮合并口径=61.3% (n=80)
3. **epoch 量级对比**：ACT 50k ≈ 1000+ epoch（极度过拟合区间），pi0.5 v3 20k ≈ 200 epoch——两者训练强度不可同日而语，但 ACT 在 beaker3 上仍凭更高 epoch 拿到 90%。可能原因：ACT 数据 51 eps / 6200 帧（极小，1 epoch 看完整数据集仅需 50 步），pi0.5 数据 105 eps / 12722 帧（2 倍大）
4. **小数据集训练经验**：b256+EMA0.999 在 105 eps 上越训越差（v4 三档单降），b128+无 EMA 在 v3/v5 上也不同表现
5. **unwrap 修复**：评测端 unwrap 对成功率无可测量影响
6. **涨点方向**：失败模式单一 → 优先扩充数据/开启 DR，而非继续调超参
7. **统计纪律**：n<30 的结果只做参考

---

## 待补全字段（缺信息源）

- pi05_libero 的 epoch（需 LIBERO 数据集帧数 + action_horizon 推算）
- pi05_beaker3 各 checkpoint 的训练时长目前来自 xlsx（2h2m / 4.5h / 9h / 13h43m / 2.6h / 5.2h / 7h43m），本地无训练日志交叉验证