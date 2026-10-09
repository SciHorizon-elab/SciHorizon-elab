import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("1_place_beaker_flask_and_petri_on_three_square_mats")
class Task1PlaceBeakerFlaskAndPetriOnThreeSquareMatsConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(-0.1800, -0.1120), 0.8],
            solution="CuSO4_solution_1",
            solution_rgba=[0, 0.45, 1, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="square_mat_green_0",
            xml_path=name2class_xml["square_mat_green"][-1],
            position=[random.uniform(0.1810, 0.3320), random.uniform(0.0245, 0.1755), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.2825, -0.1455), random.uniform(-0.1800, -0.0430), 0.8],
            solution="FeCl2_solution_1",
            solution_rgba=[0.6, 1, 0.6, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="square_mat_yellow_0",
            xml_path=name2class_xml["square_mat_yellow"][-1],
            position=[random.uniform(-0.3410, -0.1900), random.uniform(0.0670, 0.2180), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="petri_dish_0",
            xml_path=name2class_xml["petri_dish"][-1],
            position=[random.uniform(-0.0315, 0.0315), random.uniform(-0.0040, 0.0590), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0189, 0.0189, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="square_mat_purple_0",
            xml_path=name2class_xml["square_mat_purple"][-1],
            position=[random.uniform(-0.0800, 0.0710), random.uniform(0.1670, 0.3180), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place one item on each square mat: the small beaker containing CuSO4 solution on the green square mat, the flask containing FeCl2 solution on the yellow square mat, and the petri dish on the purple square mat."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['small_beaker_0'], container='square_mat_green_0')),
            dict(on=dict(entities=['flask_0'], container='square_mat_yellow_0')),
            dict(on=dict(entities=['petri_dish_0'], container='square_mat_purple_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("1_place_beaker_flask_and_petri_on_three_square_mats")
class Task1PlaceBeakerFlaskAndPetriOnThreeSquareMatsTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.place, target_container_name="square_mat_green_0"),
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.place, target_container_name="square_mat_yellow_0"),
            partial(SkillLib.pick, target_entity_name="petri_dish_0"),
            partial(SkillLib.place, target_container_name="square_mat_purple_0"),
        ]
        return skill_sequence
