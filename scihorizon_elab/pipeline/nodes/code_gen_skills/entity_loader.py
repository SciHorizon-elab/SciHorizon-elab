"""
Entity Loader - 结构化实体加载代码生成

简化设计：不再区分 container 和 object，所有实体统一放到 load_objects。
只有两种特殊情况：
  1. ChemistryTube → subentity 模式，自动注入 tube_stand 父容器
  2. 带 solution → liquid 模式
  3. 其余 → plain 模式

设计原则:
  - 一个 uid 只出现一次，不会多实例冲突
  - name2class_xml 查询用 spec（lookup key），entity name 用 uid
"""

import logging
import os
import random
import re
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 试管 subentity 布局常量
TUBE_COL_POS = [-0.16, -0.08, 0, 0.08, 0.16]
TUBE_ROW_POS = [-0.05, 0.05]

# 移液枪架 subentity 布局常量 (4 段中点)
PIPETTE_STAND_COL_POS = [0]
PIPETTE_STAND_ROW_POS = [-0.1088, -0.0363, 0.0363, 0.1088]

# ── Bbox 感知布局算法常量 ───────────────────────────────────────────────
WORK_AREA = {"x_min": -0.45, "x_max": 0.45, "y_min": -0.20, "y_max": 0.40}
TARGET_CENTER = (0.0, 0.10)
LAYOUT_MARGIN = 0.03  # 3cm（5cm 太大，会导致两个 flask 叠放超工作区深度）

# 兜底注册表（spec -> (dx, dy)）
SPEC_BBOX = {}

# 默认 bbox（米）：10cm × 10cm
DEFAULT_BBOX = (0.10, 0.10)


class LayoutOverflowError(Exception):
    """桌面空间不足以摆放所有小件时抛出"""
    pass


# ── 原有常量 ─────────────────────────────────────────────────────────────

# 多实体位置分散策略：确保同场景多个实体不会重叠
# 每个实体的位置范围之间有足够的间隔（至少0.1m）
ENTITY_POSITION_RANGES = [
    ([0.05, 0.15], [-0.15, -0.05]),   # 玻璃棒位置
    ([0.35, 0.45], [-0.05, 0.05]),    # 容器位置（与玻璃棒间隔>0.2m）
    ([0.15, 0.25], [0.05, 0.15]),     # 备用位置1
    ([0.25, 0.35], [0.05, 0.15]),     # 备用位置2
    ([0.05, 0.15], [-0.05, 0.05]),    # 备用位置3
    ([0.35, 0.45], [-0.15, -0.05]),   # 备用位置4
]

# ── 大件/小件分类与朝向控制 ───────────────────────────────────────────────

# 大件白名单：远离机械臂 + 需要门/把手朝向机械臂
FIXTURE_WITH_HANDLE_CLASSES = {
    "DryingBox",
    "ContainerWithDrawer",   # 覆盖 cabinet 和 drawer
}

# 大件朝向：绕 z 轴旋转，使门/把手朝向机械臂（world -y 方向）
# DryingBox:  yaw=π/2（90°），让按钮/门把手正对机器人
# ContainerWithDrawer:  原始方向已对，无需旋转
FIXTURE_HANDLE_YAW = {
    "DryingBox": np.pi / 2,
    "ContainerWithDrawer": 0.0,
}

# 小件位置区间：靠近机械臂
# x: 全宽 [-0.30, +0.30] 随机（左右分布）
# y: [-0.05, 0.25]，偏近端（robot base 在 y=-0.4）
# 与大件之间留 0.15m 缓冲带（[0.25, 0.40]），防止物理碰撞
SMALL_LABWARE_RANGES = [
    ([-0.30, -0.15], [-0.05, 0.10]),   # 左侧偏前
    ([-0.15,  0.00], [-0.05, 0.10]),   # 中左偏前
    ([ 0.00,  0.15], [-0.05, 0.10]),   # 中右偏前
    ([ 0.15,  0.30], [-0.05, 0.10]),   # 右侧偏前
    ([-0.30, -0.15], [0.10, 0.25]),    # 左侧偏后
    ([-0.15,  0.00], [0.10, 0.25]),    # 中左偏后
    ([ 0.00,  0.15], [0.10, 0.25]),    # 中右偏后
    ([ 0.15,  0.30], [0.10, 0.25]),    # 右侧偏后
]

# 大件位置区间：远离机械臂
# x: 全宽 [-0.30, +0.30] 随机（左右分布）
# y: [0.40, 0.45]，远端（与缓冲带 [0.25, 0.40] 隔开）
FIXTURE_RANGES = [
    ([-0.30, -0.15], [0.40, 0.45]),   # 左侧远端
    ([-0.15,  0.00], [0.40, 0.45]),   # 中左远端
    ([ 0.00,  0.15], [0.40, 0.45]),   # 中右远端
    ([ 0.15,  0.30], [0.40, 0.45]),   # 右侧远端
]

# 固定位置表：key 为 class_name，value 为 (x, y)，z 始终为 0.8
# 用于需要精确定位的物体（如 drying_box 由视觉标定过）
FIXED_POSITIONS = {
    "DryingBox": (0.30, 0.45),
    "ContainerWithDrawer": (0.0, 0.4),
}

# 容器类需要被固定到 arena 才能完成任务的清单
# （单手机械臂无法在被自由放置的物体上完成拧/插/按等需要底座稳定的操作）
ATTACH_TO_ARENA_CLASSES = {
    # 暂时禁用 attach_to_arena 以测试 drawer 问题
    "ContainerWithCap",
    "DryingBox",
    "ContainerWithDrawer",
}


@dataclass
class EntityLoadPlan:
    """描述一个实体应该如何被加载"""
    uid: str
    spec: str
    class_name: str
    load_mode: str          # "plain" | "liquid" | "subentity"
    method_name: str         # "load_objects" | "load_init_containers"
    properties: Dict = field(default_factory=dict)
    parent_spec: Optional[str] = None
    parent_class: Optional[str] = None  # subentity 的父容器 class_name
    binding: Optional[object] = None     # ParentBinding（subentity 模式才有）
    position_index: int = 0  # 用于位置分散
    orientation_yaw: float = 0.0  # 仅大件使用，绕 z 轴 rad；小件默认为 0
    attach_to_arena: bool = False  # 加载后是否焊死到 arena
    subentity_position: list = field(default_factory=list)  # 子实体相对位置
    # ── 新增：bbox 感知布局 ──
    bbox: Tuple[float, float] = (0.10, 0.10)  # (dx, dy) 占地宽和高（米）
    bbox_dz: float = 0.10  # 高度（米）；用于 init_z = bbox_dz（避免细长物体自由落体反弹倾斜）
    region: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None  # ((xmin,xmax),(ymin,ymax))


