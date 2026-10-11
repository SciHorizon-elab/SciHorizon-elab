"""
AlcoholLamp - 酒精灯。
"""
from scihorizon_elab.simulation.entities.specific_entities.common_grasped_entity import CommonGraspedEntity
from scihorizon_elab.simulation.entities.mixins import FlameDisplayMixin
from scihorizon_elab.utils.register import register


@register.add_entity("AlcoholLamp")
class AlcoholLamp(CommonGraspedEntity, FlameDisplayMixin):
    """
    酒精灯。
    - CommonGraspedEntity: 可被机械臂抓取
    - FlameDisplayMixin: 可控制火焰显示/熄灭

    默认状态（XML）：火焰 geom alpha=0，火焰不可见。
    调用 set_flame_state(lit=True) 时，火焰变为可见。
    """

    LIT_RGBA_OUTER = [1.0, 0.45, 0.05, 0.48]
    LIT_RGBA_INNER = [1.0, 0.95, 0.8, 0.85]

    def set_flame_state(self, physics, lit: bool):
        """控制火焰可见性。"""
        self._is_lit = lit

        flame_configs = [
            ("flame_outer", self.LIT_RGBA_OUTER),
            ("flame_inner", self.LIT_RGBA_INNER),
        ]

        for geom_name, lit_rgba in flame_configs:
            geom = self.mjcf_model.worldbody.find("geom", geom_name)
            if geom is None:
                continue

            if lit:
                physics.bind(geom).rgba = list(lit_rgba)
            else:
                rgba = list(lit_rgba)
                rgba[3] = 0.0
                physics.bind(geom).rgba = rgba

    def initialize_episode(self, physics, random_state):
        """确保 episode 开始时火焰熄灭。"""
        self.set_flame_state(physics, lit=False)
        return super().initialize_episode(physics, random_state)
