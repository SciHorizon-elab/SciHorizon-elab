"""
compute_bbox.py - 批量给 MuJoCo XML 资产添加 @bbox 注释。

用法:
  python compute_bbox.py --dry-run          # 只打印，不写入
  python compute_bbox.py --write            # 实际写入 XML

计算方式：读取每个 XML 引用的所有 OBJ mesh 文件顶点，按其 scale 缩放后取 AABB 的 dx/dy/dz。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 根目录（可配置）
ASSETS_ROOT = Path(__file__).parent.parent / "scihorizon_elab" / "simulation" / "assets" / "obj"

# 匹配 <mesh ... /> 或 <mesh ...>（允许属性跨多行、含空格）
# 捕获整个 <mesh ... /> 标签内容
MESH_TAG_RE = re.compile(
    r'<mesh\b([^>]*?)\/?>', re.IGNORECASE | re.DOTALL
)
MESH_FILE_RE = re.compile(r'file=["\']([^"\']+)["\']', re.IGNORECASE)
MESH_SCALE_RE = re.compile(r'scale=["\']([^"\']+)["\']', re.IGNORECASE)

# OBJ 顶点行
OBJ_VERTEX_RE = re.compile(
    r'^\s*v\s+([\-\d.eE+]+)\s+([\-\d.eE+]+)\s+([\-\d.eE+]+)',
    re.MULTILINE,
)

# 已有 bbox 检测
BBOX_COMMENT_RE = re.compile(
    r'<!--\s*@bbox\s+dx=([\d.]+)\s+dy=([\d.]+)\s+dz=([\d.]+)\s*-->',
    re.IGNORECASE,
)

# 跳过清单（无法用 mesh+obj 方式计算 或 尺寸超大不进布局）
SKIP_FILES = {
    "table/table.xml",                      # 只有 inline geom，无 mesh
    "drawer/drawer.xml",                    # 使用 .msh 格式
    "lab_equipment/petri_dish.xml",         # 嵌套复杂，待单独处理
    "centrifuge/centrifuge.xml",            # 场景中放桌外，不进桌面布局
    # 超大尺寸（远超 WORK_AREA 0.7m×0.5m），不进 BLF 桌面布局
    "chemistry_lab_table/chemistry_lab_table/chemistry_lab_table/chemistry_lab_table.xml",
    "lab_table/lab_table/lab_table/lab_table.xml",
}


def parse_vec3(s: str) -> Tuple[float, float, float]:
    """解析 "x y z" 或 "x" → (x,y,z)"""
    parts = s.replace(",", " ").split()
    if len(parts) == 1:
        v = float(parts[0])
        return (v, v, v)
    if len(parts) >= 3:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    return (1.0, 1.0, 1.0)


def load_mesh_bbox(obj_path: Path, scale: Tuple[float, float, float]) -> Optional[Tuple[float, float, float]]:
    """读取 OBJ 文件顶点，返回缩放后的 dx/dy/dz"""
    try:
        text = obj_path.read_text(errors="ignore")
    except Exception:
        return None
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    found = False
    for m in OBJ_VERTEX_RE.finditer(text):
        x = float(m.group(1)) * scale[0]
        y = float(m.group(2)) * scale[1]
        z = float(m.group(3)) * scale[2]
        min_x, max_x = min(min_x, x), max(max_x, x)
        min_y, max_y = min(min_y, y), max(max_y, y)
        min_z, max_z = min(min_z, z), max(max_z, z)
        found = True
    if not found:
        return None
    return (max_x - min_x, max_y - min_y, max_z - min_z)


def compute_xml_bbox(xml_path: Path) -> Optional[Tuple[float, float, float]]:
    """
    返回 (dx, dy, dz)，单位米。
    """
    try:
        text = xml_path.read_text()
    except Exception:
        return None

    # 解析所有 <mesh> 标签，收集 (file, scale)
    mesh_specs: List[Tuple[str, Tuple[float, float, float]]] = []
    for m in MESH_TAG_RE.finditer(text):
        attrs = m.group(1)  # 可能跨多行
        file_m = MESH_FILE_RE.search(attrs)
        if not file_m:
            continue
        file_str = file_m.group(1).strip()
        scale_m = MESH_SCALE_RE.search(attrs)
        scale = parse_vec3(scale_m.group(1)) if scale_m else (1.0, 1.0, 1.0)
        mesh_specs.append((file_str, scale))

    if not mesh_specs:
        return None

    # 对每个 mesh spec 加载 OBJ 文件，计算 AABB
    xml_dir = xml_path.parent
    aabbs: List[Tuple[float, float, float]] = []
    for file_str, scale in mesh_specs:
        obj_path = (xml_dir / file_str).resolve()
        if not obj_path.exists():
            continue
        bbox = load_mesh_bbox(obj_path, scale)
        if bbox:
            aabbs.append(bbox)

    if not aabbs:
        return None

    # 取所有 mesh AABB 的并集（保守：各取最大维度）
    max_dx = max(b[0] for b in aabbs)
    max_dy = max(b[1] for b in aabbs)
    max_dz = max(b[2] for b in aabbs)
    return (max_dx, max_dy, max_dz)


def has_bbox_comment(xml_path: Path) -> bool:
    text = xml_path.read_text(errors="ignore")
    return bool(BBOX_COMMENT_RE.search(text))


def find_insert_after_xml_decl(text: str) -> int:
    """
    返回插入 @bbox 注释的行号（0-indexed）。

    策略：找到 <?xml?> 声明行，插在其之后。
    这样 <?xml?> 始终在第一行，符合 XML 规范。
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("<?"):
            return i + 1
    # 没有 <?xml?>，插在 <mujoco> 之前（即行 0）
    for i, line in enumerate(lines):
        if line.strip().startswith("<mujoco"):
            return i
    return 0


