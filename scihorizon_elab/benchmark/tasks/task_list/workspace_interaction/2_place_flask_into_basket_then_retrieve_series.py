import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_place_flask_into_basket_then_retrieve")
class Task2PlaceFlaskIntoBasketThenRetrieveConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(0.1300, 0.2670), random.uniform(0.0315, 0.1685), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="basket_0",
            xml_path=name2class_xml["basket"][-1],
            position=[random.uniform(-0.4300, 0.0200), random.uniform(-0.1007, 0.3007), 0.8],
        )
        obj_config["class"] = "Container"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "flask_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the flask into the basket, then pick it up and drop it."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(contain=dict(container='basket_0', entities=['flask_0'])),
            dict(is_grasped=dict(entities=['flask_0'], robot='robot')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_place_flask_into_basket_then_retrieve")
class Task2PlaceFlaskIntoBasketThenRetrieveTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.place, target_container_name="basket_0"),
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.drop),
        ]
        return skill_sequence
