import os
import json
from scihorizon_elab.utils.register import register
from scihorizon_elab.simulation.envs.dm_env import LM4ManipDMEnv
from scihorizon_elab.utils.utils import find_key_by_value

# load global robot config here, corresponding to different embodiments
with open(os.path.join(os.getenv("SCIHORIZON_ELAB_ROOT"), "simulation/configs/robot_config.json"), "r") as f:
    ROBOT_CONFIG= json.load(f)

def load_env(task, 
             robot="franka", 
             config=None, 
             time_limit=float('inf'), 
             reset_wait_step=10, 
             episode_config=None, 
             random_init=False,
             **kwargs):
    """
    load environment with given config
    params:
        task: str, name of the environment/task
        robot: str, name of the robot
        config: dict, additional configuration for the environment, including robot, task, etc.
        time_limit: int, maximum time steps for the environment
        reset_wait_step: int, number of steps to wait after reset, using for initialize the scene with no collision
        episode_config: dict, deterministic config for a specific episode, used for evaluation or trajetcory replay.
        random_init: bool, if true, the env will take random layout/texture in each reset. Set this value 'False' when eval or replay.
    """
    # load config
    # 动态获取 name2config 和 TASK_CONFIG（避免模块级导入的缓存问题）
    from scihorizon_elab.benchmark.configs import name2config
    with open(os.path.join(os.getenv("SCIHORIZON_ELAB_ROOT"), "benchmark/configs/task_config.json"), "r") as f:
        TASK_CONFIG = json.load(f)

    # 动态注册任务兼容：如果 task 已注册但 name2config/TASK_CONFIG 中找不到，
    # 则用 task_series = task（即 task_name_series 作为 series name）
    task_series = find_key_by_value(name2config, task)
    if task_series == task and task in register._tasks:
        # task 已在 register 中注册（registration_node 已处理），尝试从动态更新的 TASK_CONFIG 读取
        task_series = f"{task}_series"
    specific_config = TASK_CONFIG.get(task_series, {})
    default_config = TASK_CONFIG["default"]
    default_config.update(specific_config)
    if config is not None and isinstance(config, dict):
        default_config.update(config)
    # load and update robot config first and then load robot entity
    robot_config = ROBOT_CONFIG.get(robot, None)
    assert robot_config is not None, f"robot {robot} is not supported"
    robot_config_overide = default_config.get("robot", {})
    robot_config.update(robot_config_overide)
    robot = register.load_robot(robot)(**robot_config)
    if default_config.get('task') and default_config['task'].get("random_init", None) is not None:
        random_init = default_config['task']['random_init']
    if episode_config is not None:
        # forbid random initialization if given episode config
        random_init = False 
    task = register.load_task(task)(task, robot, episode_config=episode_config, random_init=random_init, **kwargs)
    env = LM4ManipDMEnv(task=task, time_limit=time_limit, reset_wait_step=reset_wait_step)
    env.reset()
    return env