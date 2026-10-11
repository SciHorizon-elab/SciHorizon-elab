import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("4_heat_small_beaker_then_flask_over_alcohol_flame")
class Task4HeatSmallBeakerThenFlaskOverAlcoholFlameConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="alcohol_lamp_0",
            xml_path=name2class_xml["alcohol_lamp"][-1],
            position=[random.uniform(-0.0505, 0.0505), random.uniform(-0.1450, -0.0440), 0.8],
        )
        obj_config["class"] = "AlcoholLamp"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(0.0660, 0.1340), 0.8],
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.2975, -0.1605), random.uniform(0.0315, 0.1685), 0.8],
            solution="CuSO4_solution_1",
            solution_rgba=[0, 0.45, 1, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "alcohol_lamp_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ['Wait until a human lights the alcohol lamp. Pick the small beaker containing KMnO4 solution. Then heat it with the alcohol lamp. Then drop it. Then pick the flask containing CuSO4 solution and heat it with the alcohol lamp. Then drop it. .']

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(wait_for=dict(entity='alcohol_lamp_0', robot='robot', wait_duration=2.0)),
            dict(is_grasped=dict(entities=['small_beaker_0'], robot='robot')),
            dict(heat_with_flame=dict(
            target_entity='small_beaker_0',
            heat_source='alcohol_lamp_0',
            robot='robot',
        )),
            dict(is_grasped=dict(entities=['flask_0'], robot='robot')),
            dict(heat_with_flame=dict(target_entity='flask_0', heat_source='alcohol_lamp_0', robot='robot')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("4_heat_small_beaker_then_flask_over_alcohol_flame")
class Task4HeatSmallBeakerThenFlaskOverAlcoholFlameTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="alcohol_lamp_0", change_type="Light_the_alcohol_lamp"),
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.heat_with_alcohol_lamp, target_entity_name="small_beaker_0", hold_time=3.0),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.heat_with_alcohol_lamp, target_entity_name="flask_0", hold_time=3.0),
            partial(SkillLib.drop),
        ]
        return skill_sequence
