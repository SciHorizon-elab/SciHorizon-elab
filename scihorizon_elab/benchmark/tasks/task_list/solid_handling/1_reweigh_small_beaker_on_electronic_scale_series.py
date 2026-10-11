import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("1_reweigh_small_beaker_on_electronic_scale")
class Task1ReweighSmallBeakerOnElectronicScaleConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(-0.1780, -0.1100), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="electronic_scale_0",
            xml_path=name2class_xml["electronic_scale"][-1],
            position=[random.uniform(-0.0680, 0.0680), random.uniform(0.0000, 0.2000), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the small beaker on the electronic scale, pick it up, and place it back on the electronic scale."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['small_beaker_0'], container='electronic_scale_0')),
            dict(is_grasped=dict(entities=['small_beaker_0'], robot='robot')),
            dict(on=dict(entities=['small_beaker_0'], container='electronic_scale_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("1_reweigh_small_beaker_on_electronic_scale")
class Task1ReweighSmallBeakerOnElectronicScaleTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.place, target_container_name="electronic_scale_0"),
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.place, target_container_name="electronic_scale_0"),
        ]
        return skill_sequence
