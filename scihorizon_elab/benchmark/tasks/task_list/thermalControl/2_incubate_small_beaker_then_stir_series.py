import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_incubate_small_beaker_then_stir")
class Task2IncubateSmallBeakerThenStirConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="water_bath_0",
            xml_path=name2class_xml["water_bath"][-1],
            position=[random.uniform(-0.2430, 0.2430), random.uniform(-0.0020, 0.3440), 0.8],
        )
        obj_config["class"] = "WaterBathContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.1605, -0.0895), random.uniform(-0.1800, -0.1120), 0.8],
            solution="CuSO4_solution_1",
            solution_rgba=[0, 0.45, 1, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="glass_stirring_rod_0",
            xml_path=name2class_xml["glass_stirring_rod"][-1],
            position=[random.uniform(0.0005, 0.0085), random.uniform(-0.1000, -0.0920), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "water_bath_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Wait until a human adds <water_0> to the <water_bath_0>. Place the <small_beaker_0> containing <CuSO4 solution_0> in the <water_bath_0>. Wait for 3 seconds. Then pick up the <glass_stirring_rod_0>. Then stir the <CuSO4 solution_0> in the <small_beaker_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(wait_for=dict(
            entity='water_bath_0',
            robot='robot',
            wait_duration=2.0,
            change_type='add_solution',
            solution='water',
        )),
            dict(contain=dict(container='water_bath_0', entities=['small_beaker_0'])),
            dict(is_grasped=dict(entities=['glass_stirring_rod_0'], robot='robot')),
            dict(stir=dict(
            entities=['glass_stirring_rod_0'],
            container='small_beaker_0',
            robot='robot',
            min_distance=0.15,
            tool_tip_site='bottom_site',
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_incubate_small_beaker_then_stir")
class Task2IncubateSmallBeakerThenStirTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="water_bath_0", change_type="add_solution", solution="water"),
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.place, target_container_name="water_bath_0"),
            partial(SkillLib.wait, wait_time=3),
            partial(SkillLib.pick, target_entity_name="glass_stirring_rod_0"),
            partial(SkillLib.stir_entity_with_tool, target_container_name="small_beaker_0"),
        ]
        return skill_sequence
