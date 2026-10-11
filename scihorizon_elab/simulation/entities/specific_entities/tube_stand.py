"""
TubeStand - 试管架。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin
from scihorizon_elab.utils.register import register


@register.add_entity("TubeStand")
class TubeStand(ContainerMixin, Entity):
    """
    试管架，用于放置 ChemistryTube。
    继承 ContainerMixin 以提供 get_place_points()，对应 XML 中 group=2 的 placepoint site。
    """
    pass
