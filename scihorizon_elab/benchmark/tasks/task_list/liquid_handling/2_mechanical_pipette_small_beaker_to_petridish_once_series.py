import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("2_mechanical_pipette_small_beaker_to_petridish_once")
class Task2MechanicalPipetteSmallBeakerToPetridishOnceConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="mechanical_pipette_0",
            xml_path=name2class_xml["mechanical_pipette"][-1],
            position=[random.uniform(-0.0340, 0.0340), random.uniform(0.0280, 0.0540), 0.8],
        )
        obj_config["class"] = "MechanicalPipette"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(-0.1300, -0.0620), 0.8],
            solution="FeCl2_solution_1",
            solution_rgba=[0.56, 0.75, 0.56, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="petri_dish_0",
            xml_path=name2class_xml["petri_dish"][-1],
            position=[random.uniform(-0.0315, 0.0315), random.uniform(0.1420, 0.2050), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0189, 0.0189, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "mechanical_pipette_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Pick up <mechanical_pipette_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(is_grasped=dict(entities=['mechanical_pipette_0'], robot='robot')),
            dict(aspirate=dict(
            source_container='small_beaker_0',
            tool='mechanical_pipette_0',
            robot='robot',
            dwell_steps=20,
        )),
            dict(dispense=dict(
            target_container='petri_dish_0',
            tool='mechanical_pipette_0',
            robot='robot',
            dwell_steps=20,
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_mechanical_pipette_small_beaker_to_petridish_once")
class Task2MechanicalPipetteSmallBeakerToPetridishOnceTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="mechanical_pipette_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.aspirate, source_container_name="small_beaker_0"),
            partial(SkillLib.moveto_entity, target_entity_name="petri_dish_0", offset=np.array([0, 0, 0.08])),
            partial(SkillLib.dispense, target_container_name="petri_dish_0"),
        ]
        return skill_sequence
