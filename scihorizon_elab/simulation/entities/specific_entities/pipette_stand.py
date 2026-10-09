"""
PipetteStand - 移液管架。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.utils.register import register


@register.add_entity("PipetteStand")
class PipetteStand(Entity):
    """
    移液管架，用于放置 Pipette 等移取工具。
    不需要额外的 mixin，只是一个简单的静态容器。
    """
    pass
