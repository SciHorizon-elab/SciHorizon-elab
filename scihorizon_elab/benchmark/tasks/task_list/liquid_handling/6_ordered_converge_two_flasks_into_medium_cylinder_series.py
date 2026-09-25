import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("6_ordered_converge_two_flasks_into_medium_cylinder")
class Task6OrderedConvergeTwoFlasksIntoMediumCylinderConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.3155, -0.1785), random.uniform(0.0565, 0.1935), 0.8],
            solution="CuSO4_solution_1",
            solution_rgba=[0, 0.45, 1, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="cylinder_mid_0",
            xml_path=name2class_xml["cylinder_mid"][-1],
            position=[random.uniform(-0.0250, 0.0250), random.uniform(-0.0935, -0.0435), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0150, 0.0150, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_1",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.0685, 0.0685), random.uniform(0.0565, 0.1935), 0.8],
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "flask_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Pick up the <flask_0> which contains <CuSO4 solution_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(is_grasped=dict(entities=['flask_0'], robot='robot')),
            dict(pour_into=dict(
            target_entity='flask_0',
            receiver_container='cylinder_mid_0',
            robot='robot',
        )),
            dict(is_grasped=dict(entities=['flask_1'], robot='robot')),
            dict(pour_into=dict(
            target_entity='flask_1',
            receiver_container='cylinder_mid_0',
            robot='robot',
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("6_ordered_converge_two_flasks_into_medium_cylinder")
class Task6OrderedConvergeTwoFlasksIntoMediumCylinderTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.pour_to_entity, target_container_name="cylinder_mid_0"),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="flask_1"),
            partial(SkillLib.pour_to_entity, target_container_name="cylinder_mid_0"),
            partial(SkillLib.drop),
        ]
        return skill_sequence
