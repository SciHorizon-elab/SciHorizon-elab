import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_wait_add_water_then_place_flask")
class Task2WaitAddWaterThenPlaceFlaskConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="water_bath_0",
            xml_path=name2class_xml["water_bath"][-1],
            position=[random.uniform(-0.1830, 0.3030), random.uniform(-0.0730, 0.2730), 0.8],
        )
        obj_config["class"] = "WaterBathContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.4300, -0.2930), random.uniform(0.0315, 0.1685), 0.8],
            solution="FeCl2_solution_1",
            solution_rgba=[0.56, 1.0, 0.56, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "water_bath_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Wait until a human adds <water_0> to the <water_bath_0>. Place the <flask_0> containing <FeCl2 solution_0> in the <water_bath_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(wait_for=dict(
            entity='water_bath_0',
            robot='robot',
            wait_duration=2.0,
            change_type='add_solution',
            solution='water',
        )),
            dict(contain=dict(container='water_bath_0', entities=['flask_0'])),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_wait_add_water_then_place_flask")
class Task2WaitAddWaterThenPlaceFlaskTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="water_bath_0", change_type="add_solution", solution="water"),
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.place, target_container_name="water_bath_0"),
        ]
        return skill_sequence
