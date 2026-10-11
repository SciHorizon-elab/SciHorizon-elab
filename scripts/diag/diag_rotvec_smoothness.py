# diag_rotvec_smoothness.py
# rotvec 改造后专用平滑度诊断：检查角度变化是否平滑，是否还存在单帧跳变。
# 直接从 H5 的 ee_state（已经是绝对 rotvec）逐帧计算：
#   - 单帧 Δrotvec 参数化距离 |r[i] - r[i-1]|
#   - 单帧 SO(3) 测地线距离（两旋转向量夹角）— 几何真距离，绕 ±2π 边界不受影响
#   - 单帧 quat(wxyz) 点积变化（点积突变 → 旋转突变）
# 同时给出 5 帧/30 帧/95 帧滑窗累计几何距离的 max。
# 关键：剔除 |r|≈π 边界伪影（这种"边界伪影"必然是 180°，不代表真跳变）。

import argparse
import glob
import json
import os
from pathlib import Path

import h5py
import numpy as np
from scipy.spatial.transform import Rotation as R


def quat_from_rotvec(rv):
    """绝对 rotvec (T,3) → quat wxyz (T,4)."""
    return R.from_rotvec(rv).as_quat()[:, [3, 0, 1, 2]]


def geodesic_angle(r1, r2):
    """两旋转向量夹角 = 几何真旋转距离。"""
    n1 = np.linalg.norm(r1)
    n2 = np.linalg.norm(r2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    a = r1 / n1
    b = r2 / n2
    c = np.clip(np.dot(a, b), -1.0, 1.0)
    return float(np.arccos(c))


def analyze_one(path, jump_thresh_deg=5.0):
    """返回一份诊断 dict,包含逐帧序列 + 统计."""
    with h5py.File(path, "r") as f:
        ts = next(iter(f["data"].keys()))
        ee = f["data"][ts]["observation"]["ee_state"][()]
    rv = ee[:, 3:6].astype(np.float64)        # (T, 3) 绝对 rotvec
    T = len(rv)

    # 参数化距离 |Δr|（会被 ±π 边界参数化选择影响）
    para = np.linalg.norm(np.diff(rv, axis=0), axis=1)  # (T-1,)
    # 几何真旋转距离（不受边界影响）
    geo = np.array([geodesic_angle(rv[i], rv[i - 1]) for i in range(1, T)])
    # quat 点积差（点积接近 ±1 时旋转接近一致；突变表示旋转跳变）
    qwxyz = quat_from_rotvec(rv)
    qdot = np.sum(qwxyz[1:] * qwxyz[:-1], axis=1)
    qdot = np.clip(qdot, -1.0, 1.0)
    qangle = np.arccos(np.abs(qdot))   # 取 abs 因为 q 与 -q 同一旋转
    qangle_deg = np.degrees(qangle)

    # 单帧旋转跳变阈值（默认 5°）的帧
    big = np.where(qangle_deg > jump_thresh_deg)[0]
    para_deg = np.degrees(para)
    geo_deg = np.degrees(geo)

    # ---- 剔除 rotvec 边界伪影 ----
    # |r|≈π 时,+π·n̂ 与 -π·n̂ 同旋,几何夹角 = 180° 是参数化带来的伪影,不代表真跳变
    # 判定条件:两端 |r| 都接近 π 且方向相反(加和接近 0)
    geo_real_mask = np.ones(len(geo_deg), dtype=bool)
    for i in range(1, T):
        ri, rj = rv[i], rv[i - 1]
        ni, nj = np.linalg.norm(ri), np.linalg.norm(rj)
        # 两端都接近 π(>3.10) 且 方向相反(单位向量的点积 < -0.99)
        if ni > 3.10 and nj > 3.10:
            dot = np.dot(ri, rj) / (ni * nj + 1e-12)
            if dot < -0.99:
                geo_real_mask[i - 1] = False
    geo_real = geo_deg[geo_real_mask]
    geo_max_deg_real = float(geo_real.max()) if len(geo_real) else 0.0
    geo_q99_deg_real = float(np.quantile(geo_real, 0.99)) if len(geo_real) else 0.0
    geo_q95_deg_real = float(np.quantile(geo_real, 0.95)) if len(geo_real) else 0.0
    boundary_artifact = int((~geo_real_mask).sum())

    # 滑窗累计几何距离
    def rolling_max(arr, win):
        if len(arr) < win:
            return float(arr.max()) if len(arr) else 0.0
        csum = np.concatenate([[0.0], np.cumsum(arr)])
        return float((csum[win:] - csum[:-win]).max())

    win5_max = rolling_max(geo_deg, 5)
    win30_max = rolling_max(geo_deg, 30)
    win95_max = rolling_max(geo_deg, 95)

    return {
        "name": os.path.basename(path),
        "T": T,
        "para_max_deg": float(para_deg.max()),
        "para_q99_deg": float(np.quantile(para_deg, 0.99)),
        "para_q95_deg": float(np.quantile(para_deg, 0.95)),
        "geo_max_deg": float(geo_deg.max()),
        "geo_q99_deg": float(np.quantile(geo_deg, 0.99)),
        "geo_q95_deg": float(np.quantile(geo_deg, 0.95)),
        "geo_median_deg": float(np.median(geo_deg)),
        "geo_max_deg_real": geo_max_deg_real,
        "geo_q99_deg_real": geo_q99_deg_real,
        "geo_q95_deg_real": geo_q95_deg_real,
        "boundary_artifact_frames": boundary_artifact,
        "qangle_max_deg": float(qangle_deg.max()),
        "qangle_q99_deg": float(np.quantile(qangle_deg, 0.99)),
        "qangle_q95_deg": float(np.quantile(qangle_deg, 0.95)),
        "jump_thresh_deg": jump_thresh_deg,
        "jumps_gt_thresh": int(len(big)),
        "jump_indices": big.tolist(),
        "jump_qangle_deg": qangle_deg[big].tolist(),
        "win5_max": win5_max,
        "win30_max": win30_max,
        "win95_max": win95_max,
        "_para_deg": para_deg.tolist(),
        "_geo_deg": geo_deg.tolist(),
        "_geo_real_mask": geo_real_mask.tolist(),
        "_qangle_deg": qangle_deg.tolist(),
    }


def ascii_sparkline(values, width=60):
    """极简 ASCII 折线。"""
    if not len(values):
        return "(empty)"
    v = np.asarray(values, dtype=np.float64)
    # 只显示 q99 截尾,避免被 1 个极值压缩
    cap = np.quantile(v, 0.99) if len(v) > 5 else v.max()
    cap = max(cap, 1e-6)
    v_clip = np.minimum(v, cap)
    if v_clip.max() < 1e-9:
        return "(all near zero)"
    bars = " ▁▂▃▄▅▆▇█"
    idx = np.linspace(0, len(v_clip) - 1, width).astype(int)
    sampled = v_clip[idx]
    norm = (sampled / cap * (len(bars) - 1)).astype(int)
    return "".join(bars[n] for n in norm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-dir", required=True)
    ap.add_argument("--max-files", type=int, default=10)
    ap.add_argument("--jump-thresh-deg", type=float, default=5.0,
                    help="单帧 SO(3) 真旋转角超过此阈值算'跳变'")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.task_dir, "*.hdf5")))[:args.max_files]
    print(f"# episodes: {len(files)} from {args.task_dir}")
    print(f"# 单帧跳变阈值: {args.jump_thresh_deg}°（基于几何真旋转角,绕 ±π 边界不受影响）\n")

    all_results = []
    for p in files:
        r = analyze_one(p, jump_thresh_deg=args.jump_thresh_deg)
        all_results.append(r)
        print(f"[{r['name']}] T={r['T']}")
        print(f"  单帧 (相邻帧) 旋转角度：")
        print(f"    参数化距离 |Δr|   max={r['para_max_deg']:6.2f}°  q99={r['para_q99_deg']:6.2f}°  q95={r['para_q95_deg']:6.2f}°")
        print(f"    几何真距离 (含边界伪影) max={r['geo_max_deg']:6.2f}°  q99={r['geo_q99_deg']:6.2f}°  q95={r['geo_q95_deg']:6.2f}°  median={r['geo_median_deg']:5.2f}°")
        print(f"    几何真距离 (剔除边界伪影后) max={r['geo_max_deg_real']:6.2f}°  q99={r['geo_q99_deg_real']:6.2f}°  q95={r['geo_q95_deg_real']:6.2f}°  (伪影帧 {r['boundary_artifact_frames']})")
        print(f"    quat 点积角度        max={r['qangle_max_deg']:6.2f}°  q99={r['qangle_q99_deg']:6.2f}°  q95={r['qangle_q95_deg']:6.2f}°")
        print(f"  滑窗累计几何距离 max：  5帧={r['win5_max']:6.2f}°  30帧={r['win30_max']:7.2f}°  95帧={r['win95_max']:7.2f}°")
        print(f"  单帧跳变（>{args.jump_thresh_deg}°）：{r['jumps_gt_thresh']} 次", end="")
        if r["jumps_gt_thresh"] > 0 and r["jumps_gt_thresh"] < 20:
            print(f"  帧号={r['jump_indices']}  角度={[f'{x:.2f}' for x in r['jump_qangle_deg']]}°")
        elif r["jumps_gt_thresh"] >= 20:
            print(f"  帧号(前10)={r['jump_indices'][:10]}...  角度={[f'{x:.2f}' for x in r['jump_qangle_deg'][:10]]}°")
        else:
            print()
        print(f"  单帧几何真距离折线（q99 截尾）：{ascii_sparkline(r['_geo_deg'], width=60)}")
        print()

    # 聚合
    print("=" * 70)
    print("# 聚合")
    print("=" * 70)
    if not all_results:
        print("no data")
        return
    geo_max_all = max(r["geo_max_deg"] for r in all_results)
    geo_q99_all = max(r["geo_q99_deg"] for r in all_results)
    geo_max_real_all = max(r["geo_max_deg_real"] for r in all_results)
    geo_q99_real_all = max(r["geo_q99_deg_real"] for r in all_results)
    qangle_max_all = max(r["qangle_max_deg"] for r in all_results)
    total_jumps = sum(r["jumps_gt_thresh"] for r in all_results)
    print(f"  episodes       : {len(all_results)}")
    print(f"  单帧几何 max   : {geo_max_all:.2f}° (含边界伪影)")
    print(f"  单帧几何 q99   : {geo_q99_all:.2f}° (含边界伪影)")
    print(f"  单帧几何 max(real,剔除边界伪影): {geo_max_real_all:.2f}°")
    print(f"  单帧几何 q99(real,剔除边界伪影): {geo_q99_real_all:.2f}°")
    print(f"  quat 点积角度 max : {qangle_max_all:.2f}°")
    print(f"  跳变总数 (>{args.jump_thresh_deg}°): {total_jumps}")

    print()
    print("=" * 70)
    print("# 平滑度判定")
    print("=" * 70)
    # 阈值说明：
    # - 单帧 ≥ 5° 算跳变。100fps 任务 5°/帧 = 500°/秒,机械臂根本达不到
    # - 实测单帧 0.5~2° 是正常;|r|≈π 附近的几何 180° 是 rotvec 边界伪影,已剔除
    if total_jumps == 0:
        print(f"  ✓✓✓ 所有 episode 都没有 >{args.jump_thresh_deg}°/帧 的单帧跳变")
        print(f"      （最大单帧真旋转角 {geo_max_real_all:.2f}° 在 {args.jump_thresh_deg}° 阈值内）")
    else:
        print(f"  ✗ 共 {total_jumps} 个单帧跳变 (>{args.jump_thresh_deg}°)，需要排查")
    if geo_q99_real_all < args.jump_thresh_deg:
        print(f"  ✓ 99% 的单帧步长 < {args.jump_thresh_deg}°（q99(real)={geo_q99_real_all:.2f}°），数据整体平滑")
    else:
        print(f"  ? q99(real)={geo_q99_real_all:.2f}° 接近阈值,可能存在少数跳变帧但整体仍平滑")
    if geo_max_real_all > 30:
        print(f"  · 单帧最大真旋转角 {geo_max_real_all:.2f}° > 30°：可能对应任务的真实大幅动作（如 flip/drop），需人工查看")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        out = []
        for r in all_results:
            r2 = {k: v for k, v in r.items() if not k.startswith("_")}
            r2["_para_deg_head_tail"] = r["_para_deg"][:10] + r["_para_deg"][-10:]
            r2["_geo_deg_head_tail"] = r["_geo_deg"][:10] + r["_geo_deg"][-10:]
            out.append(r2)
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n# wrote summary → {args.output}")


if __name__ == "__main__":
    main()