def _append_plain_like_plan(
    plans: List[EntityLoadPlan],
    uid: str,
    spec: str,
    class_name: str,
    properties: Dict,
    small_counter: int,
    fixture_counter: int,
    attach_to_arena: bool = False,
) -> None:
    """
    为 plain/liquid 实体构建 EntityLoadPlan，并根据 class_name 选取对应的位置表和朝向。

    大件走 FIXTURE_RANGES（远离机械臂）并设置 orientation_yaw；
    小件走 SMALL_LABWARE_RANGES（靠近机械臂），无朝向。
    """
    if class_name in FIXTURE_WITH_HANDLE_CLASSES:
        pos_index = fixture_counter
        yaw = FIXTURE_HANDLE_YAW[class_name]
    else:
        pos_index = small_counter
        yaw = 0.0

    plans.append(EntityLoadPlan(
        uid=uid,
        spec=spec,
        class_name=class_name,
        load_mode="liquid" if "solution" in properties else "plain",
        method_name="load_objects",
        properties=properties,
        position_index=pos_index,
        orientation_yaw=yaw,
        attach_to_arena=attach_to_arena,
    ))


# ── Bbox 读取函数 ───────────────────────────────────────────────────────
def _resolve_abs_xml(xml_path: str) -> str:
    """把相对路径解析为绝对路径（找不到就原样返回）"""
    if not xml_path:
        return ""
    if os.path.isabs(xml_path):
        return xml_path
    vlabench_root = os.environ.get("SCIHORIZON_ELAB_ROOT", "")
    if vlabench_root:
        # constant.py 的 xml_path 相对于 vlabench_root/scihorizon_elab/simulation/assets/
        # （即 vlabench_root = /path/to/SciHorizon-ELAB，资产在 scihorizon_elab/simulation/assets/ 下）
        elab_root = os.path.join(vlabench_root, "scihorizon_elab")
        for prefix in (
            os.path.join(elab_root, "simulation", "assets"),
            os.path.join(vlabench_root, "simulation", "assets"),
            os.path.join(vlabench_root, "assets"),
            vlabench_root,
        ):
            cand = os.path.join(prefix, xml_path)
            if os.path.exists(cand):
                return cand
    return xml_path


