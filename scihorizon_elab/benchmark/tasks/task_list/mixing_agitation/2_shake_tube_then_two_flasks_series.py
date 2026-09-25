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

@register.add_config_manager("2_shake_tube_then_two_flasks")
class Task2ShakeTubeThenTwoFlasksConfigManager(BenchTaskConfigManager):
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
        col_pos = relative_col_pos[0]
        row_pos = relative_row_pos[0]
        pos = [col_pos, row_pos, 0.05]
        init_container_config = next(            c for c in self.config["task"]["components"]            if c.get("name") == "chemistry_tube_stand"        )
        if "subentities" not in init_container_config:
            init_container_config["subentities"] = []
        obj_config = dict(
            name="tube_0",
            xml_path=name2class_xml["tube"][-1],
            solution="CuSO4_solution_1",
            solution_rgba=[0, 0.45, 1, 0.4],
            position=pos,
        )
        obj_config["class"] = "ChemistryTube"
        init_container_config["subentities"].append(obj_config)

        obj_config = dict(
            name="flask_0",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.1520, -0.0150), random.uniform(0.1170, 0.2540), 0.8],
            solution="FeCl2_solution_1",
            solution_rgba=[0.4, 0.8, 0.4, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="flask_1",
            xml_path=name2class_xml["flask"][-1],
            position=[random.uniform(-0.1520, -0.0150), random.uniform(-0.1300, 0.0070), 0.8],
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0, 0.5, 0.4],
        )
        obj_config["class"] = "ChemistryContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "tube_0"

    def get_instruction(self, target_entity, init_container, **kwargs):
        self.config["task"]["instructions"] = ["Shake the <tube_0> containing <CuSO4 solution_0>."]

    def get_condition_config(self, target_entity, init_container, **kwargs):
        conditions_config = [
            dict(shake=dict(
            entities=['tube_0'],
            robot='robot',
            min_direction_changes=3,
            min_angle_threshold=0.1,
            check_axis=1,
        )),
            dict(shake=dict(
            entities=['flask_0'],
            robot='robot',
            min_direction_changes=3,
            min_angle_threshold=0.1,
            check_axis=1,
        )),
            dict(shake=dict(
            entities=['flask_1'],
            robot='robot',
            min_direction_changes=3,
            min_angle_threshold=0.1,
            check_axis=1,
        )),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("2_shake_tube_then_two_flasks")
class Task2ShakeTubeThenTwoFlasksTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="tube_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.shake, n_shakes=3, shake_angle=0.7, steps_per_swing=5),
            partial(SkillLib.insert_to_entity, target_entity_name="chemistry_tube_stand"),
            partial(SkillLib.pick, target_entity_name="flask_0"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.shake, n_shakes=3, shake_angle=0.7, steps_per_swing=5),
            partial(SkillLib.drop),
            partial(SkillLib.pick, target_entity_name="flask_1"),
            partial(SkillLib.lift, lift_height=0.15),
            partial(SkillLib.shake, n_shakes=3, shake_angle=0.7, steps_per_swing=5),
            partial(SkillLib.drop),
        ]
        return skill_sequence
