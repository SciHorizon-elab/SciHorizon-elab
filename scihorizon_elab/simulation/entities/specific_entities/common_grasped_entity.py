"""
CommonGraspedEntity - 所有可抓取物品的基类。
继承 GraspMixin，提供标准的抓握判定和 keypoints 获取。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import GraspMixin
from scihorizon_elab.utils.register import register


@register.add_entity("CommonGraspedEntity")
class CommonGraspedEntity(GraspMixin, Entity):
    """
    可抓取物品的具体类。
    提供统一的 is_grasped 和 get_grasped_keypoints 实现。
    """
    pass
