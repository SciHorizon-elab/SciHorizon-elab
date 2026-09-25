"""
ContainerWithDoor - 带门的容器。
"""
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin, HingeMixin
from scihorizon_elab.utils.register import register


@register.add_entity("ContainerWithDoor")
class ContainerWithDoor(ContainerMixin, HingeMixin, Entity):
    """
    带门容器（冰箱、保险柜等）。
    - ContainerMixin: 可容纳物品
    - HingeMixin: 门可开合
    """

    def is_grasped(self, physics, robot) -> bool:
        """
        特殊抓握判定：仅当夹爪与门把手 body 的 geom 接触时才视为 grasped。
        这样既反映真实物理状态，又不会把夹爪碰触箱体误判为抓握。
        """
        handle_geom_ids = set()
        for site in self.grasp_sites(physics):
            site_body = site.parent
            if site_body is None:
                continue
            for geom in site_body.find_all('geom'):
                handle_geom_ids.add(physics.bind(geom).element_id)
        if not handle_geom_ids:
            handle_geom_ids = {physics.bind(g).element_id for g in self.geoms}

        gripper_geom_ids = {physics.bind(g).element_id for g in robot.gripper_geoms}
        for c in physics.data.contact:
            if (c.geom1 in gripper_geom_ids and c.geom2 in handle_geom_ids) or \
               (c.geom2 in gripper_geom_ids and c.geom1 in handle_geom_ids):
                return True
        return False

    def get_grasped_keypoints(self, physics) -> list:
        """返回门把手处的 grasp keypoints。"""
        grasp_sites = self.grasp_sites(physics)
        return [physics.bind(site).xpos for site in grasp_sites]
