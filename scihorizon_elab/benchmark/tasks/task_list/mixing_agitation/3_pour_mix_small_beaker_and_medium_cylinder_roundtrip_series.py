import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("3_pour_mix_small_beaker_and_medium_cylinder_roundtrip")
class Task3PourMixSmallBeakerAndMediumCylinderRoundtripConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(0.0910, 0.1590), 0.8],
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0.0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="cylinder_mid_0",
            xml_path=name2class_xml["cylinder_mid"][-1],
            position=[random.uniform(-0.0250, 0.0250), random.uniform(-0.0590, -0.0090), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0150, 0.0150, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Pour the <KMnO4 solution_0> from the <small_beaker_0> into the <cylinder_mid_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(pour_into=dict(
            target_entity='small_beaker_0',
            receiver_container='cylinder_mid_0',
            robot='robot',
            tilt_threshold=0,
            z_clearance=0.01,
        )),
            dict(pour_into=dict(
            target_entity='cylinder_mid_0',
            receiver_container='small_beaker_0',
            robot='robot',
            tilt_threshold=0,
            z_clearance=0.01,
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("3_pour_mix_small_beaker_and_medium_cylinder_roundtrip")
class Task3PourMixSmallBeakerAndMediumCylinderRoundtripTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.pour_to_entity, target_container_name="cylinder_mid_0"),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="cylinder_mid_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.pour_to_entity, target_container_name="small_beaker_0"),
            partial(SkillLib.drop),
        ]
        return skill_sequence
