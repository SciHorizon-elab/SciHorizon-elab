import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

@register.add_config_manager("1_weigh_fluorite_then_halite_on_electronic_scale")
class Task1WeighFluoriteThenHaliteOnElectronicScaleConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="mineral_fluorite_0",
            xml_path=name2class_xml["mineral_fluorite"][-1],
            position=[random.uniform(-0.0350, 0.0350), random.uniform(-0.0960, -0.0391), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0171, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="electronic_scale_0",
            xml_path=name2class_xml["electronic_scale"][-1],
            position=[random.uniform(-0.2811, -0.1449), random.uniform(0.0000, 0.2000), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="chemistry_lab_table_0",
            xml_path=name2class_xml["chemistry_lab_table"][-1],
            position=[random.uniform(0.1450, 0.2450), random.uniform(0.0500, 0.1500), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="mineral_halite_0",
            xml_path=name2class_xml["mineral_halite"][-1],
            position=[random.uniform(-0.0349, 0.0349), random.uniform(0.0650, 0.1350), 0.8],
        )
        obj_config["class"] = "CommonGraspedEntity"
        obj_config["randomness"] = dict(pos=[0.0200, 0.0200, 0], quat=[0, 0, 0.05])
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "mineral_fluorite_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Place the fluorite mineral on the electronic scale, pick it up and drop it on the table. Then place the halite mineral on the electronic scale."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(on=dict(entities=['mineral_fluorite_0'], container='electronic_scale_0')),
            dict(is_grasped=dict(entities=['mineral_fluorite_0'], robot='robot')),
            dict(on=dict(entities=['mineral_fluorite_0'], container='chemistry_lab_table_0')),
            dict(on=dict(entities=['mineral_halite_0'], container='electronic_scale_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("1_weigh_fluorite_then_halite_on_electronic_scale")
class Task1WeighFluoriteThenHaliteOnElectronicScaleTask(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="mineral_fluorite_0"),
            partial(SkillLib.place, target_container_name="electronic_scale_0"),
            partial(SkillLib.pick, target_entity_name="mineral_fluorite_0"),
            partial(SkillLib.place, target_container_name="chemistry_lab_table_0"),
            partial(SkillLib.pick, target_entity_name="mineral_halite_0"),
            partial(SkillLib.place, target_container_name="electronic_scale_0"),
        ]
        return skill_sequence
