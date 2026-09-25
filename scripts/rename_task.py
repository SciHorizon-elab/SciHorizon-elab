#!/usr/bin/env python3
"""
任务重命名脚本
用法: python rename_task.py <旧任务名> <新任务名>
示例: python rename_task.py pick_small_beaker_place_small_beaker place_beaker

该脚本会同步修改以下内容：
1. tasks/ 目录树 (含 autogen_tasks、task_list 等子目录) 中的 {old_name}_series.py 文件重命名
2. Python 文件内的类名和装饰器注册名 (数字开头任务名的类名加 Task 前缀)
3. 任务所在子目录 __init__.py 中的 import 语句 (存在时)
4. configs/__init__.py 中的 name2config (存在对应条目时)
5. configs/task_config.json 中的 JSON key (存在对应条目时)
"""

import os
import sys
import json
import re
import shutil
import argparse
from pathlib import Path

SCIHORIZON_ELAB_ROOT = Path(__file__).parents[1] / "scihorizon_elab" / "benchmark"
TASKS_DIR = SCIHORIZON_ELAB_ROOT / "tasks"


def parse_args():
    parser = argparse.ArgumentParser(description="重命名 scihorizon_elab 任务")
    parser.add_argument("old_name", help="旧任务名，如 pick_small_beaker_place_small_beaker")
    parser.add_argument("new_name", help="新任务名，如 place_beaker")
    return parser.parse_args()


def to_class_name(name):
    """将任务名转换为合法类名 (snake_case -> PascalCase)

    数字开头的任务名 (如 3_xxx) 不能直接作为 Python 类名，
    按仓库约定加上 Task 前缀 (如 3_xxx -> Task3Xxx)。
    """
    class_name = "".join(word.capitalize() for word in name.split("_"))
    if class_name and class_name[0].isdigit():
        class_name = "Task" + class_name
    return class_name


def check_files_exist(old_name):
    """检查相关文件是否存在 (在整个 tasks 目录树下查找)"""
    return locate_series_file(old_name, TASKS_DIR)[0] is not None


def check_name_conflict(new_name):
    """检查新名字是否已存在 (在整个 tasks 目录树下查找)"""
    for series_file, _ in _iter_series_candidates(new_name):
        if series_file.exists():
            return f"新文件名已存在: {series_file}"

    task_json = SCIHORIZON_ELAB_ROOT / "configs" / "task_config.json"
    with open(task_json) as f:
        if f'"{new_name}_series"' in f.read():
            return f"task_config.json 中已存在 {new_name}_series 的配置"

    return None


def _iter_series_candidates(name):
    """在 tasks 目录树 (含全部子目录) 中枚举 <name>_series.py 的位置"""
    for series_file in TASKS_DIR.rglob(f"{name}_series.py"):
        yield series_file, series_file.parent


def locate_series_file(name, _search_dir=None):
    """在整个 tasks 目录树中定位 series 文件 (兼容旧签名)"""
    for series_file, parent in _iter_series_candidates(name):
        if series_file.exists():
            return series_file, parent
    return None, None


def rename_task(old_name, new_name):
    """执行重命名操作"""
    series_file, source_subdir = locate_series_file(old_name, TASKS_DIR)
    if series_file is None:
        print(f"错误: 找不到任务文件: {old_name}_series.py")
        sys.exit(1)

    new_series_file = source_subdir / f"{new_name}_series.py"
    init_file = source_subdir / "__init__.py"
    configs_init = SCIHORIZON_ELAB_ROOT / "configs" / "__init__.py"
    task_json = SCIHORIZON_ELAB_ROOT / "configs" / "task_config.json"

    # 1. 重命名文件
    shutil.move(series_file, new_series_file)
    print(f"✓ 重命名文件: {series_file.name} -> {new_series_file.name}")

    # 2. 修改 Python 文件内容
    old_class_prefix = to_class_name(old_name)
    new_class_prefix = to_class_name(new_name)

    content = new_series_file.read_text()

    # 替换装饰器注册名 (两次: ConfigManager 和 Task)
    content = content.replace(f'@register.add_config_manager("{old_name}")', f'@register.add_config_manager("{new_name}")')
    content = content.replace(f'@register.add_task("{old_name}")', f'@register.add_task("{new_name}")')

    # 替换类名
    content = content.replace(old_class_prefix, new_class_prefix)

    new_series_file.write_text(content)
    print(f"✓ 修改 Python 文件内容: {old_class_prefix}* -> {new_class_prefix}*")

    # 3. 修改子目录对应的 __init__.py (存在时才修改)
    if init_file.exists():
        init_content = init_file.read_text()
        init_content = init_content.replace(f"{old_name}_series", f"{new_name}_series")
        init_file.write_text(init_content)
        print(f"✓ 修改 {init_file.relative_to(SCIHORIZON_ELAB_ROOT)}")

    # 4. 修改 configs/__init__.py (存在对应条目时才修改)
    if configs_init.exists():
        configs_content = configs_init.read_text()
        new_configs_content = configs_content.replace(f'"{old_name}_series"', f'"{new_name}_series"')
        new_configs_content = new_configs_content.replace(f'["{old_name}"]', f'["{new_name}"]')
        if new_configs_content != configs_content:
            configs_init.write_text(new_configs_content)
            print(f"✓ 修改 configs/__init__.py")

    # 5. 修改 task_config.json (存在对应条目时才修改)
    with open(task_json, "r") as f:
        json_content = json.load(f)

    if f"{old_name}_series" in json_content:
        json_content[f"{new_name}_series"] = json_content.pop(f"{old_name}_series")
        with open(task_json, "w") as f:
            json.dump(json_content, f, indent=2)
        print(f"✓ 修改 configs/task_config.json")

    print(f"\n重命名完成: {old_name} -> {new_name}")


def main():
    args = parse_args()
    old_name = args.old_name
    new_name = args.new_name

    print(f"开始重命名: {old_name} -> {new_name}\n")

    # 检查旧文件是否存在
    if not check_files_exist(old_name):
        print(f"错误: 找不到任务文件: {old_name}_series.py")
        sys.exit(1)

    # 检查新名字是否冲突
    conflict = check_name_conflict(new_name)
    if conflict:
        print(f"错误: {conflict}")
        sys.exit(1)

    try:
        rename_task(old_name, new_name)
    except Exception as e:
        print(f"\n错误: 重命名失败 - {e}")
        print("所有文件保持不变")
        sys.exit(1)


if __name__ == "__main__":
    main()