def _read_bbox_from_xml_comment(xml_path: str):
    """
    从 XML 的 <!-- @bbox dx=.. dy=.. dz=.. --> 注释读取占地尺寸。
    返回 (dx, dy) 或 None（dz 单独读）。
    """
    abs_xml = _resolve_abs_xml(xml_path)
    try:
        with open(abs_xml, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    m = re.search(r'@bbox\s+dx=([\d.]+)\s+dy=([\d.]+)', content)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    return None


def _read_bbox_dz_from_xml_comment(xml_path: str) -> Optional[float]:
    """从 XML 的 <!-- @bbox dx=.. dy=.. dz=.. --> 注释读取 dz（高度，米）。

    dz 用于决定 init_z：细长物体用 dz 避免从 0.8m 自由落体反弹倾斜。
    """
    abs_xml = _resolve_abs_xml(xml_path)
    try:
        with open(abs_xml, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None
    m = re.search(r'@bbox\s+dx=[\d.]+\s+dy=[\d.]+\s+dz=([\d.]+)', content)
    if m:
        return float(m.group(1))
    return None


# bbox 合理性校验常量
MIN_VALID_BBOX = 0.01   # 1cm（最小合理尺寸）
MAX_VALID_BBOX = 0.50   # 50cm（最大合理尺寸，超出则为数据错误）


def extract_bbox(xml_path: str, spec: str = "") -> Tuple[float, float]:
    """
    读取优先级：XML @bbox 注释 > SPEC_BBOX 注册表 > DEFAULT_BBOX。
    缺 @bbox 注释时发 warning，并对返回值做合理性校验。
    返回 (dx, dy)。
    """
    bbox = _read_bbox_from_xml_comment(xml_path)
    source = "XML @bbox"
    if bbox is None and spec and spec in SPEC_BBOX:
        bbox = SPEC_BBOX[spec]
        source = "SPEC_BBOX"
    if bbox is None:
        logger.warning(
            f"[extract_bbox] {spec or xml_path} 缺 @bbox 注释且 SPEC_BBOX 无注册，"
            f"fallback 到 {DEFAULT_BBOX}"
        )
        bbox = DEFAULT_BBOX
        source = "DEFAULT_BBOX (fallback)"
    dx, dy = bbox
    # 合理性校验
    if not (MIN_VALID_BBOX <= dx <= MAX_VALID_BBOX and
            MIN_VALID_BBOX <= dy <= MAX_VALID_BBOX):
        logger.warning(
            f"[extract_bbox] {spec or xml_path} bbox={bbox} ({source}) 超出合理范围 "
            f"[{MIN_VALID_BBOX}, {MAX_VALID_BBOX}]，仍按原值使用"
        )
    work_w = WORK_AREA["x_max"] - WORK_AREA["x_min"]
    work_h = WORK_AREA["y_max"] - WORK_AREA["y_min"]
    if dx > work_w * 0.95 or dy > work_h * 0.95:
        logger.warning(
            f"[extract_bbox] {spec or xml_path} bbox={bbox} 接近工作区尺寸 "
            f"({work_w:.3f} x {work_h:.3f}m)，可能无法与其他物体共存"
        )
    return bbox


# ── 布局算法：纯 BLF + 中心平移 ───────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
# 布局算法：CP-SAT 主算法 + MaxRects 兜底
# ══════════════════════════════════════════════════════════════════════════════

def _build_pert_max(plans_with_bbox):
    """计算所有物体中最大的扰动幅度（用于边界 buffer）"""
    max_pert = 0.01  # 最小 1cm
    for _, dx, dy in plans_with_bbox:
        pert_x = min(max(dx * 0.3, 0.01), 0.02)
        pert_y = min(max(dy * 0.3, 0.01), 0.02)
        max_pert = max(max_pert, pert_x, pert_y)
    return max_pert


# ── Part B：CP-SAT 主算法 ────────────────────────────────────────────────────

def _cpsat_layout(plans_with_bbox):
    """
    使用 Google OR-Tools CP-SAT 求解二维矩形布局（允许90°旋转）。

    关键设计：
    - AddNoOverlap2D：精确保证所有矩形两两不相交
    - 边界约束：中心含 pert buffer 后仍在工作区内
    - 目标：最大化布局质量分数（居中性 + 靠机械臂偏好 + 不旋转偏好）
    """
    from ortools.sat.python import cp_model

    n = len(plans_with_bbox)
    if n == 0:
        return {}

    SCALE = 2000   # 0.5mm 精度
    MARGIN_Q = int(LAYOUT_MARGIN * SCALE)  # 60 单位

    # 计算每个物体的扰动幅度 pert = min(max(dx*0.3, 0.01), 0.02)
    pert_mm = []
    for _, dx, dy in plans_with_bbox:
        pert_x_raw = min(dx * 0.3, 0.02)
        pert_y_raw = min(dy * 0.3, 0.02)
        if pert_x_raw < 0.01:
            pert_x_raw = 0.01
        if pert_y_raw < 0.01:
            pert_y_raw = 0.01
        pert_mm.append((int(round(pert_x_raw * SCALE)), int(round(pert_y_raw * SCALE))))

    x_min_q = int(WORK_AREA["x_min"] * SCALE)
    x_max_q = int(WORK_AREA["x_max"] * SCALE)
    y_min_q = int(WORK_AREA["y_min"] * SCALE)
    y_max_q = int(WORK_AREA["y_max"] * SCALE)
    tx_q = int(TARGET_CENTER[0] * SCALE)
    ty_q = int(TARGET_CENTER[1] * SCALE)

    model = cp_model.CpModel()
    x_vars, y_vars, rot_vars = [], [], []
    dx_q, dy_q = [], []

    for i, (_, dx, dy) in enumerate(plans_with_bbox):
        dxi = int(round(dx * SCALE))
        dyi = int(round(dy * SCALE))
        dx_q.append(dxi)
        dy_q.append(dyi)
        ptx, pty = pert_mm[i]

        # 中心范围（含 pert 后仍在边界内）
        cx_min = x_min_q + (dxi // 2) + ptx
        cx_max = x_max_q - (dxi // 2) - ptx
        cy_min = y_min_q + (dyi // 2) + pty
        cy_max = y_max_q - (dyi // 2) - pty
        x_vars.append(model.NewIntVar(cx_min, cx_max, f"x_{i}"))
        y_vars.append(model.NewIntVar(cy_min, cy_max, f"y_{i}"))
        rot_vars.append(model.NewBoolVar(f"rot_{i}"))

    # NoOverlap：4 分离方向 BoolVar + AddBoolOr
    # 分离量 = 物体半宽和 + margin + 双向扰动 buffer，保证加 randomness 后仍不穿透
    for i in range(n):
        for j in range(i + 1, n):
            left_ij   = model.NewBoolVar(f"L_{i}_{j}")   # i 在 j 左边
            right_ij  = model.NewBoolVar(f"R_{i}_{j}")   # i 在 j 右边
            below_ij  = model.NewBoolVar(f"B_{i}_{j}")   # i 在 j 下边
            above_ij  = model.NewBoolVar(f"A_{i}_{j}")   # i 在 j 上边
            model.AddBoolOr([left_ij, right_ij, below_ij, above_ij])

            dxi, dyi = dx_q[i], dy_q[i]
            dxj, dyj = dx_q[j], dy_q[j]
            # w_i, h_i = 旋转后的尺寸（整数）
            w_i = dxi + rot_vars[i] * (dyi - dxi)
            h_i = dyi - rot_vars[i] * (dyi - dxi)
            w_j = dxj + rot_vars[j] * (dyj - dxj)
            h_j = dyj - rot_vars[j] * (dyj - dxj)

            # 分离 buffer：margin + 两个物体各自 x/y 方向的扰动幅度
            ptx_i, pty_i = pert_mm[i]
            ptx_j, pty_j = pert_mm[j]
            sep_x = MARGIN_Q + 2 * (ptx_i + ptx_j)
            sep_y = MARGIN_Q + 2 * (pty_i + pty_j)

            # i 在 j 左边: x_j - x_i >= (w_i + w_j)/2 + sep_x（乘2消除/2）
            model.Add(2 * x_vars[j] - 2 * x_vars[i] >= w_i + w_j + 2 * sep_x).OnlyEnforceIf(left_ij)
            model.Add(2 * x_vars[i] - 2 * x_vars[j] >= w_i + w_j + 2 * sep_x).OnlyEnforceIf(right_ij)
            model.Add(2 * y_vars[j] - 2 * y_vars[i] >= h_i + h_j + 2 * sep_y).OnlyEnforceIf(below_ij)
            model.Add(2 * y_vars[i] - 2 * y_vars[j] >= h_i + h_j + 2 * sep_y).OnlyEnforceIf(above_ij)

    # 目标函数
    W_CENTER, W_Y_LOW, W_NOROT = 10, 5, 2
    abs_x, abs_y = [], []
    for i in range(n):
        ax = model.NewIntVar(0, 999999, f"absx_{i}")
        ay = model.NewIntVar(0, 999999, f"absy_{i}")
        model.AddAbsEquality(ax, x_vars[i] - tx_q)
        model.AddAbsEquality(ay, y_vars[i] - ty_q)
        abs_x.append(ax); abs_y.append(ay)

    objective = [
        -W_CENTER * (abs_x[i] + abs_y[i])
        + W_Y_LOW * (ty_q - y_vars[i])
        - W_NOROT * rot_vars[i] * 1000
        for i in range(n)
    ]
    model.Maximize(sum(objective))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 1.0
    solver.parameters.num_search_workers = 4
    solver.parameters.log_search_progress = False
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        logger.warning(f"[Layout] CP-SAT 求解失败: {solver.StatusName(status)}")
        return None

    out = {}
    for i, (uid, dx, dy) in enumerate(plans_with_bbox):
        cx = solver.Value(x_vars[i]) / SCALE
        cy = solver.Value(y_vars[i]) / SCALE
        rot = bool(solver.Value(rot_vars[i]))
        w_eff = dy if rot else dx
        h_eff = dx if rot else dy
        out[uid] = ((cx - w_eff / 2, cx + w_eff / 2),
                    (cy - h_eff / 2, cy + h_eff / 2))

    logger.info(f"[Layout] CP-SAT 状态: {solver.StatusName(status)}")
    return out


# ── Part C：MaxRects 兜底算法 ──────────────────────────────────────────

class MaxRects:
    """
    简化的 MaxRects 数据结构，支持 Bottom-Left-Fit 放置 + 90° 旋转尝试。

    关键方法：
        insert(w, h, margin) -> ((px, py, pw, ph), rot_used) | None
    """

    def __init__(self, width: float, height: float):
        self.W = width
        self.H = height
        # 每个元素: (x, y, w, h) — 空白矩形的左下角坐标和尺寸
        self.free_rects = [(0.0, 0.0, width, height)]
        self.placed = []

    def insert(self, w: float, h: float, margin: float):
        """
        尝试在空白区域中找一个 BLF 位置放下 w×h（含 margin）。
        先试原方向，失败再试旋转。
        Returns: ((px, py, w, h), rotated: bool) 或 None
        """
        r = self._find_bl(w + 2 * margin, h + 2 * margin)
        if r:
            self._commit(r, w + 2 * margin, h + 2 * margin)
            return ((r[0] + margin, r[1] + margin, w, h), False)
        if abs(w - h) > 1e-6:
            r = self._find_bl(h + 2 * margin, w + 2 * margin)
            if r:
                self._commit(r, h + 2 * margin, w + 2 * margin)
                return ((r[0] + margin, r[1] + margin, h, w), True)
        return None

    def _find_bl(self, w: float, h: float):
        """Bottom-Left-Fit：y 最小优先，y 相同时 x 最小"""
        best, best_y, best_x = None, float('inf'), float('inf')
        for fx, fy, fw, fh in self.free_rects:
            if fw >= w and fh >= h:
                if fy < best_y or (fy == best_y and fx < best_x):
                    best = (fx, fy, fw, fh)
                    best_y, best_x = fy, fx
        return best

    def _commit(self, rect, w: float, h: float):
        """放置后用标准 MaxRects 切分规则更新 free_rects"""
        x, y, _, _ = rect
        self.placed.append((x, y, w, h))
        new_free = []
        for fx, fy, fw, fh in self.free_rects:
            # 完全不相交则保留
            if x + w <= fx or fx + fw <= x or y + h <= fy or fy + fh <= y:
                new_free.append((fx, fy, fw, fh))
                continue
            # 左上剩余
            if x > fx:
                new_free.append((fx, fy, x - fx, fh))
            # 右上剩余
            if x + w < fx + fw:
                new_free.append((x + w, fy, fx + fw - x - w, fh))
            # 左下剩余
            if y > fy:
                new_free.append((fx, fy, fw, y - fy))
            # 右下剩余
            if y + h < fy + fh:
                new_free.append((fx, y + h, fw, fy + fh - y - h))
        # 去除被完全包含的矩形
        self.free_rects = [r for r in new_free
                           if r[2] > 1e-6 and r[3] > 1e-6
                           and not self._is_contained(r, new_free)]

    @staticmethod
    def _is_contained(r, rects):
        """检查 r 是否被 rects 中某个矩形完全包含"""
        rx, ry, rw, rh = r
        for fx, fy, fw, fh in rects:
            if id((fx, fy, fw, fh)) != id(r):
                if rx >= fx and ry >= fy and rx + rw <= fx + fw and ry + rh <= fy + fh:
                    return True
        return False


def _maxrects_layout(plans_with_bbox):
    """
    MaxRects 兜底：尝试多种排序策略，取布局质量最优的结果。

    排序策略：面积降序、最长边降序、最短边降序、随机（两种种子）
    评分 = 群中心距 TARGET_CENTER 距离 - 0.1 * 边缘 buffer 总和
    """
    if not plans_with_bbox:
        return {}

    # 计算有效工作区（去掉最大 pert buffer）
    pert_max = _build_pert_max(plans_with_bbox)
    eff_x_min = WORK_AREA["x_min"] + LAYOUT_MARGIN + pert_max
    eff_y_min = WORK_AREA["y_min"] + LAYOUT_MARGIN + pert_max
    eff_x_max = WORK_AREA["x_max"] - LAYOUT_MARGIN - pert_max
    eff_y_max = WORK_AREA["y_max"] - LAYOUT_MARGIN - pert_max
    W = eff_x_max - eff_x_min
    H = eff_y_max - eff_y_min

    if W <= 0 or H <= 0:
        logger.error("[Layout] 有效工作区为非正值，请检查 WORK_AREA 和 LAYOUT_MARGIN")
        return None

    strategies = [
        ("area_desc",  lambda p: -p[1] * p[2]),
        ("long_desc",  lambda p: -max(p[1], p[2])),
        ("short_desc", lambda p: -min(p[1], p[2])),
        ("random_1",   None),
        ("random_2",   None),
    ]

    best_score = float('inf')
    best_result = None

    for name, key in strategies:
        if key is None:
            items = list(plans_with_bbox)
            random.Random(abs(hash(name)) % 0xFFFF).shuffle(items)
        else:
            items = sorted(plans_with_bbox, key=key)

        mr = MaxRects(W, H)
        placed = {}
        ok = True
        for uid, dx, dy in items:
            # margin 含物体自身扰动 buffer（另一侧的扰动由相邻物体的 margin 承担）
            pert = min(max(dx * 0.3, 0.01), 0.02) / 2 + min(max(dy * 0.3, 0.01), 0.02) / 2
            r = mr.insert(dx, dy, LAYOUT_MARGIN + pert)
            if r is None:
                ok = False
                break
            (px, py, pw, ph), rot = r
            placed[uid] = (
                (eff_x_min + px, eff_x_min + px + pw),
                (eff_y_min + py, eff_y_min + py + ph),
                rot,
            )

        if not ok:
            continue

        # 评分：群中心距 TARGET_CENTER 距离越小越好，边缘 buffer 总和越大越好
        cxs = [(placed[u][0][0] + placed[u][0][1]) / 2 for u in placed]
        cys = [(placed[u][1][0] + placed[u][1][1]) / 2 for u in placed]
        cx = sum(cxs) / len(cxs)
        cy = sum(cys) / len(cys)
        dist = ((cx - TARGET_CENTER[0]) ** 2 + (cy - TARGET_CENTER[1]) ** 2) ** 0.5

        edge_buf = 0.0
        for uid, (dx, dy) in [(u, (plans_with_bbox[i][1], plans_with_bbox[i][2]))
                               for i, u in enumerate(placed)]:
            (xmin, xmax), (ymin, ymax) = placed[uid][:2]
            edge_buf += min(
                xmin - WORK_AREA["x_min"],
                WORK_AREA["x_max"] - xmax,
                ymin - WORK_AREA["y_min"],
                WORK_AREA["y_max"] - ymax,
            )

        score = dist - 0.1 * edge_buf
        if score < best_score:
            best_score = score
            best_result = {u: placed[u][:2] for u in placed}

    return best_result


# ── Part D：compute_layout_regions 入口 ─────────────────────────────────

def compute_layout_regions(plans_with_bbox):
    """
    三层兜底布局算法：
      1. CP-SAT (ortools)：精确求解，允许 90° 旋转，优化布局质量
      2. MaxRects：兜底，不旋转时通常也足够好
      3. raise LayoutOverflowError

    Args:
        plans_with_bbox: List[(uid, dx, dy)]，dx/dy 单位为米

    Returns:
        {uid: ((xmin, xmax), (ymin, ymax))}
    """
    if not plans_with_bbox:
        return {}

    # 第一层：CP-SAT
    try:
        regions = _cpsat_layout(plans_with_bbox)
        if regions:
            logger.info(f"[Layout] CP-SAT 成功，{len(regions)}/{len(plans_with_bbox)} 物体")
            return regions
    except ImportError:
        logger.warning("[Layout] ortools 未安装，使用 MaxRects 兜底")
    except Exception as e:
        logger.warning(f"[Layout] CP-SAT 异常: {e}，使用 MaxRects 兜底")

    # 第二层：MaxRects 兜底
    regions = _maxrects_layout(plans_with_bbox)
    if regions:
        expected_uids = {u for u, _, _ in plans_with_bbox}
        placed_count = len([u for u in regions if u in expected_uids])
        logger.info(f"[Layout] MaxRects 兜底成功，{placed_count}/{len(plans_with_bbox)} 物体")
        return regions

    raise LayoutOverflowError(
        f"桌面空间不足：{len(plans_with_bbox)} 个物体无法全部放下"
    )


# ── 原有函数 ─────────────────────────────────────────────────────────────
def plan_entity_loading(
    instances: List[Dict],
    asset_status: Dict,
) -> List[EntityLoadPlan]:
    """
    为每个物理实体生成加载计划。

    简化规则：
      1. 跳过 is_physical=False 的实体
      2. ChemistryTube → subentity 模式，自动注入 tube_stand 父容器
      3. 带 solution → liquid 模式
      4. 其余 → plain 模式
      所有实体统一放到 load_objects（除 TubeStand 放到 load_init_containers）
    """
    plans: List[EntityLoadPlan] = []
    emitted_init_parents: set = set()  # 已生成 init-container 计划的父容器 spec
    small_counter = 0    # 小件位置序号（靠近机械臂）
    fixture_counter = 0  # 大件位置序号（远离机械臂）

    # 第一遍扫描：找出已有的父容器实例（任意父容器，不限于 TubeStand）
    #   key = 父容器 spec, value = 用户已显式摆放的 uid
    existing_parent_uids: Dict[str, str] = {}
    parent_specs_needed: set = set()
    for inst in instances:
        if not inst.get("is_physical", True):
            continue
        binding = _resolve_binding(inst.get("spec", ""))
        if binding is not None:
            parent_specs_needed.add(binding.parent_spec)

    for inst in instances:
        if not inst.get("is_physical", True):
            continue
        spec = inst.get("spec", "")
        if spec in parent_specs_needed:
            existing_parent_uids[spec] = inst["uid"]
        info = asset_status.get(inst.get("uid", ""), {})
        if info.get("class_name") in {"TubeStand", "PipetteStand"}:
            # 已显式声明的父容器类（不依赖 spec 推断）
            existing_parent_uids.setdefault(spec, inst["uid"])

    def _ensure_parent_plan(parent_uid: str, parent_spec: str, parent_class: str) -> None:
        """为 subentity 的父容器补一个 init-container 计划（按父容器 spec 去重）。"""
        if parent_spec in emitted_init_parents:
            return
        plans.append(EntityLoadPlan(
            uid=parent_uid, spec=parent_spec,
            class_name=parent_class,
            load_mode="plain",
            method_name="load_init_containers",
        ))
        emitted_init_parents.add(parent_spec)

    for inst in instances:
        if not inst.get("is_physical", True):
            continue

        uid = inst["uid"]
        spec = inst.get("spec", "")
        info = asset_status.get(uid, {})
        class_name = info.get("class_name", "CommonGraspedEntity")
        properties = info.get("properties", {})

        # SubEntity: 由实体类 get_parent_container() 声明
        binding = _resolve_binding(spec)
        if binding is not None:
            parent_spec = binding.parent_spec
            parent_class = binding.parent_class
            parent_uid = existing_parent_uids.get(parent_spec, parent_spec)
            _inject_parent_asset(asset_status, parent_spec, parent_class)
            _ensure_parent_plan(parent_uid, parent_spec, parent_class)

            plans.append(EntityLoadPlan(
                uid=uid, spec=spec, class_name=class_name,
                load_mode="subentity", method_name="load_objects",
                properties=properties, parent_spec=parent_spec,
                binding=binding,
            ))
            continue

        # 跳过已被作为父容器使用的实例（任何父容器）
        if spec in emitted_init_parents or spec in existing_parent_uids:
            if spec in parent_specs_needed:
                continue

        # Liquid: 带 solution
        elif "solution" in properties:
            _append_plain_like_plan(
                plans, uid, spec, class_name, properties,
                small_counter, fixture_counter, attach_to_arena=(class_name in ATTACH_TO_ARENA_CLASSES),
            )
            if class_name in FIXTURE_WITH_HANDLE_CLASSES:
                fixture_counter += 1
            else:
                small_counter += 1

        # Plain: 所有其他实体（统一走 load_objects）
        else:
            _append_plain_like_plan(
                plans, uid, spec, class_name, properties,
                small_counter, fixture_counter, attach_to_arena=(class_name in ATTACH_TO_ARENA_CLASSES),
            )
            if class_name in FIXTURE_WITH_HANDLE_CLASSES:
                fixture_counter += 1
            else:
                small_counter += 1

    # ── Bbox + 统一布局规划（plain + liquid + init_container 共同参与 BLF）──
    bbox_cache: Dict[str, Tuple[float, float]] = {}
    dz_cache: Dict[str, float] = {}
    all_desktop = []
    for plan in plans:
        # 跳过 subentity、大件 fixture
        if plan.load_mode not in ("plain", "liquid"):
            continue
        # 跳过 FIXTURE_WITH_HANDLE_CLASSES（大件 fixture 有固定位置）
        if plan.class_name in FIXTURE_WITH_HANDLE_CLASSES:
            continue

        if plan.spec not in bbox_cache:
            xml_path = asset_status.get(plan.uid, {}).get("xml_path", "")
            bbox_cache[plan.spec] = extract_bbox(xml_path, plan.spec)
        plan.bbox = bbox_cache[plan.spec]
        # 同时读取 dz，用于决定 init_z（避免细长物体从 0.8m 自由落体反弹倾斜）
        if plan.spec not in dz_cache:
            xml_path = asset_status.get(plan.uid, {}).get("xml_path", "")
            dz = _read_bbox_dz_from_xml_comment(xml_path)
            dz_cache[plan.spec] = dz if dz is not None else 0.10
        plan.bbox_dz = dz_cache[plan.spec]
        all_desktop.append(plan)

    if all_desktop:
        try:
            regions = compute_layout_regions(
                [(p.uid, p.bbox[0], p.bbox[1]) for p in all_desktop]
            )
            for plan in all_desktop:
                plan.region = regions.get(plan.uid)
            logger.info(
                f"[Entity Loader] 统一布局规划: {len(all_desktop)} 个桌面物体已分配 region"
            )
        except LayoutOverflowError as e:
            logger.error(f"[Entity Loader] 布局失败: {e}")
            raise

    return plans


def _inject_parent_asset(asset_status: Dict, parent_spec: str, parent_class: str) -> None:
    """根据 ParentBinding 把父容器注入 asset_status（如果不在 name2class_xml 中）。
    xml_path 直接复用常量注册表，无需每个父容器单独写一个函数。
    """
    if parent_spec in asset_status:
        return
    from scihorizon_elab.simulation.configs.constant import name2class_xml
    asset_status[parent_spec] = {
        "xml_path": name2class_xml[parent_spec][-1],
        "class_name": parent_class,
        "properties": {},
    }


def _resolve_binding(spec: str):
    """根据 spec 查询实体类的 get_parent_container()。惰性导入避免循环依赖。"""
    try:
        from scihorizon_elab.simulation.configs.constant import name2class_xml
    except Exception:
        return None
    if spec not in name2class_xml:
        return None
    cls = name2class_xml[spec][0]
    if cls is None:
        return None
    return cls.get_parent_container()


def generate_load_methods(plans: List[EntityLoadPlan], asset_status: Dict) -> tuple:
    """
    从加载计划生成 load 方法代码。

    Returns:
        (load_methods_code: str, extra_imports: str|None, extra_constants: str|None)
    """
    # 按 method_name 分组
    methods: Dict[str, List[EntityLoadPlan]] = {}
    for plan in plans:
        methods.setdefault(plan.method_name, []).append(plan)

    code_parts = []
    needs_name2class_xml = False
    needs_tube_constants = False
    needs_pipette_stand_constants = False

    # 只处理 load_init_containers 和 load_objects（不再生成 load_containers）
    for method_name in ["load_init_containers", "load_objects"]:
        method_plans = methods.get(method_name, [])
        if not method_plans:
            continue
        code, flags = _generate_method(method_name, method_plans)
        code_parts.append(code)
        needs_name2class_xml = needs_name2class_xml or flags.get("needs_name2class_xml", False)
        needs_tube_constants = needs_tube_constants or flags.get("needs_tube_constants", False)
        needs_pipette_stand_constants = needs_pipette_stand_constants or flags.get("needs_pipette_stand_constants", False)

    load_methods_code = "\n".join(code_parts)

    extra_imports = None
    if needs_name2class_xml:
        extra_imports = "from scihorizon_elab.simulation.configs.constant import name2class_xml"

    extra_constants_lines = []
    if needs_tube_constants:
        extra_constants_lines.append(f"relative_col_pos = {TUBE_COL_POS}")
        extra_constants_lines.append(f"relative_row_pos = {TUBE_ROW_POS}")
    if needs_pipette_stand_constants:
        extra_constants_lines.append(f"relative_pipette_stand_col_pos = {PIPETTE_STAND_COL_POS}")
        extra_constants_lines.append(f"relative_pipette_stand_row_pos = {PIPETTE_STAND_ROW_POS}")
    extra_constants = "\n".join(extra_constants_lines) + "\n" if extra_constants_lines else None

    return load_methods_code, extra_imports, extra_constants


def _generate_method(method_name: str, plans: List[EntityLoadPlan]) -> tuple:
    """生成单个 load 方法"""
    flags = {"needs_name2class_xml": False, "needs_tube_constants": False, "needs_pipette_stand_constants": False}

    if method_name == "load_init_containers":
        return _gen_init_containers(plans, flags)
    return _gen_objects(plans, flags)


# ── load_init_containers ──────────────────────────────────────────────────

def _gen_init_containers(plans: List[EntityLoadPlan], flags: Dict) -> str:
    """
    生成 load_init_containers 方法。
    用于 ChemistryTube 的父容器（TubeStand）。
    如果 init_container plan 有 region（统一 BLF 布局），使用 region 的 x/y 范围。
    """
    def _region_pos(uid, plans):
        for p in plans:
            if p.uid == uid and p.method_name == "load_init_containers" and p.region is not None:
                (xmin, xmax), (ymin, ymax) = p.region
                return f"random.uniform({xmin:.4f}, {xmax:.4f}), random.uniform({ymin:.4f}, {ymax:.4f})"
        # 没有 region 时不应该发生（CP-SAT 应该已为 init_container 分配了 region）
        # 回退到工作区中央偏左上（保守位置）
        return "random.uniform(-0.30, -0.20), random.uniform(0.10, 0.20)"
    lines = ["    def load_init_containers(self, init_container):"]

    for plan in plans:
        # 每个 init_container plan 都直接对应一个父容器注册块
        # （plan 来自 plan_entity_loading() 的 _ensure_parent_plan，已按 spec 去重）
        parent_spec = plan.spec
        parent_class = plan.class_name
        parent_uid = plan.uid
        lines += [
            f"        if init_container is None or init_container == \"{parent_spec}\":",
            f"            container_config = dict(",
            f"                name=\"{parent_uid}\",",
            f"                xml_path=name2class_xml[\"{parent_spec}\"][-1],",
            f"                position=[{_region_pos(parent_uid, plans)}, 0.8],",
            f"            )",
            f"            container_config[\"class\"] = \"{parent_class}\"",
            f"            self.config[\"task\"][\"components\"].append(container_config)",
        ]

    lines.append("")
    flags["needs_name2class_xml"] = True
    return "\n".join(lines), flags


# ── load_objects ─────────────────────────────────────────────────────────

def _gen_objects(plans: List[EntityLoadPlan], flags: Dict) -> str:
    """生成 load_objects 方法，支持 plain / liquid / subentity"""
    lines = ["    def load_objects(self, target_entity):"]

    # 预分配 hole_grid 孔位：所有 binding.params.preallocate_holes=True 的 subentity
    # 按 parent_spec 分组，组内不重复分配孔位
    hole_assignments: Dict[str, int] = {}  # uid -> hole_index
    hole_group: Dict[str, List[EntityLoadPlan]] = {}  # parent_spec -> [plan, ...]
    for plan in plans:
        binding = getattr(plan, "binding", None)
        if (plan.load_mode == "subentity"
                and binding is not None
                and binding.placement == "hole_grid"
                and binding.params.get("preallocate_holes")):
            parent = getattr(plan, "parent_spec", None) or "default"
            hole_group.setdefault(parent, []).append(plan)

    for parent_spec, hole_plans in hole_group.items():
        n = len(hole_plans)
        max_holes = len(TUBE_COL_POS) * len(TUBE_ROW_POS)
        if n > max_holes:
            logger.warning(f"[Entity Loader] hole_grid 数量 {n} 超过孔位数 {max_holes}（父={parent_spec}），部分会重叠")
        hole_indices = list(range(min(n, max_holes)))
        random.shuffle(hole_indices)
        for i, plan in enumerate(hole_plans):
            hole_assignments[plan.uid] = hole_indices[i] if i < len(hole_indices) else 0

    for plan in plans:
        if plan.load_mode == "subentity":
            hole_idx = hole_assignments.get(plan.uid)
            lines += _code_subentity(plan, flags, hole_idx=hole_idx)
        elif plan.load_mode == "liquid":
            lines += _code_liquid(plan, flags)
        else:
            lines += _code_plain(plan, flags)

    # 覆盖 target_entity 为第一个 load_objects 计划的 uid，
    # 确保 self.target_entity 与 self.entities 中的 key 一致
    first_uid = next((p.uid for p in plans), None)
    if first_uid:
        lines.append(f'        self.target_entity = "{first_uid}"')
        lines.append("")

    flags["needs_name2class_xml"] = True
    return "\n".join(lines), flags


def _code_plain(plan: EntityLoadPlan, flags: Dict) -> List[str]:
    # init_z：让物体的 grasppoint（细长物体 grasppoint 在中部 z≈bbox_dz/2）落在机器人工作区中央。
    # 细长物体 init_z 调到使 grasppoint ≈ 0.95（工作区中央），避免 grasppoint 偏离工作区。
    if plan.bbox_dz > 0.20:
        # grasppoint 在物体中部 ≈ bbox_dz/2；目标 grasppoint ≈ 0.95；init_z ≈ 0.95 - bbox_dz/2
        init_z = max(round(0.95 - plan.bbox_dz / 2, 4), 0.6)
    else:
        init_z = 0.8
    # 优先：使用新布局算法的 region
    if plan.region is not None:
        (x_min, x_max), (y_min, y_max) = plan.region
        position_line = (
            f'            position=[random.uniform({x_min:.4f}, {x_max:.4f}), '
            f'random.uniform({y_min:.4f}, {y_max:.4f}), {init_z}],'
        )
    # 固定位置优先（由视觉标定过的物体）
    elif plan.class_name in FIXED_POSITIONS:
        fx, fy = FIXED_POSITIONS[plan.class_name]
        position_line = f'            position=[{fx}, {fy}, {init_z}],'
    else:
        if plan.class_name in FIXTURE_WITH_HANDLE_CLASSES:
            pos_table = FIXTURE_RANGES
        else:
            pos_table = SMALL_LABWARE_RANGES
        pos_range = pos_table[plan.position_index % len(pos_table)]
        position_line = (
            f'            position=[random.uniform({pos_range[0][0]}, {pos_range[0][1]}), '
            f'random.uniform({pos_range[1][0]}, {pos_range[1][1]}), {init_z}],'
        )

    # 随机扰动幅度：根据 bbox 尺寸计算（不超过 dx/dy 的 30%，最小 1cm）
    dx, dy = plan.bbox
    pert_x = min(max(dx * 0.3, 0.01), 0.02)
    pert_y = min(max(dy * 0.3, 0.01), 0.02)

    lines = [
        f'        obj_config = dict(',
        f'            name="{plan.uid}",',
        f'            xml_path=name2class_xml["{plan.spec}"][-1],',
        position_line,
        f'        )',
        f'        obj_config["class"] = "{plan.class_name}"',
    ]
    # 大件：门/把手朝向机械臂（绕 z 轴旋转，dict 构造完之后追加）
    if plan.orientation_yaw != 0.0:
        lines.append(f'        obj_config["orientation"] = [0, 0, {plan.orientation_yaw:.4f}]')
    lines.append(f'        obj_config["randomness"] = dict(pos=[{pert_x:.4f}, {pert_y:.4f}, 0], quat=[0, 0, 0.05])')
    if plan.attach_to_arena:
        lines.append(f'        obj_config["attach_to_arena"] = True')
    lines += [
        f'        self.config["task"]["components"].append(obj_config)',
        "",
    ]
    return lines


def _code_liquid(plan: EntityLoadPlan, flags: Dict) -> List[str]:
    solution_rgba = plan.properties.get("solution_rgba")
    solution = plan.properties.get("solution", plan.uid)

    # init_z：细长物体调高使 grasppoint ≈ 0.95；其它用 0.8 桌面通用高度
    if plan.bbox_dz > 0.20:
        init_z = max(round(0.95 - plan.bbox_dz / 2, 4), 0.6)
    else:
        init_z = 0.8

    # 优先：使用新布局算法的 region
    if plan.region is not None:
        (x_min, x_max), (y_min, y_max) = plan.region
        position_line = (
            f'            position=[random.uniform({x_min:.4f}, {x_max:.4f}), '
            f'random.uniform({y_min:.4f}, {y_max:.4f}), {init_z}],'
        )
    else:
        if plan.class_name in FIXTURE_WITH_HANDLE_CLASSES:
            pos_table = FIXTURE_RANGES
        else:
            pos_table = SMALL_LABWARE_RANGES
        pos_range = pos_table[plan.position_index % len(pos_table)]
        position_line = (
            f'            position=[random.uniform({pos_range[0][0]}, {pos_range[0][1]}), '
            f'random.uniform({pos_range[1][0]}, {pos_range[1][1]}), {init_z}],'
        )

    # 随机扰动幅度：根据 bbox 尺寸计算（不超过 dx/dy 的 30%，最小 1cm）
    dx, dy = plan.bbox
    pert_x = min(max(dx * 0.3, 0.01), 0.02)
    pert_y = min(max(dy * 0.3, 0.01), 0.02)

    lines = [
        f'        obj_config = dict(',
        f'            name="{plan.uid}",',
        f'            xml_path=name2class_xml["{plan.spec}"][-1],',
        position_line,
        f'            solution="{solution}",',
    ]
    if solution_rgba:
        lines.append(f'            solution_rgba={solution_rgba},')
    lines.append(f'        )')
    lines.append(f'        obj_config["class"] = "{plan.class_name}"')
    # 大件：门/把手朝向机械臂（绕 z 轴旋转，单独写赋值语句避免破坏 dict literal）
    if plan.orientation_yaw != 0.0:
        lines.append(f'        obj_config["orientation"] = [0, 0, {plan.orientation_yaw:.4f}]')
    lines.append(f'        obj_config["randomness"] = dict(pos=[{pert_x:.4f}, {pert_y:.4f}, 0], quat=[0, 0, 0.05])')
    if plan.attach_to_arena:
        lines.append(f'        obj_config["attach_to_arena"] = True')
    lines += [
        f'        self.config["task"]["components"].append(obj_config)',
        "",
    ]
    return lines


def _code_subentity(plan: EntityLoadPlan, flags: Dict, hole_idx: Optional[int] = None) -> List[str]:
    """生成子实体代码。

    摆放策略由 plan.binding.placement 决定（来自实体类的 get_parent_container()）：
      - "hole_grid": 试管架孔位网格（tube 预分配、pipette 随机）
      - "pipette_slot": pipettes_stand 顶部凹槽（带倾斜补偿的固定偏移）
      - "fixed": 无额外位置行（subentity 直接挂在父容器 init_pos 上）
    """
    solution_rgba = plan.properties.get("solution_rgba")
    # solution 字段仅在 properties 显式声明时输出（与 liquid 模式行为一致）
    solution = plan.properties.get("solution")
    local_z = (plan.binding.params.get("local_z", 0.05) if plan.binding else 0.05)

    # 通过 parent_spec 查找正确的父容器（不是用 [-1]，因为 subentity 可能在多个 plain 之后才添加）
    parent_spec = getattr(plan, "parent_spec", None)
    if parent_spec:
        find_parent = (
            f'        init_container_config = next('
            f'            c for c in self.config["task"]["components"]'
            f'            if c.get("name") == "{parent_spec}"'
            f'        )'
        )
    else:
        find_parent = '        init_container_config = self.config["task"]["components"][-1]'

    # 按 placement 策略生成位置行
    placement = plan.binding.placement if plan.binding else "fixed"
    if placement == "hole_grid":
        if plan.binding and plan.binding.params.get("preallocate_holes"):
            flags["needs_tube_constants"] = True
            col_idx = hole_idx // len(TUBE_ROW_POS)
            row_idx = hole_idx % len(TUBE_ROW_POS)
            pos_lines = [
                f"        col_pos = relative_col_pos[{col_idx}]",
                f"        row_pos = relative_row_pos[{row_idx}]",
                f"        pos = [col_pos, row_pos, {local_z}]",
            ]
        else:
            flags["needs_tube_constants"] = True
            pos_lines = [
                "        col_pos = random.choice(relative_col_pos)",
                "        row_pos = random.choice(relative_row_pos)",
                f"        pos = [col_pos, row_pos, {local_z}]",
            ]
    elif placement == "pipette_slot":
        flags["needs_pipette_stand_constants"] = True
        local_pos = plan.binding.params.get("local_pos", [0, 0, 0])
        pos_lines = [
            "        col_pos = random.choice(relative_pipette_stand_col_pos)",
            "        row_pos = random.choice(relative_pipette_stand_row_pos)",
            f"        pos = {local_pos}",
        ]
    else:  # "fixed"
        pos_lines = ["        pos = [0, 0, 0]"]

    # 子实体配置（solution 字段仅在 properties 中显式声明时输出）
    obj_lines = [
        f'        obj_config = dict(',
        f'            name="{plan.uid}",',
        f'            xml_path=name2class_xml["{plan.spec}"][-1],',
        f'            position=pos,',
    ]
    if solution is not None:
        obj_lines.insert(3, f'            solution="{solution}",')
    if solution_rgba:
        obj_lines.insert(4 if solution is not None else 3, f'            solution_rgba={solution_rgba},')
    obj_lines += [
        f'        )',
        f'        obj_config["class"] = "{plan.class_name}"',
        '        init_container_config["subentities"].append(obj_config)',
        "",
    ]
    return pos_lines + [find_parent,
                        '        if "subentities" not in init_container_config:',
                        '            init_container_config["subentities"] = []'] + obj_lines
