import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_place_weight_then_replace_aragonite_with_halite_on_balance")
class Task2PlaceWeightThenReplaceAragoniteWithHaliteOnBalanceConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="weight_0",
            xml_path=name2class_xml["weight"][-1],
            position=[random.uniform(-0.0144, 0.0144), random.uniform(0.0980, 0.1270), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="balance_0",
            xml_path=name2class_xml["balance"][-1],
            position=[random.uniform(-0.2250, 0.2250), random.uniform(-0.1799, 0.0079), 0.7974],
        )
        obj_config["class"] = "Container"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="mineral_aragonite_0",
            xml_path=name2class_xml["mineral_aragonite"][-1],
            position=[random.uniform(0.1045, 0.1745), random.uniform(0.1122, 0.1689), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0170, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="mineral_halite_0",
            xml_path=name2class_xml["mineral_halite"][-1],
            position=[random.uniform(-0.1744, -0.1046), random.uniform(0.1180, 0.1880), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "weight_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the weight on the balance. Then place the aragonite mineral on the balance, pick it up and drop it. Then place the halite mineral on the balance."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['weight_0'], container='balance_0')),
            dict(on=dict(entities=['mineral_aragonite_0'], container='balance_0')),
            dict(is_grasped=dict(entities=['mineral_aragonite_0'], robot='robot')),
            dict(on=dict(entities=['mineral_halite_0'], container='balance_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_place_weight_then_replace_aragonite_with_halite_on_balance")
class Task2PlaceWeightThenReplaceAragoniteWithHaliteOnBalanceTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="weight_0"),
            partial(SkillLib.place, target_container_name="balance_0"),
            partial(SkillLib.pick, target_entity_name="mineral_aragonite_0"),
            partial(SkillLib.place, target_container_name="balance_0"),
            partial(SkillLib.pick, target_entity_name="mineral_aragonite_0"),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="mineral_halite_0"),
            partial(SkillLib.place, target_container_name="balance_0"),
        ]
        return skill_sequence
