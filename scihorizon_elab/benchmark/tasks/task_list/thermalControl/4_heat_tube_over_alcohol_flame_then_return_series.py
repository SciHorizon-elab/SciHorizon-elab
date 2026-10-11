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

@register.add_config_manager("4_heat_tube_over_alcohol_flame_then_return")
class Task4HeatTubeOverAlcoholFlameThenReturnConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_init_containers(self, init_container):
        if init_container is None or init_container == "chemistry_tube_stand":
            container_config = dict(
                name="chemistry_tube_stand_0",
                xml_path=name2class_xml["chemistry_tube_stand"][-1],
                position=[random.uniform(-0.1175, 0.1175), random.uniform(-0.1300, 0.3300), 0.8],
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
            solution="KMnO4_solution_1",
            solution_rgba=[0.5, 0, 0.5, 0.4],
            position=pos,
        )
        obj_config["class"] = "ChemistryTube"
        init_container_config["subentities"].append(obj_config)

        obj_config = dict(
            name="alcohol_lamp_0",
            xml_path=name2class_xml["alcohol_lamp"][-1],
            position=[random.uniform(0.2275, 0.3285), random.uniform(0.0495, 0.1505), 0.8],
        )
        obj_config["class"] = "AlcoholLamp"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "tube_0"

    def get_instruction(self, target_entity, init_container, **kwargs):
        self.config["task"]["instructions"] = ['Wait until a human lights the alcohol lamp. Pick up the tube containing KMnO4 solution, . heat it with the alcohol lamp, then insert it back into the tube stand.']

    def get_condition_config(self, target_entity, init_container, **kwargs):
        conditions_config = [
            dict(wait_for=dict(entity='alcohol_lamp_0', robot='robot', wait_duration=2.0)),
            dict(is_grasped=dict(entities=['tube_0'], robot='robot')),
            dict(heat_with_flame=dict(
            target_entity='tube_0',
            heat_source='alcohol_lamp_0',
            robot='robot',
            distance_threshold=0.02,
            duration=2.0,
        )),
            dict(contain=dict(container='chemistry_tube_stand_0', entities=['tube_0'])),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("4_heat_tube_over_alcohol_flame_then_return")
class Task4HeatTubeOverAlcoholFlameThenReturnTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.wait_for, wait_duration=2.0, entity_name="alcohol_lamp_0", change_type="Light_the_alcohol_lamp"),
            partial(SkillLib.pick, target_entity_name="tube_0"),
            partial(SkillLib.heat_with_alcohol_lamp, target_entity_name="tube_0"),
            partial(SkillLib.insert_to_entity, target_entity_name="chemistry_tube_stand_0"),
        ]
        return skill_sequence
