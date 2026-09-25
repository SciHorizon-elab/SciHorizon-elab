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

@register.add_config_manager("10_wait_then_mechanical_pipette_large_beaker_to_tube")
class Task10WaitThenMechanicalPipetteLargeBeakerToTubeConfigManager(BenchTaskConfigManager):
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
        obj_config = dict(
            name="large_beaker_0",
            xml_path=name2class_xml["large_beaker"][-1],
            position=[random.uniform(-0.1460, -0.0150), random.uniform(-0.1030, 0.0220), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="mechanical_pipette_0",
            xml_path=name2class_xml["mechanical_pipette"][-1],
            position=[random.uniform(-0.0830, -0.0150), random.uniform(0.1120, 0.1380), 0.8],
        )
        obj_config["class"] = "MechanicalPipette"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0100, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        col_pos = relative_col_pos[0]
        row_pos = relative_row_pos[0]
        pos = [col_pos, row_pos, 0.05]
        init_container_config = next(            c for c in self.config["task"]["components"]            if c.get("name") == "chemistry_tube_stand"        )
        if "subentities" not in init_container_config:
            init_container_config["subentities"] = []
        obj_config = dict(
            name="tube_0",
            xml_path=name2class_xml["tube"][-1],
            position=pos,
        )
        obj_config["class"] = "ChemistryTube"
        init_container_config["subentities"].append(obj_config)

        self.target_entity = "large_beaker_0"

    def get_instruction(self, target_entity, init_container, **kwargs):
        self.config["task"]["instructions"] = ["Wait until a human adds <FeCl2 solution_0> to the <large_beaker_0>."]

    def get_condition_config(self, target_entity, init_container, **kwargs):
        conditions_config = [
            dict(wait_for=dict(
            entity='large_beaker_0',
            robot='robot',
            wait_duration=2.0,
            change_type='add_solution',
            solution='FeCl2',
        )),
            dict(aspirate=dict(
            source_container='large_beaker_0',
            tool='mechanical_pipette_0',
            robot='robot',
            dwell_steps=20,
        )),
            dict(dispense=dict(
            target_container='tube_0',
            tool='mechanical_pipette_0',
            robot='robot',
            dwell_steps=20,
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("10_wait_then_mechanical_pipette_large_beaker_to_tube")
class Task10WaitThenMechanicalPipetteLargeBeakerToTubeTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="large_beaker_0", change_type="add_solution", solution="FeCl2"),
            partial(SkillLib.pick, target_entity_name="mechanical_pipette_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.aspirate, source_container_name="large_beaker_0"),
            partial(SkillLib.moveto_entity, target_entity_name="tube_0", offset=np.array([0, 0, 0.08])),
            partial(SkillLib.dispense, target_container_name="tube_0"),
            partial(SkillLib.drop),
        ]
        return skill_sequence
