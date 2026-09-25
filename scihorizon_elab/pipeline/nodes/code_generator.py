"""
Code Generator Node - 确定性模板代码生成

UID 贯穿设计：
  - entity name = uid（全局唯一标识符）
  - Skill 参数中的 uid 保持原样（不替换为 spec）
  - 框架通过 uid 精确定位实体，同 spec 多实例不会冲突

设计原则:
  - 确定性: 相同输入必定生成相同代码
  - Fail-Fast: 模板失败即报错，不降级
  - 执行完即成功: get_condition_config 为 pass
  - 数据源统一: 只读 normalized_context（废弃 task_graph）
  - 字段名对齐: 读 class_name（与 asset_manager 输出一致）
"""

import logging
import os
import re
from pathlib import Path
from typing import Dict, List

from .code_gen_skills.entity_loader import plan_entity_loading, generate_load_methods
from .code_gen_skills.skill_formatter import format_skill_sequence
from .node_logger import log_node_output_file

logger = logging.getLogger(__name__)

# ==================== 模板常量 ====================

IMPORTS_BLOCK = """\
import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
"""

CONFIG_MANAGER_TEMPLATE = """\
@register.add_config_manager("{task_name}")
class {class_prefix}ConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

{load_methods}
    def get_instruction(self, target_entity, {extra_params}**kwargs):
        self.config["task"]["instructions"] = [{instruction}]

{condition_config_method}
"""

TASK_CLASS_TEMPLATE = """\
@register.add_task("{task_name}")
class {class_prefix}Task(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
{skill_lines}
        ]
        return skill_sequence
"""


# ==================== 辅助函数 ====================

def _to_class_prefix(task_name: str) -> str:
    """将 task_name 转为 CamelCase 类名前缀

    保证以字母或下划线开头（Python 标识符要求）。如果 task_name 以数字开头
    （如 '1_pour_beaker_into_beaker'），前缀加 'Task' 以确保合法。
    """
    prefix = "".join(word.capitalize() for word in task_name.split("_"))
    if prefix and prefix[0].isdigit():
        prefix = "Task" + prefix
    return prefix


def _build_condition_config_code(condition_plan, extra_params: str = "") -> str:
    """
    从 condition_plan 生成 get_condition_config 方法体。

    condition_plan 格式:
    [{"step_id": 0, "condition_type": "is_grasped", "params": {"entities": ["beaker_0"], "robot": "robot"}, ...},
     {"step_id": 1, "condition_type": "shake", "params": {...}, ...}]

    生成 list 形式的 conditions_config，每个元素是一个 dict(condition_type=params)。
    list 顺序与 step_id 顺序一致，由 SequentialConditionSet 做顺序检查。

    只取全部非 pass 条件；pass 条件不参与评测。
    """
    if not condition_plan:
        return (
            "    def get_condition_config(self, target_entity, "
            + extra_params
            + "**kwargs):\n"
            + "        # 执行完即成功\n"
            + "        pass\n"
        )

    # 过滤出非 pass 条件
    non_pass = [cp for cp in condition_plan if cp.get("condition_type") != "pass"]
    if not non_pass:
        return (
            "    def get_condition_config(self, target_entity, "
            + extra_params
            + "**kwargs):\n"
            + "        # 执行完即成功\n"
            + "        pass\n"
        )

    # 按 step_id 排序，保证条件顺序与 step 顺序一致
    non_pass = sorted(non_pass, key=lambda cp: cp.get("step_id", 0))

    # 构造 list 字面量，每个 entry 形如 dict(is_grasped=dict(...))
    entries = []
    for cp in non_pass:
        cond_type = cp["condition_type"]
        params = cp.get("params", {})
        params_str = _format_params(params, indent=12)
        entries.append(f"            dict({cond_type}={params_str}),")

    entries_str = "\n".join(entries)

    lines = [
        "    def get_condition_config(self, target_entity, " + extra_params + "**kwargs):",
        "        conditions_config = [",
        entries_str,
        "        ]",
        '        self.config["task"]["conditions"] = conditions_config',
    ]
    return "\n".join(lines)


def _format_params(params: Dict, indent: int = 12) -> str:
    """将 params dict 格式化为紧凑的 Python dict 字面量"""
    if not params:
        return "dict()"

    items = []
    for k, v in params.items():
        items.append(f"{k}={repr(v)}")

    # 尝试放在一行
    one_line = "dict(" + ", ".join(items) + ")"
    if len(one_line) < 80:
        return one_line

    # 多行
    ind = " " * indent
    lines = []
    for k, v in params.items():
        lines.append(f"{ind}{k}={repr(v)},")
    return "dict(\n" + "\n".join(lines) + f"\n{' ' * (indent - 4)})"


