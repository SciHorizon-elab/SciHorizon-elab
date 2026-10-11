"""
Table - 桌面/平面承载。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import SurfaceMixin
from scihorizon_elab.utils.register import register


@register.add_entity("Table")
class Table(SurfaceMixin, Entity):
    """
    桌面。
    - SurfaceMixin: 平面承载，可放置物品
    """
    pass
