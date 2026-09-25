import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("9_ordered_addition_three_stage_small_beaker_then_flask_then_mechanical_pipette_large_beaker_into_medium_cylinder")
class Task9OrderedAdditionThreeStageSmallBeakerThenFlaskThenMechanicalPipetteLargeBeakerIntoMediumCylinderConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0355, 0.0355), random.uniform(-0.1300, -0.0620), 0.8],
            solution="CuSO4_1",
            solution_rgba=[0, 0.45, 1, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="cylinder_mid_0",
            xml_path=name2class_xml["cylinder_mid"][-1],
            position=[random.uniform(-0.0250, 0.0250), random.uniform(0.1340, 0.1840), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0150, 0.0150, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.2810, -0.1440), random.uniform(0.0565, 0.1935), 0.8],
            solution="FeCl2_1",
            solution_rgba=[0.56, 0.8, 0.56, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="mechanical_pipette_0",
            xml_path=name2class_xml["mechanical_pipette"][-1],
            position=[random.uniform(-0.1340, -0.0840), random.uniform(0.0280, 0.0540), 0.8],
        )
        obj_config["class"] = "MechanicalPipette"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="large_beaker_0",
            xml_path=name2class_xml["large_beaker"][-1],
            position=[random.uniform(0.1440, 0.2750), random.uniform(0.0625, 0.1875), 0.8],
            solution="KMnO4_1",
            solution_rgba=[0.5, 0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Pick up the <small_beaker_0> which contains <CuSO4 solution_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(is_grasped=dict(entities=['small_beaker_0'], robot='robot')),
            dict(pour_into=dict(
            target_entity='small_beaker_0',
            receiver_container='cylinder_mid_0',
            robot='robot',
            tilt_threshold=0,
            z_clearance=0.01,
        )),
            dict(is_grasped=dict(entities=['flask_0'], robot='robot')),
            dict(pour_into=dict(
            target_entity='flask_0',
            receiver_container='cylinder_mid_0',
            robot='robot',
            tilt_threshold=0,
            z_clearance=0.01,
        )),
            dict(is_grasped=dict(entities=['mechanical_pipette_0'], robot='robot')),
            dict(aspirate=dict(
            source_container='large_beaker_0',
            tool='mechanical_pipette_0',
            robot='robot',
            dwell_steps=20,
        )),
            dict(dispense=dict(
            target_container='cylinder_mid_0',
            tool='mechanical_pipette_0',
            robot='robot',
            dwell_steps=20,
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("9_ordered_addition_three_stage_small_beaker_then_flask_then_mechanical_pipette_large_beaker_into_medium_cylinder")
class Task9OrderedAdditionThreeStageSmallBeakerThenFlaskThenMechanicalPipetteLargeBeakerIntoMediumCylinderTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.pour_to_entity, target_container_name="cylinder_mid_0", tilt_angle=1.8, wait_time=10),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.pour_to_entity, target_container_name="cylinder_mid_0", tilt_angle=1.8, wait_time=10),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="mechanical_pipette_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.aspirate, source_container_name="large_beaker_0", dwell_steps=20, descend_below_surface=0.01),
            partial(SkillLib.moveto_entity, target_entity_name="cylinder_mid_0", offset=np.array([0, 0, 0.08])),
            partial(SkillLib.dispense, target_container_name="cylinder_mid_0", dwell_steps=20),
            partial(SkillLib.drop),
        ]
        return skill_sequence
