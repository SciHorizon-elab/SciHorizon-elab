import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("pick_small_beaker_pour_object_use_glass_stirring_rod")
class PickSmallBeakerPourObjectUseGlassStirringRodConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(0.0495, 0.1805), random.uniform(0.0152, 0.1432), 0.8],
            solution="CuSO4_solution_1",
            solution_rgba=[0, 0.45, 1, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="large_beaker_0",
            xml_path=name2class_xml["large_beaker"][-1],
            position=[random.uniform(-0.1805, 0.0105), random.uniform(-0.0133, 0.1717), 0.8],
            solution="Fecl2_1",
            solution_rgba=[0.56, 0.93, 0.56, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="glass_stirring_rod_0",
            xml_path=name2class_xml["glass_stirring_rod"][-1],
            position=[random.uniform(-0.1690, -0.1010), random.uniform(0.1952, 0.2632), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["pick the <small_beaker_0> which contains <CuSO4 solution_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(is_grasped=dict(entities=['small_beaker_0'], robot='robot')),
            dict(pour_into=dict(
            target_entity='small_beaker_0',
            receiver_container='large_beaker_0',
            robot='robot',
            tilt_threshold=0,
            z_clearance=0.01,
        )),
            dict(stir=dict(
            entities=['glass_stirring_rod_0'],
            container='large_beaker_0',
            robot='robot',
            min_distance=0.15,
            tool_tip_site='bottom_site',
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("pick_small_beaker_pour_object_use_glass_stirring_rod")
class PickSmallBeakerPourObjectUseGlassStirringRodTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.pour_to_entity, target_container_name="large_beaker_0", tilt_angle=1.8, wait_time=10),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="glass_stirring_rod_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.stir_entity_with_tool, target_container_name="large_beaker_0", stir_radius=0.02, stir_duration=5, insert_ratio=0.6666666667),
            partial(SkillLib.drop),
        ]
        return skill_sequence
