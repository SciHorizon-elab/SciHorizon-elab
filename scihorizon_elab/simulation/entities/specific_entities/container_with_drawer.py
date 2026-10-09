"""
ContainerWithDrawer - 带抽屉的容器。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin, SlideMixin, GraspMixin
from scihorizon_elab.utils.register import register


@register.add_entity("ContainerWithDrawer")
class ContainerWithDrawer(ContainerMixin, SlideMixin, GraspMixin, Entity):
    """
    带抽屉容器。
    - ContainerMixin: 可容纳物品
    - SlideMixin: 抽屉可滑动
    - GraspMixin: 可被机械臂抓取
    """
    pass