def _build_instruction(normalized_context: Dict, skill_plan: Dict) -> str:
    """
    从 steps 或 global_skill_plan 提取指令文本。

    instruction 中的 <uid> 保持原样，作为语义占位符。
    重要：合并所有 step 的 semantic_instruction / grounded_instruction 形成完整
    任务链，而不是只取第一步——否则多步任务的副步骤会被截断丢失
    （例如"等待人工加水后放烧杯"只输出等待句）。
    """
    global_plan = skill_plan.get("global_skill_plan", [])
    if global_plan:
        # 按 step_id 排序后拼接所有 semantic_instruction
        sorted_plan = sorted(global_plan, key=lambda s: s.get("step_id", 0))
        all_insts = []
        for step in sorted_plan:
            sem = step.get("semantic_instruction", "").strip()
            if sem:
                all_insts.append(sem)
        if all_insts:
            combined = " ".join(all_insts)
            return f'"{combined}"'

    steps = normalized_context.get("steps", [])
    if steps:
        # 按 step_id 排序后拼接所有 grounded_instruction
        sorted_steps = sorted(steps, key=lambda s: s.get("step_id", 0))
        all_insts = []
        for step in sorted_steps:
            inst = step.get("grounded_instruction", "").strip()
            if inst:
                all_insts.append(inst)
        if all_insts:
            combined = " ".join(all_insts)
            return f'"{combined}"'

    return '"Perform the task"'


def _validate_code(code: str) -> tuple:
    """基础校验生成的代码"""
    required_patterns = [
        ("@register.add_task", "missing @register.add_task decorator"),
        ("@register.add_config_manager", "missing @register.add_config_manager decorator"),
        ("get_expert_skill_sequence", "missing get_expert_skill_sequence method"),
        ("PrimitiveTask", "missing PrimitiveTask inheritance"),
        ("BenchTaskConfigManager", "missing BenchTaskConfigManager inheritance"),
    ]

    for pattern, error_msg in required_patterns:
        if pattern not in code:
            return False, error_msg

    try:
        compile(code, "<generated>", "exec")
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"

    return True, ""


# ==================== 主节点函数 ====================

