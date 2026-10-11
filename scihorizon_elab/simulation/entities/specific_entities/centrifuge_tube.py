"""
CentrifugeTube - 离心管（迁移自 AutoBio 资产）。

与 ChemistryTube 的区别：
- 无默认父容器（AutoBio 离心管配 60 孔离心板 / 10 孔支架，暂未迁移，
  先作为独立物体放到桌面，与 MechanicalPipette 同路径）。
- XML 已含 placepoint / grasppoint / solution geom，ContainerMixin /
  LiquidDisplayMixin / GraspMixin 能力直接可用。
"""
from scihorizon_elab.simulation.entities.specific_entities.chemistry_tube import ChemistryTube
from scihorizon_elab.utils.register import register


@register.add_entity("CentrifugeTube15ml")
class CentrifugeTube15ml(ChemistryTube):
    """15ml 离心管（带盖，刚体简化：盖与管体一体）。"""

    @classmethod
    def get_parent_container(cls):
        return None  # 独立放置，不挂试管架
