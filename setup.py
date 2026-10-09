from pathlib import Path
from setuptools import find_packages, setup


long_description = (Path(__file__).parent / "README.md").read_text()

core_requirements = [
    "gym",
    "ipdb",
    "mujoco",
    "dm_control",
    "imageio",
]

setup(
    name="scihorizon-elab",
    version="0.1",
    author="SciHorizon Team",
    url="",
    description="SciHorizon-ELAB: A benchmark for language-conditioned robotics manipulation with LLM-powered task synthesis pipeline",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">3.8",
    install_requires=core_requirements,
)
