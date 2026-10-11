import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("5_alcohol_lamp_small_beaker_then_insert_thermometer")
class Task5AlcoholLampSmallBeakerThenInsertThermometerConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="alcohol_lamp_0",
            xml_path=name2class_xml["alcohol_lamp"][-1],
            position=[random.uniform(-0.0505, 0.0505), random.uniform(-0.1800, -0.0790), 0.8],
        )
        obj_config["class"] = "AlcoholLamp"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(0.1090, 0.1770), 0.8],
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="thermometer_0",
            xml_path=name2class_xml["thermometer"][-1],
            position=[random.uniform(-0.0040, 0.0040), random.uniform(0.0110, 0.0190), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "alcohol_lamp_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ['Wait until a human lights the alcohol lamp. Heat the small beaker containing KMnO4 solution with the alcohol lamp, drop it, then insert the thermometer into the small beaker.']

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(wait_for=dict(entity='alcohol_lamp_0', robot='robot', wait_duration=2.0)),
            dict(heat_with_flame=dict(
            target_entity='small_beaker_0',
            heat_source='alcohol_lamp_0',
            robot='robot',
            distance_threshold=0.02,
            duration=2.0,
        )),
            dict(contain=dict(container='small_beaker_0', entities=['thermometer_0'])),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("5_alcohol_lamp_small_beaker_then_insert_thermometer")
class Task5AlcoholLampSmallBeakerThenInsertThermometerTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="alcohol_lamp_0", change_type="Light_the_alcohol_lamp"),
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.heat_with_alcohol_lamp, target_entity_name="small_beaker_0", hold_time=3.0),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="thermometer_0"),
            partial(SkillLib.insert_to_entity, target_entity_name="small_beaker_0", insert_depth=0.05),
        ]
        return skill_sequence
