import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("4_mechanical_pipette_large_beaker_to_small_beaker_then_stir")
class Task4MechanicalPipetteLargeBeakerToSmallBeakerThenStirConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="mechanical_pipette_0",
            xml_path=name2class_xml["mechanical_pipette"][-1],
            position=[random.uniform(-0.0340, 0.0340), random.uniform(0.1120, 0.1380), 0.8],
        )
        obj_config["class"] = "MechanicalPipette"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="large_beaker_0",
            xml_path=name2class_xml["large_beaker"][-1],
            position=[random.uniform(-0.2750, -0.1440), random.uniform(0.0625, 0.1875), 0.8],
            solution="CuSO4_solution_1",
            solution_rgba=[0, 0.45, 1, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(-0.1240, -0.0560), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="glass_stirring_rod_0",
            xml_path=name2class_xml["glass_stirring_rod"][-1],
            position=[random.uniform(-0.0040, 0.0040), random.uniform(0.0340, 0.0420), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0100, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "mechanical_pipette_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Use the <mechanical_pipette_0> to aspirate <CuSO4_solution_0> from the <large_beaker_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(aspirate=dict(
            source_container='large_beaker_0',
            tool='mechanical_pipette_0',
            robot='robot',
        )),
            dict(dispense=dict(
            target_container='small_beaker_0',
            tool='mechanical_pipette_0',
            robot='robot',
        )),
            dict(stir=dict(
            entities=['glass_stirring_rod_0'],
            container='small_beaker_0',
            robot='robot',
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("4_mechanical_pipette_large_beaker_to_small_beaker_then_stir")
class Task4MechanicalPipetteLargeBeakerToSmallBeakerThenStirTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="mechanical_pipette_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.aspirate, source_container_name="large_beaker_0"),
            partial(SkillLib.moveto_entity, target_entity_name="small_beaker_0", offset=np.array([0, 0, 0.08])),
            partial(SkillLib.dispense, target_container_name="small_beaker_0"),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="glass_stirring_rod_0"),
            partial(SkillLib.stir_entity_with_tool, target_container_name="small_beaker_0"),
            partial(SkillLib.drop),
        ]
        return skill_sequence
