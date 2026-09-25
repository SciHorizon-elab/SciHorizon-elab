import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("10_two_human_additions_small_beaker_and_large_beaker_to_flask")
class Task10TwoHumanAdditionsSmallBeakerAndLargeBeakerToFlaskConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(0.0910, 0.1590), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.2825, -0.1455), random.uniform(0.0565, 0.1935), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="large_beaker_0",
            xml_path=name2class_xml["large_beaker"][-1],
            position=[random.uniform(0.1455, 0.2765), random.uniform(0.0625, 0.1875), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="mechanical_pipette_0",
            xml_path=name2class_xml["mechanical_pipette"][-1],
            position=[random.uniform(-0.0340, 0.0340), random.uniform(-0.0250, 0.0010), 0.8],
        )
        obj_config["class"] = "MechanicalPipette"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Wait until a human adds <CuSO4 solution_0> to the <small_beaker_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(wait_for=dict(
            entity='small_beaker_0',
            robot='robot',
            change_type='add_solution',
            solution='CuSO4',
        )),
            dict(pour_into=dict(
            target_entity='small_beaker_0',
            receiver_container='flask_0',
            robot='robot',
        )),
            dict(wait_for=dict(
            entity='large_beaker_0',
            robot='robot',
            change_type='add_solution',
            solution='FeCl2',
        )),
            dict(aspirate=dict(
            source_container='large_beaker_0',
            tool='mechanical_pipette_0',
            robot='robot',
        )),
            dict(dispense=dict(target_container='flask_0', tool='mechanical_pipette_0', robot='robot')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("10_two_human_additions_small_beaker_and_large_beaker_to_flask")
class Task10TwoHumanAdditionsSmallBeakerAndLargeBeakerToFlaskTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="small_beaker_0", change_type="add_solution", solution="CuSO4"),
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.pour_to_entity, target_container_name="flask_0", tilt_angle=1.8, wait_time=10),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.drop),
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="large_beaker_0", change_type="add_solution", solution="FeCl2"),
            partial(SkillLib.pick, target_entity_name="mechanical_pipette_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.aspirate, source_container_name="large_beaker_0", dwell_steps=20, descend_below_surface=0.01),
            partial(SkillLib.moveto_entity, target_entity_name="flask_0", offset=np.array([0, 0, 0.08])),
            partial(SkillLib.dispense, target_container_name="flask_0", dwell_steps=20),
            partial(SkillLib.drop),
        ]
        return skill_sequence
