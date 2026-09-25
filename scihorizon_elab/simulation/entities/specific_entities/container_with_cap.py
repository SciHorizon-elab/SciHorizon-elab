"""
ContainerWithCap - 带盖子的容器（瓶盖）。
"""
import numpy as np
import logging
from scihorizon_elab.simulation.entities.entity import Entity
from scihorizon_elab.simulation.entities.mixins import ContainerMixin, HingeMixin, SlideMixin, GraspMixin
from scihorizon_elab.utils.register import register

logger = logging.getLogger(__name__)


@register.add_entity("ContainerWithCap")
class ContainerWithCap(ContainerMixin, HingeMixin, SlideMixin, GraspMixin, Entity):
    """
    带盖子容器（瓶子等）。
    - ContainerMixin: 可容纳物品
    - HingeMixin: 盖子可旋转打开
    - SlideMixin: 盖子可滑升
    - GraspMixin: 可被机械臂抓取

    盖子通过 hinge joint 旋转解锁，然后 slide joint 让盖子升起。
    """

    def __init__(self,
                 open_threshold: float = 3 * np.pi / 2,
                 close_threshold: float = np.pi / 6,
                 unlock_rotation: float = 0.5 * np.pi,
                 unlock_slide_range: float = 0.02,
                 **kwargs):
        self.open_threshold = open_threshold
        self.close_threshold = close_threshold
        self.unlock_rotation = unlock_rotation
        self.unlock_slide_range = unlock_slide_range
        self._slide_unlocked = False
        self._initial_door_qpos = 0.0
        super().__init__(**kwargs)

    @property
    def cap_joint(self):
        """查找盖子的 hinge joint。"""
        for joint in self.joints:
            if "door" in joint.name:
                return joint
        return None

    @property
    def slide_joint(self):
        """查找盖子的 slide joint。"""
        for joint in self.joints:
            if "slide" in joint.name:
                return joint
        return None

    def get_cap_body(self):
        """获取盖子 body。"""
        if self.cap_joint is None:
            return None
        return self.cap_joint.parent

    def is_cap_open(self, physics, initial_joint_qpos=None, initial_slide_qpos=None) -> bool:
        """判断盖子是否打开。"""
        if self.cap_joint is None:
            return False
        initial_j = initial_joint_qpos if initial_joint_qpos is not None else 0.0
        if abs(physics.bind(self.cap_joint).qpos - initial_j) > self.unlock_rotation:
            return True
        if self.slide_joint is not None and initial_slide_qpos is not None:
            if abs(physics.bind(self.slide_joint).qpos - initial_slide_qpos) > 0.01:
                return True
        return False

    def is_cap_closed(self, physics, initial_joint_qpos=None) -> bool:
        """判断盖子是否关闭。"""
        if self.cap_joint is None:
            return True
        initial_j = initial_joint_qpos if initial_joint_qpos is not None else 0.0
        return abs(physics.bind(self.cap_joint).qpos - initial_j) < self.close_threshold

    def is_slide_unlocked(self) -> bool:
        """slide joint 是否已解锁。"""
        return getattr(self, '_slide_unlocked', False)

    def record_initial_door_qpos(self, physics):
        """记录初始 door qpos。在 initialize_episode 时调用。"""
        if self.cap_joint is None:
            return
        qpos = physics.bind(self.cap_joint).qpos
        self._initial_door_qpos = float(qpos.item() if hasattr(qpos, 'item') else qpos)
        self._slide_unlocked = False

    def check_and_unlock_slide(self, physics):
        """
        当盖子旋转超过 unlock_rotation 时，解锁 slide joint。
        应该在 task 的 after_step 中调用。
        """
        if getattr(self, '_slide_unlocked', False):
            return
        if self.cap_joint is None or self.slide_joint is None:
            return
        qpos = physics.bind(self.cap_joint).qpos
        current_door = float(qpos.item() if hasattr(qpos, 'item') else qpos)
        rotation_delta = abs(current_door - self._initial_door_qpos)
        logger.debug(f"[check_and_unlock_slide] door qpos: {current_door:.4f}, "
                     f"initial: {self._initial_door_qpos:.4f}, "
                     f"delta: {rotation_delta:.4f} / {self.unlock_rotation:.4f}")
        if rotation_delta >= self.unlock_rotation:
            slide_id = physics.bind(self.slide_joint).element_id
            slide_dof = int(physics.model.jnt_dofadr[slide_id])
            physics.model.jnt_range[slide_id] = np.array([0.0, float(self.unlock_slide_range)])
            physics.model.dof_damping[slide_dof] = 2.0
            self._slide_unlocked = True
            logger.debug(f"[check_and_unlock_slide] ★ SLIDE UNLOCKED! "
                         f"range -> [0, {self.unlock_slide_range}], damping -> 2.0")

    def is_cap_separated(self, physics, penetration_threshold: float = 0.0) -> bool:
        """判断盖子是否与瓶身分离。"""
        cap_body = self.get_cap_body()
        if cap_body is None:
            return False
        cap_geom_ids = {physics.bind(g).element_id for g in cap_body.find_all('geom')}
        all_geom_ids = {physics.bind(g).element_id for g in self.geoms}
        body_geom_ids = all_geom_ids - cap_geom_ids
        if not cap_geom_ids or not body_geom_ids:
            return False
        for c in physics.data.contact:
            if c.dist >= -penetration_threshold:
                continue
            pair = {c.geom1, c.geom2}
            if pair & cap_geom_ids and pair & body_geom_ids:
                return False
        return True

    def get_cap_slide_pos(self, physics) -> float:
        """获取 slide joint 位置。"""
        if self.slide_joint is None:
            return 0.0
        return physics.bind(self.slide_joint).qpos

    def get_grasped_keypoints(self, physics) -> list:
        """
        只返回盖子 body 上的 grasp sites（不返回瓶身）。
        这样 pick() 会抓盖子而不是瓶身。
        """
        cap_body = self.get_cap_body()
        if cap_body is None:
            return super().get_grasped_keypoints(physics)
        cap_geoms = cap_body.find_all('geom')
        cap_geom_ids = {physics.bind(g).element_id for g in cap_geoms}

        keypoints = []
        for site in self.grasp_sites(physics):
            site_pos = physics.bind(site).xpos
            site_body = site.parent
            site_body_geom_ids = {physics.bind(g).element_id for g in site_body.find_all('geom')}
            if site_body_geom_ids & cap_geom_ids:
                keypoints.append(site_pos)
        return keypoints

    def is_grasped(self, physics, robot) -> bool:
        """
        接触式抓握判定：检查夹爪与 entity 任一 geom 的接触。
        """
        entity_geom_ids = {physics.bind(g).element_id for g in self.geoms}
        gripper_geom_ids = {physics.bind(g).element_id for g in robot.gripper_geoms}
        for c in physics.data.contact:
            if (c.geom1 in gripper_geom_ids and c.geom2 in entity_geom_ids) or \
               (c.geom2 in gripper_geom_ids and c.geom1 in entity_geom_ids):
                return True
        return False