def write_bbox_annotation(xml_path: Path, dx: float, dy: float, dz: float) -> None:
    """
    在 <?xml?> 声明后、<mujoco> 前插入 @bbox 注释。
    保证 <?xml?> 始终在第一行。
    """
    text = xml_path.read_text()
    insert_idx = find_insert_after_xml_decl(text)
    lines = text.splitlines(keepends=True)

    comment = f"<!-- @bbox dx={dx:.3f} dy={dy:.3f} dz={dz:.3f} -->\n"
    lines.insert(insert_idx, comment)
    xml_path.write_text("".join(lines))


def main():
    parser = argparse.ArgumentParser(description="批量为 XML 资产计算并写入 @bbox 注释")
    parser.add_argument(
        "--write", action="store_true",
        help="写入 XML（默认 dry-run，只打印）"
    )
    parser.add_argument(
        "--assets-root", type=Path, default=ASSETS_ROOT,
        help=f"资产根目录（默认 {ASSETS_ROOT}）"
    )
    args = parser.parse_args()

    xml_files = sorted(args.assets_root.rglob("*.xml"))
    print(f"扫描目录: {args.assets_root}")
    print(f"找到 XML: {len(xml_files)} 个")
    print(f"模式: {'WRITE（将写入）' if args.write else 'DRY-RUN（不写入）'}")
    print("=" * 80)

    results = {
        "added": [],
        "skipped_has_bbox": [],
        "skipped_no_mesh": [],
        "skipped_known": [],
    }

    for xml in xml_files:
        rel = str(xml.relative_to(args.assets_root))

        # 跳过：已有 bbox
        if has_bbox_comment(xml):
            results["skipped_has_bbox"].append(rel)
            continue

        # 跳过：已知无法计算的
        if rel in SKIP_FILES:
            results["skipped_known"].append((rel, "跳过：已在 SKIP_FILES 中"))
            continue

        # 计算 bbox
        bbox = compute_xml_bbox(xml)
        if bbox is None:
            results["skipped_no_mesh"].append(rel)
            continue

        dx, dy, dz = bbox
        results["added"].append((rel, xml, dx, dy, dz))

        # 打印
        print(f"  {rel:<75} dx={dx:.3f} dy={dy:.3f} dz={dz:.3f}")

    print()
    print(f"=== 结果汇总 ===")
    print(f"  新增 bbox: {len(results['added'])} 个")
    print(f"  跳过（已有）: {len(results['skipped_has_bbox'])} 个")
    print(f"  跳过（无 mesh/obj）: {len(results['skipped_no_mesh'])} 个")
    print(f"  跳过（已知不可算）: {len(results['skipped_known'])} 个")

    if results["skipped_no_mesh"]:
        print(f"\n  ⚠️  无 mesh 的 XML（可能只有 inline geom）:")
        for f in results["skipped_no_mesh"]:
            print(f"    - {f}")

    if results["skipped_known"]:
        print(f"\n  已知跳过清单:")
        for f, reason in results["skipped_known"]:
            print(f"    - {f}: {reason}")

    # 写入
    if args.write and results["added"]:
        print()
        confirm = input(f"确认写入 {len(results['added'])} 个 XML 文件？(y/n): ")
        if confirm.lower() != "y":
            print("已取消。")
            return
        for rel, xml, dx, dy, dz in results["added"]:
            write_bbox_annotation(xml, dx, dy, dz)
            print(f"  写入: {rel}")
        print("\n完成！")
    elif not args.write:
        print("\n(dry-run 模式，未写入任何文件。添加 --write 参数实际写入。)")


if __name__ == "__main__":
    main()
