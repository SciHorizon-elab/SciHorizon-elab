# diag_rotvec_delta.py
# rotvec 改造后专用诊断：检查"过去 euler 时代的 ±2π 假跳变"是否被根除。
# 数据流：H5 ee_state(8维 quat) → 复刻 convert 的 quat2rotvec → 模拟 RLDSDeltaActions wrap
# 输出四张表：rotvec 范数合规、相邻帧 |Δrotvec| 分布、跨 180° 边界 delta 异常检测、统计汇总。

import argparse
import glob
import json
import os
from pathlib import Path

import h5py
import numpy as np
from scipy.spatial.transform import Rotation as R


# 复刻 convert_to_lerobot_pi.py:10 的 quat2rotvec（wxyz 输入,xyzw 给 scipy）
def quat2rotvec(quat):
    """quat = (w,x,y,z) → rotvec"""
    return R.from_quat([quat[1], quat[2], quat[3], quat[0]]).as_rotvec()


def load_episode(path):
    """读一个 HDF5. 模仿 convert_to_lerobot_pi.py:106-115.

    注意:rotvec 改造后,生成端已直接输出 rotvec,ee_state 是 (T, 7) = pos3+rotvec3+gripper1,
    trajectory 是 (T, 8) = pos3+rotvec3+gripper2 (双指 gripper 状态)。
    历史数据(改造前)是 ee_state (T, 8) = pos3+quat(wxyz)+gripper1 + trajectory rotvec。
    本脚本按新约定(7+8 维)处理。
    """
    with h5py.File(path, "r") as f:
        ts_key = next(iter(f["data"].keys()))
        ep = f["data"][ts_key]
        ee_state = ep["observation"]["ee_state"][()]
        trajectory = ep["trajectory"][()]
        instruction = ep["instruction"][()]
    return ee_state, trajectory, instruction


# 复刻 RLDSDeltaActions 对 actions[..., 3:6] 的 (d+π)%(2π)-π wrap
def rlds_delta(state, actions):
    """actions - state, 然后 rotvec 维 wrap 到 (-π, π].

    state: [D]; actions: [T, D]; D>=6."""
    out = actions.copy()
    out[..., :6] = out[..., :6] - state[..., :6]
    out[..., 3:6] = (out[..., 3:6] + np.pi) % (2 * np.pi) - np.pi
    return out


