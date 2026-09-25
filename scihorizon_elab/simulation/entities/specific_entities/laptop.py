"""
Laptop - 翻盖设备。
"""
import numpy as np
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import GraspMixin, HingeMixin
from scihorizon_elab.utils.register import register


@register.add_entity("Laptop")
class Laptop(GraspMixin, HingeMixin, Entity):
    """
    翻盖笔记本。
    - GraspMixin: 可被机械臂抓取
    - HingeMixin: 屏幕可开合
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
