# diag_delta_distribution.py
# 独立诊断脚本：对比"旧 unwrap / 新 unwrap / 新 unwrap + 兜底归一化" 三组数据下
# actions delta 维度的污染程度。不依赖 openpi 任何模块，纯 numpy + h5py。

import argparse
import glob
import json
import os
from pathlib import Path

import h5py
import numpy as np
from scipy.spatial.transform import Rotation as R

# --- 复制自 /mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/scripts/convert_to_lerobot_pi.py ---
def quat2euler(quat, is_degree=False):
    r = R.from_quat([quat[1], quat[2], quat[3], quat[0]])
    return r.as_euler('xyz', degrees=is_degree)


def unwrap_euler_sequence(euler_seq):
    """原 converter 的实现：逐维独立，相邻帧差 >π 时对后续整段累加 ∓2π。"""
    seq = np.asarray(euler_seq, dtype=np.float64).copy()
    for k in range(seq.shape[1]):
        for i in range(1, len(seq)):
            d = seq[i, k] - seq[i - 1, k]
            if d > np.pi:
                seq[i:, k] -= 2 * np.pi
            elif d < -np.pi:
                seq[i:, k] += 2 * np.pi
    return seq


def unwrap_euler_with_offsets(euler_seq):
    """新实现：除 unwrap 后的序列外，额外返回"逐帧累计偏移"。

    把偏移序列加到 action euler 上即可实现"两条序列同分支"。"""
    seq = np.asarray(euler_seq, dtype=np.float64).copy()
    offset = np.zeros_like(seq)
    for k in range(seq.shape[1]):
        for i in range(1, len(seq)):
            d = seq[i, k] - seq[i - 1, k]
            if d > np.pi:
                delta = -2 * np.pi
            elif d < -np.pi:
                delta = 2 * np.pi
            else:
                delta = 0.0
            seq[i:, k] += delta
            offset[i:, k] += delta
    return seq, offset


# --- 复制自 openpi transforms.py (DeltaActions) ---
def delta_actions(state, actions, mask_first6=True):
    """actions - state，前 6 维；gripper 保持原值。

    state: [D], actions: [T, D]"""
    out = actions.copy()
    dims = 6 if mask_first6 else actions.shape[-1]
    out[..., :dims] -= state[..., :dims]
    return out


def wrap_pi(x):
    """(-π, π] 归一化，仅作用于 euler 维（3:6）。"""
    out = x.copy()
    out[..., 3:6] = (out[..., 3:6] + np.pi) % (2 * np.pi) - np.pi
    return out


def stats(arr, name=""):
    """打印一组数组的关键统计量。"""
    print(f"  {name}: shape={arr.shape} mean={arr.mean():+.4f} std={arr.std():.4f} "
          f"q01={np.quantile(arr, 0.01):+.4f} q99={np.quantile(arr, 0.99):+.4f} "
          f"min={arr.min():+.4f} max={arr.max():+.4f}")


def load_hdf5_episode(path):
    """加载一个 HDF5 episode，返回 (state[T, 7], actions[T, 7])。

    state = ee_state (pos3 + euler3 + gripper1)，已 unwrap
    actions = trajectory (pos3 + euler3 + gripper2)，这里只取最后一维 gripper
    """
    with h5py.File(path, "r") as f:
        ts_key = next(iter(f["data"].keys()))
        ep = f["data"][ts_key]
        ee_state = ep["observation"]["ee_state"][()]
        traj = ep["trajectory"][()]
    # 取 min 长度对齐（converter 同样处理）
    L = min(len(ee_state), len(traj))
    ee_state, traj = ee_state[:L], traj[:L]

    pos, quat, gripper = ee_state[:, :3], ee_state[:, 3:7], ee_state[:, 7]
    ee_euler = np.array([quat2euler(q) for q in quat])

    # pos 转 robot 帧（与 converter 一致）
    pos_robot = pos - np.array([0.0, -0.4, 0.78])

    # 原始 euler 序列（未 unwrap）
    raw_state_euler = ee_euler.copy()
    raw_act_euler = traj[:, 3:6].copy()

    state = np.concatenate([pos_robot, ee_euler, gripper.reshape(-1, 1)], axis=1)
    # actions: 只取 gripper 第一维（与 converter 一致——binarize 阈值那里取 actions[i][-1]）
    actions = np.concatenate([traj[:, :6], gripper.reshape(-1, 1)], axis=1)
    return state, actions, raw_state_euler, raw_act_euler


