import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_shake_two_flasks_in_order")
class Task2ShakeTwoFlasksInOrderConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.0685, 0.0685), random.uniform(0.1170, 0.2540), 0.8],
            solution="FeCl2_solution_1",
            solution_rgba=[0.6, 0.8, 0.6, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_1",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.0685, 0.0685), random.uniform(-0.1300, 0.0070), 0.8],
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0.0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "flask_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Shake the flask_0 containing FeCl2 solution_1."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(shake=dict(entities=['flask_0'], robot='robot')),
            dict(shake=dict(entities=['flask_1'], robot='robot')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_shake_two_flasks_in_order")
class Task2ShakeTwoFlasksInOrderTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.shake, n_shakes=3, shake_angle=0.7, steps_per_swing=5),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="flask_1"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.shake, n_shakes=3, shake_angle=0.7, steps_per_swing=5),
            partial(SkillLib.drop),
        ]
        return skill_sequence