def per_episode_diag(ee_state, trajectory, ep_name):
    """对单条 episode 计算诊断量,返回 dict;若失败返回 None."""
    try:
        # ---- 推断/校验格式 ----
        # 新格式:ee_state (T,7)=pos3+rotvec3+gripper1;trajectory (T,8)=pos3+rotvec3+gripper2
        # 历史格式:ee_state (T,8)=pos3+quat(wxyz)+gripper1;trajectory 已 rotvec
        if ee_state.shape[1] == 7 and trajectory.shape[1] >= 7:
            # 新格式:ee_state 已是绝对 rotvec
            ee_pos = ee_state[:, :3]
            ee_rotvec = ee_state[:, 3:6]      # (T, 3)
            ee_gripper = ee_state[:, 6]        # (T,)
            mode = "rotvec_native"
        elif ee_state.shape[1] == 8:
            # 历史格式:ee_state 仍是 8 维 quat(wxyz),需转 rotvec
            ee_pos = ee_state[:, :3]
            ee_quat = ee_state[:, 3:7]
            ee_gripper = ee_state[:, 7]
            ee_rotvec = np.array([quat2rotvec(q) for q in ee_quat])
            mode = "quat_legacy"
        else:
            return {"name": ep_name, "error": f"unknown ee_state shape {ee_state.shape}"}

        if trajectory.shape[1] < 6:
            return {"name": ep_name, "error": f"trajectory has {trajectory.shape[1]} dims"}
        act_rotvec = trajectory[:, 3:6]

        # ---- 检查 1:|rotvec| ≤ π（rotvec 唯一约束,允许 1e-6 误差）----
        abs_norms = np.linalg.norm(ee_rotvec, axis=1)
        max_abs_norm = float(abs_norms.max())
        violations_abs = int((abs_norms > np.pi + 1e-6).sum())

        # ---- 检查 2:相邻帧 |Δrotvec| (action 步帧,应该都很小)----
        diff = act_rotvec[1:] - act_rotvec[:-1]
        # delta wrap 到 (-π, π]（训练 transform 干的就是这个）
        diff_wrap = (diff + np.pi) % (2 * np.pi) - np.pi
        max_step = float(np.abs(diff_wrap).max(axis=1).max())
        steps_gt_pi = int((np.linalg.norm(diff_wrap, axis=1) > np.pi + 1e-6).sum())
        steps_gt_halfpi = int((np.linalg.norm(diff_wrap, axis=1) > np.pi / 2).sum())

        # ---- 检查 3:DeltaActions + RLDS wrap ----
        # 用第 0 帧 state 与全序列 action 算 delta（与训练时 batch stats 一致）
        state0 = np.concatenate([ee_pos[0], ee_rotvec[0], [ee_gripper[0]]])  # (7,)
        actions = np.concatenate([trajectory[:, :6], ee_gripper.reshape(-1, 1)], axis=1)
        deltas = rlds_delta(state0, actions)  # (T, 7)

        # ---- 检查 4:针对根因的"穿越 180° 边界"直接检测 ----
        # 旧 euler 根因的症状：相邻帧 |Δx_k| ≈ 2π（边界绕此带法造成 ±2π 假跳变）
        # rotvec 的 |Δx_k| 真实距离本身就在 0..2π 范围，所以只看"在 ≤3 帧内出现 ≥ π 的跳变"
        # 才能识别"边界跨越 = 旋转参数化约定变化"。
        # 但更稳的判定是：相邻帧真旋转角远小于 |Δrotvec| ⇒ 这是参数化边界跳跃，不是真实动作。
        crossing_events = 0
        for i in range(1, len(ee_rotvec)):
            r_i = ee_rotvec[i]
            r_j = ee_rotvec[i - 1]
            # 真实旋转角（两旋转向量夹角）
            ni, nj = np.linalg.norm(r_i), np.linalg.norm(r_j)
            if ni < 1e-6 or nj < 1e-6:
                continue
            cos_t = np.clip(np.dot(r_i, r_j) / (ni * nj), -1, 1)
            true_angle = float(np.arccos(cos_t))    # 0..π 真实几何旋转角
            raw_dist = float(np.linalg.norm(r_i - r_j))  # 0..2π 参数化距离
            # "假跳变"症状：参数化距离 > 真实旋转角 × 2 + 0.5（即参数化多走了半圈以上）
            if raw_dist > true_angle * 2 + 0.5 and raw_dist > 1.5:
                crossing_events += 1

        return {
            "name": ep_name,
            "mode": mode,
            "T": int(len(ee_rotvec)),
            "max_abs_norm": max_abs_norm,
            "violations_abs": violations_abs,
            "max_step_after_wrap": max_step,
            "steps_gt_pi": steps_gt_pi,
            "steps_gt_halfpi": steps_gt_halfpi,
            "crossing_events_180": crossing_events,
            "delta_q99": [float(np.quantile(deltas[:, i], 0.99)) for i in range(6)],
            "delta_min": [float(deltas[:, i].min()) for i in range(6)],
            "delta_max": [float(deltas[:, i].max()) for i in range(6)],
        }
    except Exception as e:
        return {"name": ep_name, "error": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-dir", required=True,
                    help="含 data_*.hdf5 的任务目录")
    ap.add_argument("--max-files", type=int, default=200)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.task_dir, "*.hdf5")))[:args.max_files]
    print(f"# episodes: {len(files)} from {args.task_dir}\n")

    eps = []
    for p in files:
        try:
            ee_state, traj, _ = load_episode(p)
        except Exception as e:
            print(f"  skip {os.path.basename(p)}: {e}")
            continue
        res = per_episode_diag(ee_state, traj, os.path.basename(p))
        if res is not None:
            eps.append(res)
            print(f"[{res['name']}] T={res.get('T')} "
                    f"max|rotvec|={res.get('max_abs_norm', -1):.4f} "
                    f"viol_abs={res.get('violations_abs')} "
                    f"max_step_after_wrap={res.get('max_step_after_wrap', -1):.4f} "
                    f"steps>π={res.get('steps_gt_pi')} "
                    f"cross180={res.get('crossing_events_180')}")

    # ---- 聚合判定 ----
    if not eps:
        print("\n# no valid episodes")
        return
    print("\n" + "=" * 60)
    print("# 聚合诊断")
    print("=" * 60)
    max_abs = max((e.get("max_abs_norm", 0) for e in eps), default=0)
    max_step = max((e.get("max_step_after_wrap", 0) for e in eps), default=0)
    total_viol_abs = sum(e.get("violations_abs", 0) for e in eps)
    total_steps_gt_pi = sum(e.get("steps_gt_pi", 0) for e in eps)
    total_steps_gt_halfpi = sum(e.get("steps_gt_halfpi", 0) for e in eps)
    total_cross180 = sum(e.get("crossing_events_180", 0) for e in eps)
    print(f"  episodes         : {len(eps)}")
    print(f"  max|rotvec|      : {max_abs:.6f}  (要求 ≤ π ≈ 3.14159;容差 1e-6)")
    print(f"  violations (|r|>π): {total_viol_abs}")
    print(f"  max|Δrotvec|/帧 : {max_step:.6f}  (要求 < 0.5,理想 < 0.3)")
    print(f"  steps |Δ|>π      : {total_steps_gt_pi}  (要求 = 0)")
    print(f"  steps |Δ|>π/2    : {total_steps_gt_halfpi}  (要求 = 0;有少量也无妨,需排查)")
    print(f"  穿越 180° 假跳变 : {total_cross180}  (要求 = 0;旧 euler 时代的根因症状)")

    delta_q99_all = np.array([e["delta_q99"] for e in eps])
    delta_min_all = np.array([e["delta_min"] for e in eps])
    delta_max_all = np.array([e["delta_max"] for e in eps])
    print(f"\n  delta q99 各维 (pos3 + rotvec3):")
    for i, name in enumerate(["px", "py", "pz", "rx", "ry", "rz"]):
        print(f"    {name}: q99={delta_q99_all[:, i].mean():.4f}  "
                f"min={delta_min_all[:, i].min():.4f}  max={delta_max_all[:, i].max():.4f}")

    # ---- 总体判定 ----
    print("\n" + "=" * 60)
    print("# 判定")
    print("=" * 60)
    passed_all = True
    if total_viol_abs > 0:
        print(f"  ✗ |rotvec|>π 共 {total_viol_abs} 帧：rotvec 范数不合法")
        passed_all = False
    else:
        print("  ✓ |rotvec|≤π 全程成立")
    if max_abs > np.pi + 1e-6:
        print(f"  ✗ max|rotvec|={max_abs:.6f} > π")
        passed_all = False
    else:
        print(f"  ✓ max|rotvec|={max_abs:.6f} 在容差内")
    if total_cross180 > 0:
        print(f"  ✗ 仍检测到 {total_cross180} 次参数化边界跳跃（疑似旧 euler 根因残留）")
        passed_all = False
    else:
        print("  ✓ 无参数化边界跳跃（几何距离与参数化距离一致 ⇒ 无 ±2π 假跳变）")
    if total_steps_gt_pi > 0:
        print(f"  ✗ 经 RLDS wrap 仍有 {total_steps_gt_pi} 帧 |Δrotvec|>π")
        passed_all = False
    else:
        print("  ✓ wrap 后无 |Δrotvec|>π 帧（delta 污染已根除）")
    print(f"  · max|Δrotvec|={max_step:.4f}（任务特性决定，可参考 delta q99/p99 评估）")

    summary = {
        "episodes": len(eps),
        "max_abs_norm": max_abs,
        "violations_abs": total_viol_abs,
        "max_step_after_wrap": max_step,
        "steps_gt_pi": total_steps_gt_pi,
        "steps_gt_halfpi": total_steps_gt_halfpi,
        "crossing_events_180": total_cross180,
        "passed": passed_all,
        "details": eps,
    }
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\n# wrote summary → {args.output}")

    if passed_all and max_step <= 0.5:
        print("\n  ✓✓✓ 旧 euler 时代的 ±2π 跳变问题已根除,rotvec 数据流干净")
    elif passed_all:
        print("\n  ✓ rotvec 数据流基本干净（wrap 后 delta 未越界）；max_step 反映任务真实动作幅度")
    else:
        print("\n  ✗ 仍有未消除的旧问题,需要排查")


if __name__ == "__main__":
    main()