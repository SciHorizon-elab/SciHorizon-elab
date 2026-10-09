import numpy as np
from scihorizon_elab.utils.utils import quaternion_to_euler, quaternion_to_rotvec

class Policy:
    def __init__(self, model):
        self.model = model
        
    def reset(self):
        pass
    
    def predict(self, obs):
        """
        Predict the action given the observation
        """
        pass
    
    def process_observation(self, obs, **kwargs):
        """
        Align the observation to the policy input
        """
        pass
    
    def process_output(self, output):
        """
        Align the output to the action
        """
        pass
    
    @property
    def name(self):
        return "Policy"
    
    @property
    def control_mode(self):
        """
        prediction mode of the policy, e.g. "ee" or "joint"
        """
        return "ee"

class RandomPolicy(Policy):
    def predict(self, obs, **kwargs):
        delta_pos = np.random.uniform(-0.1, 0.1, 3)
        delta_rotvec = np.random.uniform(-0.1, 0.1, 3)
        gripper_open = np.random.uniform(0, 1, 1)
        current_ee_state = obs["ee_state"]
        if len(current_ee_state) == 8:
            pos, quat = current_ee_state[:3], current_ee_state[3:]
            rotvec = quaternion_to_rotvec(quat)
        elif len(current_ee_state) == 7:
            pos, rotvec = current_ee_state[:3], current_ee_state[3:6]
        target_pos = np.array(pos) + delta_pos
        target_rotvec = rotvec + delta_rotvec
        gripper_state = np.ones(2)*0.04 if gripper_open >= 0.1 else np.zeros(2)
        return target_pos, target_rotvec, gripper_state
    
    @property
    def name(self):
        return "RandomPolicy"

