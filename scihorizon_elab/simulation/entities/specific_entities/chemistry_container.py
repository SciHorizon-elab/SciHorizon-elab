"""
ChemistryContainer - 化学容器（烧杯）。
"""
import numpy as np
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin, LiquidDisplayMixin, GraspMixin
from scihorizon_elab.utils.register import register


@register.add_entity("ChemistryContainer")
class ChemistryContainer(ContainerMixin, LiquidDisplayMixin, GraspMixin, Entity):
    """
    化学烧杯。
    - ContainerMixin: 可放置物品
    - LiquidDisplayMixin: 可显示液体
    - GraspMixin: 可被机械臂抓取

    化学烧杯。
    - ContainerMixin: 可收集物品
    - LiquidDisplayMixin: 可显示液体
    - GraspMixin: 可被机械臂抓取
    """

    def get_place_point(self, physics):
        """
        获取放置点（site group=2）。模型未设置 place point 时直接报错。
        """
        place_sites = self.place_sites(physics)
        if not place_sites:
            # mjcf.RootElement 没有 .name 属性，用 getattr 安全获取
            ent_name = getattr(self, "name", None) or getattr(self._mjcf_model, "model", "<unknown>")
            raise ValueError(
                f"Entity '{ent_name}' has no place point (group=2 site). "
                "Please add a placepoint site to its XML."
            )
        return [physics.bind(site).xpos for site in place_sites]

    def contain(self, point, physics) -> bool:
        """
        判定目标点是否在烧杯内部。
        """
        try:
            keysites = self.key_sites(physics)
            if not keysites:
                raise AttributeError("No key_sites found")
            keypoints = np.array([physics.bind(kp).xpos for kp in keysites])
            minX, maxX = keypoints[:, 0].min(), keypoints[:, 0].max()
            minY, maxY = keypoints[:, 1].min(), keypoints[:, 1].max()
            minZ, maxZ = keypoints[:, 2].min(), keypoints[:, 2].max()
            return (minX <= point[0] <= maxX and
                    minY <= point[1] <= maxY and
                    minZ <= point[2] <= maxZ)
        except (AttributeError, TypeError, ValueError):
            center = self.get_xpos(physics)
            radius = 0.05
            in_cylinder = ((point[0] - center[0])**2 + (point[1] - center[1])**2) < radius**2
            in_height = center[2] <= point[2] <= center[2] + 0.15
            return in_cylinder and in_height
