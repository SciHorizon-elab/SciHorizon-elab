import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("3_insert_thermometer_into_small_beaker_then_flask")
class Task3InsertThermometerIntoSmallBeakerThenFlaskConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="thermometer_0",
            xml_path=name2class_xml["thermometer"][-1],
            position=[random.uniform(0.1095, 0.1175), random.uniform(0.0960, 0.1040), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0515, 0.0195), random.uniform(0.0670, 0.1350), 0.8],
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0.0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.0685, 0.0685), random.uniform(-0.1800, -0.0430), 0.8],
            solution="CuSO4_solution_1",
            solution_rgba=[0.0, 0.45, 1.0, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "thermometer_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Insert the <thermometer_0> into the <small_beaker_0> containing <KMnO4 solution_1>. Then pick up the <thermometer_0>. Then insert the <thermometer_0> into the <flask_0> containing <CuSO4 solution_1>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(contain=dict(container='small_beaker_0', entities=['thermometer_0'])),
            dict(is_grasped=dict(entities=['thermometer_0'], robot='robot')),
            dict(contain=dict(container='flask_0', entities=['thermometer_0'])),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("3_insert_thermometer_into_small_beaker_then_flask")
class Task3InsertThermometerIntoSmallBeakerThenFlaskTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="thermometer_0"),
            partial(SkillLib.place, target_container_name="small_beaker_0"),
            partial(SkillLib.pick, target_entity_name="thermometer_0"),
            partial(SkillLib.place, target_container_name="flask_0"),
        ]
        return skill_sequence