def code_generator_node(state: Dict) -> Dict:
    """
    Code Generator 节点 - 确定性模板代码生成

    输入: state["normalized_context"] + state["asset_status"] + state["skill_plan"] + state["condition_plan"]
    输出: state["generated_code"] + state["task_module_path"]
    """
    logger.info("=" * 60)
    logger.info("[Code Generator] 开始生成任务代码...")

    normalized_context = state.get("normalized_context", {})
    asset_status = state.get("asset_status", {})
    skill_plan = state.get("skill_plan")
    condition_plan = state.get("condition_plan")
    task_analysis = state.get("task_analysis", {})

    # 日志输出 condition_plan（方便调试）
    if condition_plan:
        logger.info(f"[Code Generator] 接收 condition_plan: {len(condition_plan)} 个 conditions")
        for cp in condition_plan:
            logger.info(f"  Step {cp.get('step_id')}: {cp.get('condition_type')} - params={cp.get('params', {})}")
    else:
        logger.info("[Code Generator] 未收到 condition_plan（或为 None）")

    if skill_plan is None:
        error_msg = "skill_plan 为空，无法生成代码"
        logger.error(f"[Code Generator] ✗ {error_msg}")
        return {
            "error_feedback": error_msg,
            "current_stage": "registration",
        }

    instances = normalized_context.get("instances", [])
    task_name = task_analysis.get("task_name", "custom_task").replace(" ", "_")
    class_prefix = _to_class_prefix(task_name)

    # ── Step 1: 生成加载计划 ──────────────────────────────────────────
    plans = plan_entity_loading(instances, asset_status)
    logger.info(f"[Code Generator] 加载计划: {[(p.uid, p.spec, p.load_mode) for p in plans]}")

    load_methods_code, extra_imports, extra_constants = generate_load_methods(plans, asset_status)

    # ── Step 2: 生成 skill_sequence ───────────────────────────────────
    skill_lines = format_skill_sequence(skill_plan)

    # ── Step 3: 组装完整文件 ────────────────────────────────────────
    instruction = _build_instruction(normalized_context, skill_plan)

    # extra_params: 只有 init_container（试管架）时加参数
    has_init = any(p.method_name == "load_init_containers" for p in plans)
    extra_params = ""
    if has_init:
        extra_params += "init_container, "

    # 组装 imports
    imports = IMPORTS_BLOCK
    if extra_imports:
        imports += extra_imports + "\n"

    # 组装 constants
    constants_str = (extra_constants + "\n") if extra_constants else ""

    # ── Step 2.5: 生成 condition_config 方法 ─────────────────────────
    condition_config_method = _build_condition_config_code(condition_plan, extra_params)
    logger.info(f"[Code Generator] condition_config 方法:\n{condition_config_method}")

    # 组装 ConfigManager
    config_code = CONFIG_MANAGER_TEMPLATE.format(
        task_name=task_name,
        class_prefix=class_prefix,
        load_methods=load_methods_code,
        extra_params=extra_params,
        instruction=instruction,
        condition_config_method=condition_config_method,
    )

    # 组装 Task class
    task_code = TASK_CLASS_TEMPLATE.format(
        task_name=task_name,
        class_prefix=class_prefix,
        skill_lines=skill_lines,
    )

    code = imports + "\n" + constants_str + config_code + "\n\n" + task_code

    # ── Step 4: 校验 ─────────────────────────────────────────────────
    is_valid, error_msg = _validate_code(code)
    if not is_valid:
        logger.error(f"[Code Generator] ✗ 校验失败: {error_msg}")
        return {
            "error_feedback": f"Code generation failed: {error_msg}",
            "current_stage": "registration",
        }

    # ── Step 5: 写入文件 ─────────────────────────────────────────────
    vlabench_root = os.environ.get("SCIHORIZON_ELAB_ROOT")
    if not vlabench_root:
        logger.error("[Code Generator] ✗ SCIHORIZON_ELAB_ROOT 未设置")
        return {
            "error_feedback": "SCIHORIZON_ELAB_ROOT not set",
            "current_stage": "registration",
        }

    # 解析保存目录：默认到 autogen_tasks/，支持来自 create_task.py 的 __override_save_dir__ 覆盖
    vlabench_root_path = Path(vlabench_root).resolve()
    override_save_dir = state.get("__override_save_dir__")
    # 安全约束：save_dir 必须落在 ${SCIHORIZON_ELAB_ROOT}/benchmark/tasks/ 子树内
    # (允许 autogen_tasks/、task_list/ 等任意子目录)
    tasks_root = vlabench_root_path / "benchmark" / "tasks"
    if override_save_dir:
        raw_path = Path(override_save_dir).expanduser()
        # 相对路径优先解释为相对于 ${SCIHORIZON_ELAB_ROOT}
        if not raw_path.is_absolute():
            raw_path = vlabench_root_path / raw_path
        save_dir = raw_path.resolve()
        # 安全检查：save_dir 必须落在 ${SCIHORIZON_ELAB_ROOT}/benchmark/tasks/ 子树内
        try:
            save_dir.relative_to(tasks_root)
        except ValueError:
            err = (
                f"--save-dir must be inside {tasks_root} (e.g. 'benchmark/tasks/autogen_tasks/' "
                f"or 'benchmark/tasks/task_list/liquid_handling/'); got {save_dir}"
            )
            logger.error(f"[Code Generator] ✗ {err}")
            return {
                "error_feedback": err,
                "current_stage": "registration",
            }
        logger.info(f"[Code Generator] 使用 --save-dir 覆盖: {save_dir}")
    else:
        save_dir = vlabench_root_path / "benchmark" / "tasks" / "autogen_tasks"

    task_file = save_dir / f"{task_name}_series.py"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    # 确保子目录包含 __init__.py，否则 Python import 机制找不到该模块
    init_file = task_file.parent / "__init__.py"
    if not init_file.exists():
        init_file.touch()
    task_file.write_text(code, encoding="utf-8")

    logger.info(f"[Code Generator] ✓ 代码已写入: {task_file}")
    logger.info(f"[Code Generator] 代码长度: {len(code)} 字符")
    logger.info("=" * 60 + "\n")

    output = {
        "generated_code": code,
        "task_module_path": str(task_file),
        "current_stage": "registration",
    }
    log_node_output_file("code_generator", state, output)
    return output
