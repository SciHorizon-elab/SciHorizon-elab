"""
Container - 通用 3D 容器。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin
from scihorizon_elab.utils.register import register


@register.add_entity("Container")
class Container(ContainerMixin, Entity):
    """
    通用 3D 容器。
    - ContainerMixin: 可容纳物品，提供 place point 和 contain 判定
    """
    pass
