"""
HeatDevice - 加热设备（热盘）。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import SurfaceMixin, ButtonMixin
from scihorizon_elab.utils.register import register


@register.add_entity("HeatDevice")
class HeatDevice(SurfaceMixin, ButtonMixin, Entity):
    """
    热盘/加热设备。
    - SurfaceMixin: 表面可放置物品
    - ButtonMixin: 有可交互按钮
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._heating_active = False

    def is_activate(self, physics):
        """
        检测按钮按压并切换加热状态。
        """
        pressed = super().is_activate(physics)
        if pressed and not self._heating_active:
            self._heating_active = True
        elif not pressed and self._heating_active:
            self._heating_active = False
        return pressed
