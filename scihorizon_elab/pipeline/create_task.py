"""
Task Creation Entry Point - 从自然语言指令创建任务模板

这是 scihorizon_elab pipeline 的正式入口脚本，用于从用户指令端到端生成、
注册并（可选地）仿真一个任务 series。

替代原先的 test_e2e.py，定位从"测试"转为"生产工具"。

Usage:
    # 基础用法 (与旧 test_e2e.py 完全兼容)
    python -m scihorizon_elab.pipeline.create_task "lift the beaker"

    # 显式指定生成的 series 文件名 (覆盖 Analyzer 推断的 task_name)
    python -m scihorizon_elab.pipeline.create_task "pick up the tube" \\
        --task-name custom_tube_lift

    # 指定输出目录 (必须落在 ${SCIHORIZON_ELAB_ROOT} 内)
    python -m scihorizon_elab.pipeline.create_task "place the beaker" \\
        --task-name place_beaker_custom \\
        --save-dir ./benchmark/tasks/autogen_tasks/experiments/

    # 只生成+注册，跳过仿真
    python -m scihorizon_elab.pipeline.create_task "lift the beaker" \\
        --no-simulate

    # 查看帮助
    python -m scihorizon_elab.pipeline.create_task --help
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# repo 根 = 上 3 级 (scihorizon_elab/pipeline/create_task.py)
REPO_ROOT = Path(__file__).resolve().parents[2]
VLABENCH_PKG = REPO_ROOT / "scihorizon_elab"

sys.path.insert(0, str(REPO_ROOT))

import os
os.environ["SCIHORIZON_ELAB_ROOT"] = str(VLABENCH_PKG)
os.environ["DM_ENV_GRASP_LOCK"] = "0"  # substep sync 模式，每 N 个 physics substep 同步物体位姿

import scihorizon_elab.simulation.entities  # 打破 circular import

from scihorizon_elab.pipeline.nodes.analyzer import analyzer_node
from scihorizon_elab.pipeline.nodes.normalizer import normalizer_node
from scihorizon_elab.pipeline.nodes.asset_manager import asset_manager_node
from scihorizon_elab.pipeline.nodes.skill_planner import skill_planner_node
from scihorizon_elab.pipeline.nodes.condition_planner import condition_planner_node
from scihorizon_elab.pipeline.nodes.code_generator import code_generator_node
from scihorizon_elab.pipeline.nodes.registration import registration_node
from scihorizon_elab.pipeline.nodes.simulation import simulation_node
from scihorizon_elab.pipeline.nodes.node_logger import init_run_log, log_instruction_entry


# ── CLI ──────────────────────────────────────────────────────────────
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="create_task",
        description=(
            "Create a scihorizon_elab task series from a natural-language instruction. "
            "Runs the full 7-node pipeline (analyzer → registration) and optionally "
            "executes the resulting task in MuJoCo simulation."
        ),
    )
    parser.add_argument(
        "instruction",
        nargs="?",
        default="lift the beaker",
        help="Natural-language task description (e.g. 'pick up the beaker'). "
             "Default: 'lift the beaker'.",
    )
    parser.add_argument(
        "--task-name",
        dest="task_name",
        default=None,
        help="Override the auto-inferred task name. The generated Python file will "
             "be named <task_name>_series.py. If omitted, the Analyzer node decides "
             "the name via LLM.",
    )
    parser.add_argument(
        "--save-dir",
        dest="save_dir",
        default=None,
        help="Directory to write <task_name>_series.py into. Must be located inside "
             "${SCIHORIZON_ELAB_ROOT} (default: ${SCIHORIZON_ELAB_ROOT}/benchmark/"
             "tasks/autogen_tasks/). Accepts absolute or relative paths; relative "
             "paths are resolved against ${SCIHORIZON_ELAB_ROOT}.",
    )
    parser.add_argument(
        "--no-simulate",
        action="store_true",
        help="Skip the Simulation node (only generate + register the task).",
    )
    return parser.parse_args(argv)


# ── Main ─────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    args = parse_args(argv)

    instruction = args.instruction
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = init_run_log(instruction)
    log_instruction_entry(log_path, instruction)

    print(f"[create_task] instruction: {instruction!r}")
    if args.task_name:
        print(f"[create_task] --task-name override: {args.task_name!r}")
    if args.save_dir:
        print(f"[create_task] --save-dir override: {args.save_dir!r}")
    if args.no_simulate:
        print(f"[create_task] --no-simulate: skipping Simulation node")

    # ── Node 1-7: Pipeline 链式执行 ─────────────────────────────────
    state = {"user_instruction": instruction, "messages": [], "_log_filepath": log_path}
    state = {**state, **analyzer_node(state)}

    # ✦ 覆盖 Analyzer 推断的 task_name (在 Normalizer/CodeGen 之前注入) ✦
    if args.task_name:
        overridden = args.task_name.replace(" ", "_")
        state["task_analysis"]["task_name"] = overridden
        print(f"[create_task] ✓ task_name overridden to: {overridden!r}")

    state = {**state, **normalizer_node({"task_analysis": state["task_analysis"], "_log_filepath": log_path})}
    state = {**state, **asset_manager_node({"normalized_context": state["normalized_context"], "_log_filepath": log_path})}

    # skill_planner 和 condition_planner 并行执行
    skill_state = {"normalized_context": state["normalized_context"], "asset_status": state["asset_status"], "messages": [], "_log_filepath": log_path}
    cond_state = {"normalized_context": state["normalized_context"], "asset_status": state["asset_status"], "messages": [], "_log_filepath": log_path}
    skill_result = skill_planner_node(skill_state)
    cond_result = condition_planner_node(cond_state)
    state = {**state, **skill_result, **cond_result}

    # ✦ 注入 save_dir 覆盖 (由 code_generator_node 内部读取) ✦
    code_result = code_generator_node({
        "normalized_context": state["normalized_context"],
        "asset_status": state["asset_status"],
        "skill_plan": state["skill_plan"],
        "condition_plan": state.get("condition_plan"),
        "task_analysis": state["task_analysis"],
        "_log_filepath": log_path,
        "__override_save_dir__": args.save_dir,
    })
    state = {**state, **code_result}

    # 优雅处理 Code Generator 失败（如 --save-dir 非法）
    if not state.get("task_module_path"):
        err = state.get("error_feedback", "Code Generator failed without error message")
        print(f"✗ Code Generator failed: {err}")
        return 1

    state = {**state, **registration_node({
        "task_analysis": state["task_analysis"],
        "normalized_context": state["normalized_context"],
        "asset_status": state["asset_status"],
        "skill_plan": state["skill_plan"],
        "task_module_path": state["task_module_path"],
        "_log_filepath": log_path,
    })}

    print(f'Registration: {state.get("registration_success")}')
    if state.get("task_module_path"):
        print(f'  Generated file: {state["task_module_path"]}')

    if not state.get("registration_success"):
        print("Registration failed, skipping simulation")
        return 1

    # ── Node 8: Simulation (可选) ────────────────────────────────────
    if args.no_simulate:
        print("\n[create_task] ✓ Task created & registered. Simulation skipped (--no-simulate).")
        return 0

    print("\n[Simulation] 开始仿真...")
    sim_state = {
        "task_analysis": state["task_analysis"],
        "normalized_context": state["normalized_context"],
        "asset_status": state["asset_status"],
        "skill_plan": state["skill_plan"],
        "condition_plan": state.get("condition_plan"),
        "_log_filepath": log_path,
    }
    sim_out = simulation_node(sim_state)

    if sim_out.get("simulation_success"):
        print(f'✓ 仿真成功!')
        print(f'  视频路径: {sim_out.get("simulation_video_path")}')
        print(f'  HDF5路径: {sim_out.get("simulation_hdf5_path")}')
        return 0
    else:
        print(f'✗ 仿真失败')
        print(f'  error_feedback: {sim_out.get("error_feedback", "")[:500]}')
        if sim_out.get("simulation_video_path"):
            print(f'  视频仍保存于: {sim_out["simulation_video_path"]}')
        return 1


if __name__ == "__main__":
    sys.exit(main())