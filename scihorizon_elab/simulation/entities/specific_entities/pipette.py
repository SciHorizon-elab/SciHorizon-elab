"""
Pipette and Dropper - 液体移取工具。
"""
from scihorizon_elab.simulation.entities.specific_entities.common_grasped_entity import CommonGraspedEntity
from scihorizon_elab.simulation.entities.mixins import LiquidTransferMixin
from scihorizon_elab.simulation.entities.entity import ParentBinding
from scihorizon_elab.utils.register import register


@register.add_entity("Pipette")
class Pipette(CommonGraspedEntity, LiquidTransferMixin):
    """
    移液管。
    - CommonGraspedEntity: 可被机械臂抓取
    - LiquidTransferMixin: 可吸取/释放液体

    默认挂在 tube_stand 试管架的孔位上（多个 pipette 随机选孔）。
    """

    def __init__(self, bulb_type: str = "pipette", **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def get_parent_container(cls):
        return ParentBinding(
            parent_spec="chemistry_tube_stand",
            parent_class="TubeStand",
            placement="hole_grid",
            params={"preallocate_holes": False, "local_z": 0.05},
        )


@register.add_entity("MechanicalPipette")
class MechanicalPipette(Pipette):
    """
    机械移液器（如 Eppendorf / Gilson 等）。

    解绑 pipettes_stand 和 chemistry_tube_stand，作为独立资产直接放到桌面上，
    与 beaker 等普通小件走相同的 plain 加载路径。

    注意：因为继承 Pipette（默认父容器 = chemistry_tube_stand），必须显式
    覆写 get_parent_container() 返回 None 才会走基类的"无父容器"路径。
    """

    @classmethod
    def get_parent_container(cls):
        return None  # 显式声明无父容器


@register.add_entity("Dropper")
class Dropper(Pipette):
    """
    滴管。
    - 继承 Pipette，bulb_type 固定为 "dropper"
    """

    def __init__(self, **kwargs):
        super().__init__(bulb_type="dropper", **kwargs)
