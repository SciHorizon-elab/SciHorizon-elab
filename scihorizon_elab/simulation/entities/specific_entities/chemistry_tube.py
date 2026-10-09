"""
ChemistryTube - 化学试管。
"""
from scihorizon_elab.simulation.entities.specific_entities.common_grasped_entity import CommonGraspedEntity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin, LiquidDisplayMixin
from scihorizon_elab.simulation.entities.entity import ParentBinding
from scihorizon_elab.utils.register import register


@register.add_entity("ChemistryTube")
class ChemistryTube(ContainerMixin, LiquidDisplayMixin, CommonGraspedEntity):
    """
    化学试管。
    - ContainerMixin: 提供 get_place_points / contain（pipette dispense 到
      试管需要 placepoint site，XML 中需定义 group=2 的 placepoint）
    - LiquidDisplayMixin: 可显示液体（必须在 CommonGraspedEntity 之前，
      保证 LiquidDisplayMixin.__init__ 在 Entity.__init__ 之前执行，
      否则 solution/solutes/solution_rgba 不会被处理）
    - CommonGraspedEntity: 可被机械臂抓取
    """

    @classmethod
    def get_parent_container(cls):
        """试管挂在试管架的孔位网格上，多个 tube 需预分配不重复的孔位。"""
        return ParentBinding(
            parent_spec="chemistry_tube_stand",
            parent_class="TubeStand",
            placement="hole_grid",
            params={"preallocate_holes": True, "local_z": 0.05},
        )
