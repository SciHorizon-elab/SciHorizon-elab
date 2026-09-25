import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("pick_beaker_place_beaker")
class PickBeakerPlaceBeakerConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="beaker_0",
            xml_path=name2class_xml["beaker"][-1],
            position=[random.uniform(-0.3, -0.15), random.uniform(-0.05, 0.1), 0.8],
        )
        obj_config["class"] = "ChemistryBeaker"
        obj_config["randomness"] = dict(pos=[0.02, 0.02, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="square_mat_0",
            xml_path=name2class_xml["square_mat"][-1],
            position=[random.uniform(-0.15, 0.0), random.uniform(-0.05, 0.1), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.02, 0.02, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Pick the <beaker_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(is_grasped=dict(entities=['beaker_0'], robot='robot')),
            dict(on=dict(entities=['beaker_0'], container='square_mat_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("pick_beaker_place_beaker")
class PickBeakerPlaceBeakerTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="beaker_0", prior_eulers=[[-3.14159, 0, 0]]),
            partial(SkillLib.place, target_container_name="square_mat_0"),
        ]
        return skill_sequence
