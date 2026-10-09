import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_place_aragonite_then_calcite_on_balance_then_remove_both")
class Task2PlaceAragoniteThenCalciteOnBalanceThenRemoveBothConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="mineral_aragonite_0",
            xml_path=name2class_xml["mineral_aragonite"][-1],
            position=[random.uniform(-0.0350, 0.0350), random.uniform(-0.1834, -0.1266), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0170, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="balance_0",
            xml_path=name2class_xml["balance"][-1],
            position=[random.uniform(-0.2250, 0.2250), random.uniform(0.1096, 0.2974), 0.7974],
        )
        obj_config["class"] = "Container"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="mineral_calcite_blue_0",
            xml_path=name2class_xml["mineral_calcite_blue"][-1],
            position=[random.uniform(-0.0350, 0.0350), random.uniform(-0.0345, 0.0115), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0138, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "mineral_aragonite_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the aragonite mineral on the balance. Then place the blue calcite mineral on the balance. Pick up the aragonite mineral and drop it. Then pick up the blue calcite mineral and drop it."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['mineral_aragonite_0'], container='balance_0')),
            dict(on=dict(entities=['mineral_calcite_blue_0'], container='balance_0')),
            dict(is_grasped=dict(entities=['mineral_aragonite_0'], robot='robot')),
            dict(is_grasped=dict(entities=['mineral_calcite_blue_0'], robot='robot')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_place_aragonite_then_calcite_on_balance_then_remove_both")
class Task2PlaceAragoniteThenCalciteOnBalanceThenRemoveBothTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="mineral_aragonite_0"),
            partial(SkillLib.place, target_container_name="balance_0"),
            partial(SkillLib.pick, target_entity_name="mineral_calcite_blue_0"),
            partial(SkillLib.place, target_container_name="balance_0"),
            partial(SkillLib.pick, target_entity_name="mineral_aragonite_0"),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="mineral_calcite_blue_0"),
            partial(SkillLib.drop),
        ]
        return skill_sequence
