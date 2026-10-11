import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_place_small_beaker_then_flask_on_balance")
class Task2PlaceSmallBeakerThenFlaskOnBalanceConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(-0.1110, -0.0430), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="balance_0",
            xml_path=name2class_xml["balance"][-1],
            position=[random.uniform(-0.2250, 0.2250), random.uniform(0.0671, 0.2549), 0.7974],
        )
        obj_config["class"] = "Container"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.2825, -0.1455), random.uniform(-0.1800, -0.0430), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the small beaker on the balance. Then place the flask on the balance."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['small_beaker_0'], container='balance_0')),
            dict(on=dict(entities=['flask_0'], container='balance_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_place_small_beaker_then_flask_on_balance")
class Task2PlaceSmallBeakerThenFlaskOnBalanceTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.place, target_container_name="balance_0"),
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.place, target_container_name="balance_0"),
        ]
        return skill_sequence
