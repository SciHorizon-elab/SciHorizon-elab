"""
仅执行 Simulation 阶段 - 跳过所有 LLM 节点，直接加载已有任务跑仿真

支持两种指定任务的方式：
  1. --task-name NAME  ：按 task_name 自动查找（默认位置: autogen_tasks/primitive/ 或 autogen_tasks/）
  2. --task-file PATH  ：直接指定 series 文件的绝对/相对路径，模块路径自动推导

支持 SequentialConditionSet 顺序条件评测（与 evaluate_openpi.py 逻辑一致）

用法:
    # 旧用法（向后兼容）
    python scihorizon_elab/pipeline/run_task.py --task-name pick_stir

    # 新用法（推荐）：直接指定 series 文件路径
    python scihorizon_elab/pipeline/run_task.py \
        --task-file benchmark/tasks/task_list/liquid_handling/1_pour_beaker_into_beaker_series.py

    # 二者不能同时使用
"""
from pathlib import Path

# repo 根 = 上 3 级 (scihorizon_elab/pipeline/run_task.py)
REPO_ROOT = Path(__file__).resolve().parents[2]
SCIHORIZON_PKG = REPO_ROOT / "scihorizon_elab"

import sys
sys.path.insert(0, str(REPO_ROOT))

import os
os.environ.setdefault("SCIHORIZON_ELAB_ROOT", str(SCIHORIZON_PKG))
os.environ.setdefault("MUJOCO_GL", "egl")
os.environ.setdefault("DM_ENV_GRASP_LOCK", "0")

import argparse
import importlib
import importlib.util
import logging
import traceback
import numpy as np
import mediapy
from pathlib import Path

import scihorizon_elab.simulation.entities  # 打破 circular import

logging.basicConfig(level=logging.INFO, format="%(message)s")


