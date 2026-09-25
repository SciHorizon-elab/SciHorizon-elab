import random
import numpy as np
from functools import partial

from scihorizon_elab.benchmark.tasks.dm_task import *
from scihorizon_elab.benchmark.tasks.autogen_tasks.base import PrimitiveTask
from scihorizon_elab.benchmark.tasks.config_manager import BenchTaskConfigManager
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.configs.constant import name2class_xml

# 区域定义（单位：m）
# 杯子: x轴负半区, x∈[-0.15,-0.05], y∈[-0.05,0.10]  (10×10cm, x轴在负侧)
# 垫子: x轴正半区, x∈[0.05,0.15],  y∈[-0.05,0.10]  (10×10cm, x轴在正侧)
# 两区域中心在x轴间隔 10cm，边缘间隔 5cm
# 无随机 DR (randomness=None)

@register.add_config_manager("place_beaker_3")
class PlaceBeaker3ConfigManager(BenchTaskConfigManager):
    def __init__(self, task_name, num_objects=[1, 1], **kwargs):
        super().__init__(task_name, num_objects, **kwargs)
        self.config["task"]["n_distractor"] = 0

    def load_objects(self, target_entity):
        obj_config = dict(
            name="small_beaker_0",
            xml_path=name2class_xml["small_beaker"][-1],
            position=[random.uniform(-0.15, -0.05), random.uniform(-0.05, 0.10), 0.8],
        )
        obj_config["class"] = "ChemistryContainer"  # 实体注册名（旧名 ChemistryBeaker 已重命名）
        obj_config["randomness"] = None  # 无 DR
        self.config["task"]["components"].append(obj_config)

        obj_config = dict(
            name="square_mat_0",
            xml_path=name2class_xml["square_mat"][-1],
            position=[random.uniform(0.05, 0.15), random.uniform(-0.05, 0.10), 0.8],
        )
        obj_config["class"] = "FlatContainer"
        obj_config["randomness"] = None  # 无 DR
        self.config["task"]["components"].append(obj_config)

        self.target_entity = "small_beaker_0"

    def get_instruction(self, target_entity, **kwargs):
        self.config["task"]["instructions"] = ["Pick the <small_beaker_0> and place it on the <square_mat_0>."]

    def get_condition_config(self, target_entity, **kwargs):
        conditions_config = [
            dict(is_grasped=dict(entities=['small_beaker_0'], robot='robot')),
            dict(on=dict(entities=['small_beaker_0'], container='square_mat_0')),
        ]
        self.config["task"]["conditions"] = conditions_config


@register.add_task("place_beaker_3")
class PlaceBeaker3Task(PrimitiveTask):
    def __init__(self, task_name, robot, **kwargs):
        super().__init__(task_name, robot=robot, **kwargs)

    def get_expert_skill_sequence(self, physics):
        skill_sequence = [
            partial(SkillLib.pick, target_entity_name="small_beaker_0"),
            partial(SkillLib.place, target_container_name="square_mat_0"),
        ]
        return skill_sequence
