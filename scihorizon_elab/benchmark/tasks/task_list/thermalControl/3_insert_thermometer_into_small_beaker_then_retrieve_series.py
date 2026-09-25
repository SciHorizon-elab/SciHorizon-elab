import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("3_insert_thermometer_into_small_beaker_then_retrieve")
class Task3InsertThermometerIntoSmallBeakerThenRetrieveConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="thermometer_0",
            xml_path=name2class_xml["thermometer"][-1],
            position=[random.uniform(-0.0040, 0.0040), random.uniform(-0.0320, -0.0240), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(0.0660, 0.1340), 0.8],
            solution="CuSO4_solution_1",
            solution_rgba=[0, 0.45, 1, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "thermometer_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Insert the <thermometer_0> into the <small_beaker_0> containing <CuSO4 solution_0>. Wait for 3 seconds. Then pick up the <thermometer_0>. Then drop the <thermometer_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(contain=dict(container='small_beaker_0', entities=['thermometer_0'])),
            dict(is_grasped=dict(entities=['thermometer_0'], robot='robot')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("3_insert_thermometer_into_small_beaker_then_retrieve")
class Task3InsertThermometerIntoSmallBeakerThenRetrieveTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="thermometer_0"),
            partial(SkillLib.place, target_container_name="small_beaker_0"),
            partial(SkillLib.wait_for, wait_duration=3.0),
            partial(SkillLib.pick, target_entity_name="thermometer_0"),
            partial(SkillLib.drop),
        ]
        return skill_sequence