def compute_pipeline(state_raw, actions_raw, mode):
    """按 mode 走完整转换链，返回 actions delta（用于 norm_stats 输入）。"""
    # mode: 'old' / 'new_offset' / 'new_offset_wrap'
    # 原始 euler 序列（state 和 actions 的）
    state_pos = state_raw[:, :3]
    state_euler_raw = state_raw[:, 3:6]
    state_grip = state_raw[:, 6:7]

    if mode == "old":
        state_euler = unwrap_euler_sequence(state_euler_raw)
        act_euler = unwrap_euler_sequence(actions_raw[:, 3:6])
    elif mode in ("new_offset", "new_offset_wrap"):
        # 关键：用 state 的偏移序列去 align action（action 是下一帧位姿，与 state 同源）
        state_euler, offset = unwrap_euler_with_offsets(state_euler_raw)
        # action 的 euler += 同一份偏移（state 是 t 帧，action 是 t→t+1）
        # 为简化：actions[:, 3:6] 与 state[:, 3:6] 同分支，对齐偏移
        act_euler = actions_raw[:, 3:6] + offset
    else:
        raise ValueError(mode)

    state_new = np.concatenate([state_pos, state_euler, state_grip], axis=1)
    actions_new = actions_raw.copy()
    actions_new[:, 3:6] = act_euler

    # DeltaActions：actions - state，前 6 维
    deltas = delta_actions(state_new[0], actions_new)  # state[0] 是 episode 第一帧

    if mode == "new_offset_wrap":
        deltas = wrap_pi(deltas)
    return state_new, actions_new, deltas


def collect_deltas(hdf5_files, mode):
    all_deltas = []
    states_first = []
    for p in hdf5_files:
        try:
            state_raw, actions_raw, _, _ = load_hdf5_episode(p)
        except Exception as e:
            print(f"  skip {os.path.basename(p)}: {e}")
            continue
        state_new, _, deltas = compute_pipeline(state_raw, actions_raw, mode)
        all_deltas.append(deltas)
        states_first.append(state_new[0])
    if not all_deltas:
        return None, None
    return np.concatenate(all_deltas, axis=0), np.stack(states_first, axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-dir", required=True,
                    help="包含 data_*.hdf5 的任务目录，如 /mnt/t_52/qinmaokai/workspace/SciHorizon-ELAB/dataset/autogen_tasks/1_pour_beaker_into_beaker")
    ap.add_argument("--max-files", type=int, default=50)
    ap.add_argument("--output", default=None, help="可选，输出 JSON 到指定路径")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.task_dir, "*.hdf5")))[:args.max_files]
    print(f"# tasks: {len(files)} files from {args.task_dir}\n")

    summary = {}
    for mode in ["old", "new_offset", "new_offset_wrap"]:
        print(f"\n===== mode = {mode} =====")
        deltas, states = collect_deltas(files, mode)
        if deltas is None:
            print("  no data")
            continue
        print(f"  total samples: {deltas.shape[0]}")
        for i in range(7):
            stats(deltas[:, i], f"actions[{i}]")
        for i in range(7):
            stats(states[:, i], f"state[0][{i}] (first frame per episode)")
        summary[mode] = {
            "actions_std_per_dim": deltas.std(axis=0).tolist(),
            "actions_q01_per_dim": np.quantile(deltas, 0.01, axis=0).tolist(),
            "actions_q99_per_dim": np.quantile(deltas, 0.99, axis=0).tolist(),
            "actions_mean_per_dim": deltas.mean(axis=0).tolist(),
        }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\n# wrote summary → {args.output}")

    # 关键判定
    print("\n===== 判定 =====")
    old = summary["old"]["actions_std_per_dim"]
    new = summary["new_offset"]["actions_std_per_dim"]
    wrap = summary["new_offset_wrap"]["actions_std_per_dim"]
    print(f"  roll 维 (index 3) std:")
    print(f"    old            = {old[3]:.4f}")
    print(f"    new_offset     = {new[3]:.4f}  (降低 {(1 - new[3]/old[3])*100:.1f}%)")
    print(f"    new_offset_wrap= {wrap[3]:.4f}")
    if new[3] < 0.1 and wrap[3] < 0.1:
        print("  ✓ 假设得到证实：新 unwrap 能把 roll 维 std 降到 arx 量级（< 0.1）")
    elif new[3] >= 1.0:
        print("  ✗ 假设不成立：即使统一 unwrap，roll 维 std 仍然异常大")
    else:
        print(f"  ? 不确定：std 从 {old[3]:.2f} 降到 {new[3]:.2f}，可能部分成立，需要看更多任务")


if __name__ == "__main__":
    main()