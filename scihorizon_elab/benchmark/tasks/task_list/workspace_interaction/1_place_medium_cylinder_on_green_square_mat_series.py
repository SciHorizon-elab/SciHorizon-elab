import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("1_place_medium_cylinder_on_green_square_mat")
class Task1PlaceMediumCylinderOnGreenSquareMatConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="cylinder_mid_0",
            xml_path=name2class_xml["cylinder_mid"][-1],
            position=[random.uniform(-0.0250, 0.0250), random.uniform(-0.1255, -0.0755), 0.8],
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0.0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0150, 0.0150, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="square_mat_green_0",
            xml_path=name2class_xml["square_mat_green"][-1],
            position=[random.uniform(-0.0755, 0.0755), random.uniform(0.0245, 0.1755), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "cylinder_mid_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the medium cylinder containing KMnO4 solution on the green square mat."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['cylinder_mid_0'], container='square_mat_green_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("1_place_medium_cylinder_on_green_square_mat")
class Task1PlaceMediumCylinderOnGreenSquareMatTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="cylinder_mid_0"),
            partial(SkillLib.place, target_container_name="square_mat_green_0"),
        ]
        return skill_sequence