def _resolve_series_path(task_name: str, vlabench_root: str) -> Path | None:
    """按 task_name 在默认位置查找 series 文件

    查找顺序:
      1. benchmark/tasks/autogen_tasks/primitive/<task_name>_series.py
      2. benchmark/tasks/autogen_tasks/<task_name>_series.py
      3. benchmark/tasks/task_list/**/<task_name>_series.py（深度优先扫描）
    """
    series_name = f"{task_name}_series"
    candidates = [
        Path(vlabench_root) / "benchmark" / "tasks" / "autogen_tasks" / "primitive" / f"{series_name}.py",
        Path(vlabench_root) / "benchmark" / "tasks" / "autogen_tasks" / f"{series_name}.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    # 深度扫描 task_list/ 子树（最多 4 层）
    task_list_root = Path(vlabench_root) / "benchmark" / "tasks" / "task_list"
    if task_list_root.exists():
        for p in task_list_root.rglob(f"{series_name}.py"):
            return p
    return None


def _derive_module_name(series_path: Path, vlabench_root: str) -> str:
    """根据 series 文件路径推导 Python 模块名

    规则: 文件相对于 ${SCIHORIZON_ELAB_ROOT}/benchmark/tasks/ 的路径，把 / 替换为 .
    """
    try:
        rel = series_path.resolve().relative_to(Path(vlabench_root) / "benchmark" / "tasks")
        return "scihorizon_elab.benchmark.tasks." + str(rel.with_suffix("")).replace("/", ".")
    except ValueError:
        # 文件不在 benchmark/tasks/ 下，回退到按文件名推断
        return "scihorizon_elab.benchmark.tasks.autogen_tasks." + series_path.stem


def main():
    parser = argparse.ArgumentParser(
        description="Run simulation for an existing task series (skip all LLM nodes).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--task-name",
        help="Task name (e.g. 'pick_stir'). Auto-resolves the .py file under "
             "${SCIHORIZON_ELAB_ROOT}/benchmark/tasks/. Equivalent to the old "
             "single-arg mode.",
    )
    group.add_argument(
        "--task-file",
        dest="task_file",
        help="Direct path to a <task_name>_series.py file. Accepts absolute path "
             "or path relative to repo root / SCIHORIZON_ELAB_ROOT. The Python "
             "module name is auto-derived from the file's location.",
    )
    args = parser.parse_args()

    task_name: str | None = args.task_name
    vlabench_root = os.environ["SCIHORIZON_ELAB_ROOT"]

    # ── 解析 series 文件路径 ─────────────────────────────────────────
    if args.task_file:
        # 用户直接给了文件路径
        given_path = Path(args.task_file)
        if given_path.is_absolute():
            series_path = given_path
        else:
            # 相对路径优先相对于 repo_root，其次相对于 vlabench_root
            for base in (REPO_ROOT, Path(vlabench_root)):
                candidate = (base / given_path).resolve()
                if candidate.exists():
                    series_path = candidate
                    break
            else:
                series_path = (Path(vlabench_root) / given_path).resolve()
        if not series_path.exists():
            print(f"错误: --task-file 指定的文件不存在: {series_path}")
            sys.exit(1)
        # 从文件名推断 task_name (stem 去掉 _series 后缀)
        if series_path.stem.endswith("_series"):
            task_name = series_path.stem[: -len("_series")]
        else:
            print(f"警告: 文件名 {series_path.name} 不以 _series 结尾，使用全名作为 task_name")
            task_name = series_path.stem
    else:
        # 按 task_name 自动查找
        series_path = _resolve_series_path(task_name, vlabench_root)
        if series_path is None:
            print(f"错误: 找不到 series 文件: {task_name}_series.py")
            print("提示: 可使用 --task-file 直接指定 .py 文件路径。")
            sys.exit(1)

    series_name = f"{task_name}_series"
    module_name = _derive_module_name(series_path, vlabench_root)
    print(f"[run_task] task_name  = {task_name}")
    print(f"[run_task] series_path = {series_path}")
    print(f"[run_task] module_name = {module_name}")

    # ── 1. 导入框架模块，触发内置 @register 装饰器 ──────────────────────
    importlib.import_module("scihorizon_elab.simulation.robots")
    importlib.import_module("scihorizon_elab.benchmark.tasks.autogen_tasks")

    # ── 2. 动态加载 series 文件 ───────────────────────────────────────
    spec = importlib.util.spec_from_file_location(series_name, str(series_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print(f"✓ 已加载 series 文件: {series_path}")

    # ── 3. 更新 name2config（内存），使 load_env 能找到任务 ────────────
    from scihorizon_elab.benchmark.configs import name2config as configs_name2config
    import scihorizon_elab.benchmark.tasks  # 触发 @register 装饰器

    configs_name2config[series_name] = [task_name]
    print(f"✓ 已更新 name2config: {series_name} -> [{task_name}]")

    # ── 4. 加载环境 ───────────────────────────────────────────────────
    from scihorizon_elab.simulation.envs import load_env

    env = load_env(task_name, robot="franka")
    print(f"✓ 环境加载完成")

    # ── 5. 初始化条件评测（与 evaluate_openpi.py 逻辑一致） ────────────
    has_conditions = hasattr(env.task, 'conditions') and env.task.conditions is not None
    if has_conditions:
        # 重置顺序锁
        if hasattr(env.task.conditions, 'reset_locks'):
            env.task.conditions.reset_locks()
        # 记录初始状态
        for condition in env.task.conditions.conditions:
            if hasattr(condition, 'record_initial_state'):
                condition.record_initial_state(env.physics)
        # 挂载逐帧条件回调：每个 env.step 的 after_step 会自动调用
        if not hasattr(env.task, '_per_step_condition_callbacks'):
            env.task._per_step_condition_callbacks = []
        env.task._per_step_condition_callbacks.append(env.task.conditions.is_met)
        print(f"✓ 顺序条件评测已初始化 ({len(env.task.conditions.conditions)} 个条件)")
        for i, cond in enumerate(env.task.conditions.conditions):
            print(f"    条件 {i}: {type(cond).__name__}")

    # ── 6. 获取并执行技能序列 ────────────────────────────────────────
    skill_seq = env.get_expert_skill_sequence()
    if skill_seq is None:
        print("错误: get_expert_skill_sequence() 返回 None")
        sys.exit(1)

    print(f"✓ 技能序列: {[s.func.__name__ for s in skill_seq]}")
    print()
    print("=" * 60)

    env._skill_execution_mode = True
    observations = []
    task_success = False

    # try/except 兜底:技能抛异常时不让进程崩溃,保证已有 observations
    # 仍能走到下方条件评测 + 视频保存(失败录像)
    try:
        for skill_idx, skill in enumerate(skill_seq):
            skill_name = skill.func.__name__
            print(f"[仿真] 执行技能 {skill_idx + 1}/{len(skill_seq)}: {skill_name}")

            obs, waypoint, stage_success, skill_task_success = skill(env)
            observations.extend(obs)

            if not stage_success:
                print(f"[仿真] ⚠ 技能 {skill_name} 执行失败")
                break

            if skill_task_success:
                task_success = True
                break
    except Exception as e:
        print(f"[仿真] ✗ 技能执行抛出异常: {e}")
        traceback.print_exc()
        print("[仿真] 已捕获异常,尝试保存已有观测的视频")
    finally:
        env._skill_execution_mode = False

    print("=" * 60)

    # ── 7. 收集每个条件的最终结果 ────────────────────────────────────
    condition_results = {}
    all_conditions_met = False
    if has_conditions:
        for i, cond in enumerate(env.task.conditions.conditions):
            cond_name = type(cond).__name__
            condition_results[cond_name] = env.task.conditions._locked[i]
        all_conditions_met = env.task.conditions.is_met(env.physics)

    # ── 8. 保存视频 ───────────────────────────────────────────────────
    project_root = Path(vlabench_root).parent
    task_dir = project_root / "dataset" / "autogen_tasks" / task_name
    if observations:
        frames = [obs["rgb"] for obs in observations if "rgb" in obs]
        if frames:
            # 拼接 4 个摄像头画面
            frames_grid = [np.vstack([np.hstack(f[:2]), np.hstack(f[2:4])]) for f in frames]
            video_path = task_dir / f"demo_0_success_{all_conditions_met}.mp4"
            task_dir.mkdir(parents=True, exist_ok=True)
            mediapy.write_video(str(video_path), frames_grid, fps=10)
            print(f"✓ 视频保存: {video_path}")

    env.close()

    # ── 9. 打印结果 ───────────────────────────────────────────────────
    print()
    if has_conditions:
        print("条件评测结果:")
        for cond_name, met in condition_results.items():
            status = "✓ 通过" if met else "✗ 失败"
            print(f"  {cond_name}: {status}")
        print()

    if all_conditions_met:
        print("仿真成功!")
    else:
        print("仿真失败")
        if not condition_results:
            print("  原因: 无条件定义")


if __name__ == "__main__":
    main()