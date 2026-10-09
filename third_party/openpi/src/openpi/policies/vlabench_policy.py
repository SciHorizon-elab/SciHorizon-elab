import dataclasses

import einops
import numpy as np

from openpi import transforms
from openpi.models import model as _model

from scipy.spatial.transform import Rotation as R

def quat2_6d(quat):
    # H5/LeRobot quat 是 wxyz;scipy R.from_quat 要 xyzw,这里重排
    r = R.from_quat([quat[1], quat[2], quat[3], quat[0]])
    R_mat = r.as_matrix()
    # column-major: [R[:, 0], R[:, 1]] = [R[0,0], R[1,0], R[2,0], R[0,1], R[1,1], R[2,1]]
    import numpy as np
    return np.concatenate([R_mat[:, 0], R_mat[:, 1]])


def make_libero_example() -> dict:
    """Creates a random input example for the Libero policy."""
    return {
        "observation/state": np.random.rand(8),
        "observation/image": np.random.randint(256, size=(224, 224, 3), dtype=np.uint8),
        "observation/wrist_image": np.random.randint(256, size=(224, 224, 3), dtype=np.uint8),
        "prompt": "do something",
    }


def _parse_image(image) -> np.ndarray:
    image = np.asarray(image)
    if np.issubdtype(image.dtype, np.floating):
        image = (255 * image).astype(np.uint8)
    if image.shape[0] == 3:
        image = einops.rearrange(image, "c h w -> h w c")
    return image


@dataclasses.dataclass(frozen=True)
class VLABenchInputs(transforms.DataTransformFn):
    # The action dimension of the model. Will be used to pad state and actions for pi0 model (not pi0-FAST).
    action_dim: int

    # Determines which model will be used.
    model_type: _model.ModelType = _model.ModelType.PI0

    def __call__(self, data: dict) -> dict:
        mask_padding = self.model_type == _model.ModelType.PI0  # We don't mask for pi0-FAST.

        # Get the state. We are padding from 8 to the model action dim.
        # For pi0-FAST, we don't pad the state (action_dim = 7, which is < 8, so pad is skipped).
        # After RepackTransform, keys are dest names without "observation." prefix.
        ee_state = data["state"]
        state = transforms.pad_to_dim(ee_state, self.action_dim)

        # Possibly need to parse images to uint8 (H,W,C) since LeRobot automatically
        # stores as float32 (C,H,W), gets skipped for policy inference
        base_image = _parse_image(data["image"])
        second_image = _parse_image(data["second_image"])
        wrist_image = _parse_image(data["wrist_image"])

        inputs = {
            "state": state,
            "image": {
                "base_0_rgb": base_image,
                "left_wrist_0_rgb": second_image,
                "right_wrist_0_rgb": wrist_image,
            },
            "image_mask": {
                "base_0_rgb": np.True_,
                "left_wrist_0_rgb": np.True_,
                "right_wrist_0_rgb": np.True_,
            },
        }

        # Actions are only available during training.
        if "actions" in data:
            # We are padding from 7 to the model action dim.
            # For pi0-FAST, this is a no-op (since action_dim = 7).
            actions = transforms.pad_to_dim(data["actions"], self.action_dim)
            inputs["actions"] = actions

        if "prompt" in data:
            inputs["prompt"] = data["prompt"]

        return inputs


@dataclasses.dataclass(frozen=True)
class VLABenchOutputs(transforms.DataTransformFn):
    def __call__(self, data: dict) -> dict:
        # 6D rotation 改造后: actions shape = pos3 + 6d6 + gripper1 = 10 维
        # 旧 rotvec 时代: 7 维。这里按 10 维发回,policy 端会切 [3:9] 取 6D。
        return {"actions": np.asarray(data["actions"][:, :10])}
