import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

relative_col_pos = [-0.16, -0.08, 0, 0.08, 0.16]
relative_row_pos = [-0.05, 0.05]

@register.add_config_manager("10_pipette_small_beaker_to_flask_wait_then_pour_another_small_beaker_into_same_flask")
class Task10PipetteSmallBeakerToFlaskWaitThenPourAnotherSmallBeakerIntoSameFlaskConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_init_containers(self, init_container):
        if init_container is None or init_container == "chemistry_tube_stand":
            container_config = dict(
                name="chemistry_tube_stand",
                xml_path=name2class_xml["chemistry_tube_stand"][-1],
                position=[random.uniform(0.0950, 0.3300), random.uniform(-0.1300, 0.3300), 0.8],
            )
            container_config["class"] = "TubeStand"
            self.config["task"]["components"].append(container_config)

    def load_objects(self, target_entity):
        col_pos = random.choice(relative_col_pos)
        row_pos = random.choice(relative_row_pos)
        pos = [col_pos, row_pos, 0.05]
        init_container_config = next(            c for c in self.config["task"]["components"]            if c.get("name") == "chemistry_tube_stand"        )
        if "subentities" not in init_container_config:
            init_container_config["subentities"] = []
        obj_config = dict(
            name="pipette_0",
            xml_path=name2class_xml["pipette"][-1],
            position=pos,
        )
        obj_config["class"] = "Pipette"
        init_container_config["subentities"].append(obj_config)

        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.2670, -0.1960), random.uniform(0.1170, 0.1850), 0.8],
            solution="FeCl2_solution_1",
            solution_rgba=[0.6, 0.8, 0.6, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.1520, -0.0150), random.uniform(-0.1300, 0.0070), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="small_beaker_1",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.0860, -0.0150), random.uniform(0.1170, 0.1850), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "pipette_0"

    def get_instruction(self, target_entity, init_container, **kwargs):
        self.config["task"]["instructions"] = ["Use the <pipette_0> to aspirate <FeCl2 solution_0> from the <small_beaker_0>."]

    def get_condition_config(self, target_entity, init_container, **kwargs):
        conditions_config = [
            dict(aspirate=dict(
            source_container='small_beaker_0',
            tool='pipette_0',
            robot='robot',
            dwell_steps=20,
        )),
            dict(dispense=dict(
            target_container='flask_0',
            tool='pipette_0',
            robot='robot',
            dwell_steps=20,
        )),
            dict(wait_for=dict(
            entity='small_beaker_1',
            robot='robot',
            wait_duration=2.0,
            change_type='add_solution',
            solution='KMnO4_solution_0',
        )),
            dict(is_grasped=dict(entities=['small_beaker_1'], robot='robot')),
            dict(pour_into=dict(
            target_entity='small_beaker_1',
            receiver_container='flask_0',
            robot='robot',
            tilt_threshold=0,
            z_clearance=0.01,
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("10_pipette_small_beaker_to_flask_wait_then_pour_another_small_beaker_into_same_flask")
class Task10PipetteSmallBeakerToFlaskWaitThenPourAnotherSmallBeakerIntoSameFlaskTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="pipette_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.aspirate, source_container_name="small_beaker_0"),
            partial(SkillLib.moveto_entity, target_entity_name="flask_0", offset=np.array([0, 0, 0.08])),
            partial(SkillLib.dispense, target_container_name="flask_0"),
            partial(SkillLib.drop),
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="small_beaker_1", change_type="add_solution", solution="KMnO4"),
            partial(SkillLib.pick, target_entity_name="small_beaker_1"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.pour_to_entity, target_container_name="flask_0", tilt_angle=1.8, wait_time=10),
            partial(SkillLib.drop),
        ]
        return skill_sequence
