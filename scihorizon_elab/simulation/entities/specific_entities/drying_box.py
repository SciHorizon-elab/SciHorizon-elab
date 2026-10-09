"""
DryingBox - 烘干箱。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin, HingeMixin, ButtonMixin
from scihorizon_elab.utils.register import register


@register.add_entity("DryingBox")
class DryingBox(ContainerMixin, HingeMixin, ButtonMixin, Entity):
    """
    烘干箱。
    - ContainerMixin: 可容纳物品
    - HingeMixin: 门可开合
    - ButtonMixin: 有可交互按钮

    烘干箱。
    - ContainerMixin: 可容纳物品
    - HingeMixin: 门可开合
    - ButtonMixin: 有可交互按钮
    """

    _button_material_name = "button_vcol_mat"
