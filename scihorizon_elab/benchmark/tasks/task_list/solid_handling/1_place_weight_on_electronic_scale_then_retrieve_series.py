import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("1_place_weight_on_electronic_scale_then_retrieve")
class Task1PlaceWeightOnElectronicScaleThenRetrieveConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="weight_0",
            xml_path=name2class_xml["weight"][-1],
            position=[random.uniform(-0.0144, 0.0144), random.uniform(-0.0689, -0.0401), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="electronic_scale_0",
            xml_path=name2class_xml["electronic_scale"][-1],
            position=[random.uniform(-0.2405, -0.1044), random.uniform(0.0000, 0.2000), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="chemistry_lab_table_0",
            xml_path=name2class_xml["chemistry_lab_table"][-1],
            position=[random.uniform(0.0055, 0.1055), random.uniform(0.0500, 0.1500), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "weight_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the weight on the electronic scale, then pick it up and drop it on the table."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['weight_0'], container='electronic_scale_0')),
            dict(is_grasped=dict(entities=['weight_0'], robot='robot')),
            dict(on=dict(entities=['weight_0'], container='chemistry_lab_table_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("1_place_weight_on_electronic_scale_then_retrieve")
class Task1PlaceWeightOnElectronicScaleThenRetrieveTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.place, target_container_name="electronic_scale_0"),
            partial(SkillLib.pick, target_entity_name="weight_0"),
            partial(SkillLib.drop),
        ]
        return skill_sequence
