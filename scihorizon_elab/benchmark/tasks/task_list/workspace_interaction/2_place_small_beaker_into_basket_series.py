import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_place_small_beaker_into_basket")
class Task2PlaceSmallBeakerIntoBasketConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(0.1300, 0.150), random.uniform(0.0660, 0.1040), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="basket_0",
            xml_path=name2class_xml["basket"][-1],
            position=[random.uniform(-0.2300, -0.2200), random.uniform(-0.0007, 0.1007), 0.8],
        )
        obj_config["class"] = "Container"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the small beaker into the basket."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(contain=dict(container='basket_0', entities=['small_beaker_0'])),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_place_small_beaker_into_basket")
class Task2PlaceSmallBeakerIntoBasketTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="small_beaker_0", prior_eulers=[[-3.141592653589793, 0, 0]]),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.place, target_container_name="basket_0"),
        ]
        return skill_sequence
