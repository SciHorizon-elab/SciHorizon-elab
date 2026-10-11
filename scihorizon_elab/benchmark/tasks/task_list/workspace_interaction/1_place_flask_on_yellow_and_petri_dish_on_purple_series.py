import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("1_place_flask_on_yellow_and_petri_dish_on_purple")
class Task1PlaceFlaskOnYellowAndPetriDishOnPurpleConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.0685, 0.0685), random.uniform(-0.1765, -0.0395), 0.8],
            solution="FeCl2_solution_1",
            solution_rgba=[0.6, 0.8, 0.6, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="square_mat_yellow_0",
            xml_path=name2class_xml["square_mat_yellow"][-1],
            position=[random.uniform(0.1785, 0.3295), random.uniform(0.0245, 0.1755), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="petri_dish_0",
            xml_path=name2class_xml["petri_dish"][-1],
            position=[random.uniform(-0.0315, 0.0315), random.uniform(0.0685, 0.1315), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0189, 0.0189, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="square_mat_purple_0",
            xml_path=name2class_xml["square_mat_purple"][-1],
            position=[random.uniform(-0.3295, -0.1785), random.uniform(0.0245, 0.1755), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "flask_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the flask containing FeCl2 solution on the yellow square mat, then place the petri dish on the purple square mat."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['flask_0'], container='square_mat_yellow_0')),
            dict(on=dict(entities=['petri_dish_0'], container='square_mat_purple_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("1_place_flask_on_yellow_and_petri_dish_on_purple")
class Task1PlaceFlaskOnYellowAndPetriDishOnPurpleTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.place, target_container_name="square_mat_yellow_0"),
            partial(SkillLib.pick, target_entity_name="petri_dish_0"),
            partial(SkillLib.place, target_container_name="square_mat_purple_0"),
        ]
        return skill_sequence
