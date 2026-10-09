"""
FlatContainer - 平面承载容器（用于 hot_plate、electronic_scale 等平面类设备）。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import SurfaceMixin
from scihorizon_elab.utils.register import register


@register.add_entity("FlatContainer")
class FlatContainer(SurfaceMixin, Entity):
    """
    平面承载容器。
    - SurfaceMixin: 平面承载，可放置物品
    """
    pass
