"""
WaterBathContainer - 水浴槽（带可显示液面的水槽）。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin, LiquidDisplayMixin
from scihorizon_elab.utils.register import register


@register.add_entity("WaterBathContainer")
class WaterBathContainer(ContainerMixin, LiquidDisplayMixin, Entity):
    """
    水浴槽。
    - ContainerMixin: 可放置物品（被加热的小烧杯等）
    - LiquidDisplayMixin: 可被 wait_for(add_solution=...) 染色
      （用于"人工加水"的人机协同场景）

    注意：与 ChemistryContainer 的区别是本类不混入 GraspMixin，
    水浴槽是固定在桌面上的设备，不会被机械臂抓起。
    """
    pass