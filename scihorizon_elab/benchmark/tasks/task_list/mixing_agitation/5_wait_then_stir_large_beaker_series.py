import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("5_wait_then_stir_large_beaker")
class Task5WaitThenStirLargeBeakerConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="large_beaker_0",
            xml_path=name2class_xml["large_beaker"][-1],
            position=[random.uniform(-0.0655, 0.0655), random.uniform(0.0625, 0.1875), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="glass_stirring_rod_0",
            xml_path=name2class_xml["glass_stirring_rod"][-1],
            position=[random.uniform(-0.0040, 0.0040), random.uniform(-0.0355, -0.0275), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "large_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Wait until a human adds <FeCl2 solution_0> to the <large_beaker_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(wait_for=dict(
            entity='large_beaker_0',
            robot='robot',
            wait_duration=2.0,
            change_type='add_solution',
            solution='FeCl2',
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


@register.add_task("5_wait_then_stir_large_beaker")
class Task5WaitThenStirLargeBeakerTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="large_beaker_0", change_type="add_solution", solution="FeCl2"),
            partial(SkillLib.pick, target_entity_name="glass_stirring_rod_0"),
            partial(SkillLib.stir_entity_with_tool, target_container_name="large_beaker_0", stir_radius=0.02, stir_duration=5, insert_ratio=0.6666666667),
        ]
        return skill_sequence
