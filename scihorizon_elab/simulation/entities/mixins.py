"""
Mixin classes for SciHorizon-ELAB entities.
Each mixin represents a single capability that can be composed with others.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# GraspMixin - 可被抓取
# =============================================================================

class GraspMixin:
    """
    可被机械臂抓取的能力。
    提供基于 MuJoCo 接触的抓握判定和 grasp keypoints 获取。
    """

    def is_grasped(self, physics, robot) -> bool:
        """
        基于接触判定：夹爪 geoms 与 entity geoms 有接触即为 grasped。
        """
        gripper_geom_ids = {physics.bind(g).element_id for g in robot.gripper_geoms}
        entity_geom_ids = {physics.bind(g).element_id for g in self.geoms}
        for c in physics.data.contact:
            if (c.geom1 in gripper_geom_ids and c.geom2 in entity_geom_ids) or \
               (c.geom2 in gripper_geom_ids and c.geom1 in entity_geom_ids):
                return True
        return False

    def get_grasped_keypoints(self, physics) -> list:
        """
        返回 grasp sites 的位置列表；若无 grasp site 则返回 entity 中心。
        """
        grasp_keypoints = []
        if len(self.grasp_sites(physics)) > 0:
            grasp_keypoints.extend([physics.bind(site).xpos for site in self.grasp_sites(physics)])
        else:
            grasp_keypoints.append(self.get_xpos(physics))
        return grasp_keypoints


# =============================================================================
# ContainerMixin - 3D 空间容纳
# =============================================================================

class ContainerMixin:
    """
    3D bbox 容器能力（瓶子、烧杯、盒子）。
    提供 place point 和 contain 判定。
    """

    def get_place_points(self, physics):
        """
        获取放置点列表（site group=2）。
        """
        placement_sites = self.place_sites(physics)
        return [np.array(physics.bind(site).xpos) for site in placement_sites]

    def contain(self, point, physics) -> bool:
        """
        判定目标点是否在容器内部（基于 key_sites 的 bbox）。
        """
        keysites = self.key_sites(physics)
        self.keypoints = np.array([physics.bind(kp).xpos for kp in keysites])
        minX, maxX = self.keypoints[:, 0].min(), self.keypoints[:, 0].max()
        minY, maxY = self.keypoints[:, 1].min(), self.keypoints[:, 1].max()
        minZ, maxZ = self.keypoints[:, 2].min(), self.keypoints[:, 2].max()
        return (minX <= point[0] <= maxX and
                minY <= point[1] <= maxY and
                minZ <= point[2] <= maxZ)


# =============================================================================
# SurfaceMixin - 平面承载
# =============================================================================

class SurfaceMixin:
    """
    平面承载能力（桌面、垫子）。
    提供矩形表面的 contain 判定和放置点。
    """

    def __init__(self, z_threshold: float = 0.1, **kwargs):
        self.z_threshold = z_threshold
        super().__init__(**kwargs)

    def contain(self, point, physics) -> bool:
        """
        判定目标点是否在平面上（基于 key_sites 的 AABB + 高度阈值）。
        """
        self.keypoints = np.array([physics.bind(kp).xpos for kp in self.key_sites(physics)])
        minX, maxX = self.keypoints[:, 0].min(), self.keypoints[:, 0].max()
        minY, maxY = self.keypoints[:, 1].min(), self.keypoints[:, 1].max()
        platform_z = self.keypoints[:, -1].min()
        return (minX <= point[0] <= maxX and
                minY <= point[1] <= maxY and
                platform_z < point[2] < platform_z + self.z_threshold)

    def get_place_points(self, physics):
        """
        获取放置点（优先使用 site，无则使用 entity 中心上方）。
        """
        placement_sites = self.place_sites(physics)
        place_points = [np.array(physics.bind(site).xpos) for site in placement_sites]
        if len(place_points) == 0:
            place_points.append(self.get_xpos(physics) + np.array([0, 0, self.z_threshold]))
        return place_points


# =============================================================================
# LiquidDisplayMixin - 液体显示/存储
# =============================================================================

class LiquidDisplayMixin:
    """
    液体显示/存储能力。
    提供溶液颜色渲染、清空、填充等功能。
    """

    _solution_geom_name = "solution"

    def __init__(self, solution=None, solution_rgba=None, solutes=None, **kwargs):
        self.solution = solution
        self.solution_rgba = solution_rgba
        self._current_solution_rgba = None
        if solutes is not None:
            from scihorizon_elab.simulation.entities.specific_entities.solute_reaction import resolve_substance_name
            self.solutes = [resolve_substance_name(s) for s in solutes]
        elif solution is not None:
            from scihorizon_elab.simulation.entities.specific_entities.solute_reaction import resolve_substance_name
            self.solutes = [resolve_substance_name(solution)]
        else:
            self.solutes = []
        super().__init__(**kwargs)

    @property
    def solute2rgba(self):
        from scihorizon_elab.simulation.entities.specific_entities.solute_reaction import SOLUTE2RGBA
        return SOLUTE2RGBA

    def set_solution_rgba(self, physics, solution_name=None, target_rgba=None):
        """
        设置溶液颜色。
        优先级: target_rgba > solution_name > solutes > solution_rgba
        """
        geom = self.mjcf_model.worldbody.find("geom", self._solution_geom_name)
        if geom is None:
            return
        if target_rgba is not None:
            physics.bind(geom).rgba = target_rgba
        elif solution_name is not None:
            if solution_name not in self.solutes:
                self.solutes.append(solution_name)
            rgba = self.solute2rgba.get(solution_name, [1, 1, 1, 0.3])
            physics.bind(geom).rgba = rgba
        else:
            from scihorizon_elab.simulation.entities.specific_entities.solute_reaction import resolve_color_from_solutes
            rgba = resolve_color_from_solutes(self.solutes, self.solution_rgba)
            physics.bind(geom).rgba = rgba
        self._current_solution_rgba = list(physics.bind(geom).rgba)

    def get_solution_geom_id(self, physics) -> int | None:
        """
        获取 solution geom 的 element_id，用于接触判定。
        如果容器没有 solution geom（空的或非液体容器）返回 None。
        """
        geom = self.mjcf_model.worldbody.find("geom", self._solution_geom_name)
        if geom is None:
            return None
        return physics.bind(geom).element_id

    def get_solution_rgba(self, physics) -> np.ndarray | None:
        """
        获取当前溶液颜色。
        """
        geom = self.mjcf_model.worldbody.find("geom", self._solution_geom_name)
        if geom is None:
            return None
        return physics.bind(geom).rgba

    def fill_solution(self, physics, source_solutes=None, source_solution_rgba=None):
        """
        向容器中灌入溶液。
        """
        geom = self.mjcf_model.worldbody.find("geom", self._solution_geom_name)
        if geom is None:
            return
        if source_solutes is not None:
            self.solutes = list(source_solutes)
            from scihorizon_elab.simulation.entities.specific_entities.solute_reaction import resolve_color_from_solutes
            rgba = resolve_color_from_solutes(self.solutes, source_solution_rgba)
        elif source_solution_rgba is not None:
            rgba = list(source_solution_rgba)
        else:
            rgba = [1, 1, 1, 0.3]
        physics.bind(geom).rgba = rgba
        self._current_solution_rgba = list(rgba)
        self.solution_rgba = list(rgba)

    def clear_solution(self, physics):
        """
        清空容器中的溶液。
        """
        geom = self.mjcf_model.worldbody.find("geom", self._solution_geom_name)
        if geom is None:
            return
        physics.bind(geom).rgba = [1, 1, 1, 0]
        self._current_solution_rgba = [1, 1, 1, 0]
        self.solutes = []
        self.solution = None
        self.solution_rgba = None

    def initialize_episode(self, physics, random_state):
        self.set_solution_rgba(physics)
        return super().initialize_episode(physics, random_state)

    def save(self, physics):
        data = super().save(physics)
        data["solution"] = self.solution
        data["solutes"] = list(self.solutes)
        data["solution_rgba"] = list(self.solution_rgba) if self.solution_rgba is not None else None
        return data


# =============================================================================
# LiquidTransferMixin - 液体移取
# =============================================================================

class LiquidTransferMixin:
    """
    液体移取能力（移液管、滴管）。
    提供溶液存储、吸取位置等功能。
    """

    def __init__(self, solution=None, solution_rgba=None, **kwargs):
        self._solution = solution
        self._solution_rgba = solution_rgba
        super().__init__(**kwargs)

    @property
    def solution(self) -> str | None:
        return self._solution

    @property
    def solution_rgba(self) -> list | None:
        return self._solution_rgba

    def store_solution(self, solution: str, solution_rgba: list | None = None):
        """存储吸取的溶液。"""
        self._solution = solution
        self._solution_rgba = solution_rgba

    def clear_solution(self):
        """清空已存储的溶液。"""
        self._solution = None
        self._solution_rgba = None

    def has_solution(self) -> bool:
        """是否已吸取了溶液。"""
        return self._solution is not None

    def get_aspirate_site(self):
        """获取吸取用的 site（针尖位置）。

        优先级：
          1. 名为 aspirate_site 的 site（XML 显式定义）
          2. bottom_site（针尖位置，mechanical_pipette 等已有）
          3. None（回退到 EE 位姿）
        """
        worldbody = self.mjcf_model.worldbody
        site = worldbody.find("site", "aspirate_site")
        if site is not None:
            return site
        site = worldbody.find("site", "bottom_site")
        if site is not None:
            return site
        return None

    def get_aspirate_pos(self, physics) -> np.ndarray | None:
        """获取吸取位置的 world 坐标。"""
        site = self.get_aspirate_site()
        if site is None:
            return None
        return physics.bind(site).xpos


# =============================================================================
# HingeMixin - 铰链开关
# =============================================================================

class HingeMixin:
    """
    铰链开关能力（门、屏、瓶盖）。
    提供 open/close 状态判定和轨迹生成。
    """

    _hinge_joint_name = "door"

    def __init__(self,
                 open_threshold: float = np.pi / 3,
                 close_threshold: float = np.pi / 10,
                 **kwargs):
        self.open_threshold = open_threshold
        self.close_threshold = close_threshold
        super().__init__(**kwargs)

    @property
    def hinge_joint(self):
        """查找 hinge joint。"""
        for joint in self.joints:
            if self._hinge_joint_name in joint.name:
                return joint
        return None

    def is_open(self, physics) -> bool:
        """是否已打开。"""
        joint_pos = physics.bind(self.hinge_joint).qpos
        return abs(joint_pos) > self.open_threshold

    def is_closed(self, physics) -> bool:
        """是否已关闭。"""
        joint_pos = physics.bind(self.hinge_joint).qpos
        return abs(joint_pos) < self.close_threshold

    def get_handle_pos(self, physics) -> np.ndarray:
        """获取把手位置。"""
        grasp_sites = self.grasp_sites(physics)
        if len(grasp_sites) > 0:
            return physics.bind(np.random.choice(grasp_sites)).xpos
        else:
            raise ValueError("No handle site found")

    def get_open_trajectory(self, physics) -> list:
        """获取开门轨迹。"""
        from scihorizon_elab.utils.utils import rotate_point_around_axis
        trajectory = []
        init_pos = self.get_handle_pos(physics)
        rotation_axis = physics.bind(self.hinge_joint).xaxis
        rotation_anchor = physics.bind(self.hinge_joint).xanchor
        current_qpos = physics.bind(self.hinge_joint).qpos
        target_qpos = physics.bind(self.hinge_joint).range[-1]
        delta_angles = np.arange(0.1, target_qpos - current_qpos[0], 0.1)
        for delta_angle in delta_angles:
            new_pos = rotate_point_around_axis(init_pos, rotation_anchor, rotation_axis, delta_angle)
            trajectory.append(new_pos)
        return trajectory

    def get_close_trajectory(self, physics) -> list:
        """获取关门轨迹。"""
        from scihorizon_elab.utils.utils import rotate_point_around_axis
        trajectory = []
        init_pos = self.get_handle_pos(physics)
        rotation_axis = physics.bind(self.hinge_joint).xaxis
        rotation_anchor = physics.bind(self.hinge_joint).xanchor
        current_qpos = physics.bind(self.hinge_joint).qpos
        target_qpos = physics.bind(self.hinge_joint).range[0]
        delta_angles = np.arange(-0.1, target_qpos - current_qpos[0], -0.1)
        for delta_angle in delta_angles:
            new_pos = rotate_point_around_axis(init_pos, rotation_anchor, rotation_axis, delta_angle)
            trajectory.append(new_pos)
        return trajectory


# =============================================================================
# SlideMixin - 滑轨移动
# =============================================================================

class SlideMixin:
    """
    滑轨移动能力（抽屉）。
    提供 open level 和轨迹生成。
    """

    def __init__(self, **kwargs):
        self.slide_rails = []
        self.n_rail = 0
        super().__init__(**kwargs)

    def _build(self, *args, **kwargs):
        """在 _build 阶段初始化滑轨列表。"""
        result = super()._build(*args, **kwargs)
        for body in self.bodies:
            if "drawer" in body.name:
                self.slide_rails.append(body)
        self.n_rail = len(self.slide_rails)
        return result

    def get_slide_open_level(self, physics) -> list:
        """获取各滑轨的打开程度 [0, 1]。"""
        if not self.slide_rails:
            for body in self.bodies:
                if "drawer" in body.name:
                    self.slide_rails.append(body)
            self.n_rail = len(self.slide_rails)
        open_levels = []
        for joint in self.joints:
            qpos = physics.bind(joint).qpos
            range = physics.bind(joint).range
            open_level = (qpos - range[0]) / (range[1] - range[0])
            open_levels.append(open_level)
        return open_levels

    def get_slide_handle_pos(self, physics, rail_id: int) -> np.ndarray:
        """获取滑轨把手位置。"""
        if not self.slide_rails:
            for body in self.bodies:
                if "drawer" in body.name:
                    self.slide_rails.append(body)
            self.n_rail = len(self.slide_rails)
        rail = self.slide_rails[rail_id]
        sites = rail.find_all("site")
        for site in sites:
            if physics.bind(site).group == 4:
                return physics.bind(site).xpos
        raise ValueError("No handle site found")

    def get_slide_trajectory(self, physics, rail_id: int) -> list:
        """获取滑轨滑动轨迹。"""
        from scihorizon_elab.utils.utils import slide_point_along_axis
        handle_init_pos = self.get_slide_handle_pos(physics, rail_id)
        init_joint_qpos = float(physics.bind(self.joints[rail_id]).qpos)
        range = physics.bind(self.joints[rail_id]).range
        axis = physics.bind(self.joints[rail_id]).xaxis
        max_distance = float(range[1]) if abs(float(range[1])) > abs(float(range[0])) else float(range[0])
        trajectory = []
        step = -0.05 if max_distance < init_joint_qpos else 0.05
        for distance in np.arange(0.05, max_distance - init_joint_qpos, step):
            new_pos = slide_point_along_axis(handle_init_pos, axis, distance)
            trajectory.append(new_pos)
        return trajectory


# =============================================================================
# ButtonMixin - 按钮交互
# =============================================================================

class ButtonMixin:
    """
    按钮交互能力（电磁炉、烘干箱）。
    提供按钮位置检测、按压状态跟踪和视觉反馈。
    """

    _button_material_name = None

    BUTTON_COLOR_IDLE = np.array([0.6, 0.05, 0.05, 1.0])
    BUTTON_COLOR_ACTIVE = np.array([0.1, 0.6, 0.1, 1.0])

    @property
    def start_button(self):
        """返回 start_button geom。"""
        return self.mjcf_model.worldbody.find("geom", "start_button")

    def get_start_button_pos(self, physics) -> np.ndarray:
        """获取按钮表面的世界坐标。"""
        btn = self.start_button
        if btn is None:
            return np.zeros(3)
        try:
            body_xpos = np.array(physics.bind(btn).xpos)
            body_xmat = physics.bind(btn).xmat.reshape(3, 3)
            size = np.array(btn.size)
            half_height = size[1] if len(size) > 1 else size[0] * 0.5
            surface_offset_local = np.array([0, 0, half_height])
            surface_offset_world = body_xmat @ surface_offset_local
            return body_xpos + surface_offset_world
        except Exception:
            return np.zeros(3)

    def _resolve_button_material(self):
        """解析按钮材质。"""
        if self._button_material_name is not None:
            mat = self.mjcf_model.asset.find("material", self._button_material_name)
            if mat is not None:
                return mat
        btn = self.start_button
        if btn is not None and getattr(btn, "material", None) is not None:
            mat = btn.material
            if getattr(mat, "name", None):
                return mat
        for mat in self.mjcf_model.asset.find_all("material"):
            name = (getattr(mat, "name", "") or "").lower()
            if "button" in name:
                return mat
            try:
                r, g, b = float(mat.rgba[0]), float(mat.rgba[1]), float(mat.rgba[2])
            except (TypeError, ValueError, IndexError):
                continue
            if r > 0.4 and g < 0.2 and b < 0.2:
                return mat
        return None

    def is_activate(self, physics) -> bool:
        """检测按钮是否被按下。"""
        btn = self.start_button
        if btn is None:
            return False
        try:
            body_name = self.mjcf_model.model
            btn_id = physics.model.name2id(f"{body_name}/start_button", "geom")
        except Exception:
            return False
        contacts = physics.data.contact
        contact_geoms = [c.geom1 for c in contacts] + [c.geom2 for c in contacts]
        currently_pressed = btn_id in contact_geoms

        prev_pressed = getattr(self, "_is_pressed", False)
        if currently_pressed != prev_pressed:
            self._set_button_color(physics, active=currently_pressed)

        self._is_pressed = currently_pressed
        return currently_pressed

    def _set_button_color(self, physics, active: bool):
        """设置按钮颜色。"""
        mat = self._resolve_button_material()
        if mat is None:
            return
        try:
            target = self.BUTTON_COLOR_ACTIVE if active else self.BUTTON_COLOR_IDLE
            body_name = self.mjcf_model.model
            import mujoco
            raw_m = physics.model._model
            target_full_name = f"{body_name}/{mat.name}"
            mat_id = None
            for i in range(raw_m.nmat):
                addr = raw_m.name_matadr[i]
                name_bytes = raw_m.names[addr:].split(b'\x00')[0]
                name = name_bytes.decode('utf-8', errors='replace')
                if name == target_full_name or name == mat.name:
                    mat_id = i
                    break
            if mat_id is not None:
                raw_m.mat_rgba[mat_id] = target
        except Exception:
            pass

    def is_pressed(self) -> bool:
        """返回当前按压状态。"""
        return getattr(self, "_is_pressed", False)


# =============================================================================
# FlameDisplayMixin - 火焰控制
# =============================================================================

class FlameDisplayMixin:
    """
    火焰控制能力（酒精灯）。
    提供火焰点燃/熄灭状态控制。
    """

    def __init__(self, **kwargs):
        self._is_lit = False
        super().__init__(**kwargs)

    def set_flame_state(self, physics, lit: bool):
        """设置火焰状态。"""
        self._is_lit = lit
        flame_sites = self.mjcf_model.worldbody.find_all("site")
        for site in flame_sites:
            if "flame" in site.name:
                physics.bind(site).rgba[3] = 1.0 if lit else 0.0

    def is_lit(self) -> bool:
        """火焰是否点燃。"""
        return self._is_lit
