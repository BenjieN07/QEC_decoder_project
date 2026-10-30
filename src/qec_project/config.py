"""Strict experiment settings; JSON keeps the initial interface dependency-free."""
import json
import math
from pathlib import Path

NOISE = (
    "after_clifford_depolarization", "before_round_data_depolarization",
    "before_measure_flip_probability", "after_reset_flip_probability",
)


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"code_type", "basis", "distance", "rounds", "noise", "shots",
                "seed", "output_dir", "decoder"}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError("config must contain exactly: " + ", ".join(sorted(required)))
    if config["code_type"] != "rotated_surface_code":
        raise ValueError("code_type must be rotated_surface_code")
    if config["basis"] not in ("X", "Z"):
        raise ValueError("basis must be X or Z")
    for key in ("distance", "rounds", "shots", "seed"):
        value = config[key]
        if type(value) is not int or value < (0 if key == "seed" else 1):
            raise ValueError(f"{key} must be an integer in its valid range")
    if config["distance"] < 3 or config["distance"] % 2 != 1:
        raise ValueError("distance must be odd and at least 3")
    if config["seed"] >= 2**64:
        raise ValueError("seed must be below 2**64")
    if config["decoder"] != "pymatching":
        raise ValueError("decoder must be pymatching (planned M1 reference)")
    noise = config["noise"]
    if not isinstance(noise, dict) or set(noise) != set(NOISE):
        raise ValueError("noise must specify all four circuit noise channels")
    for value in noise.values():
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("noise probabilities must be finite numbers in [0, 1]")
    if not isinstance(config["output_dir"], str) or not config["output_dir"].strip():
        raise ValueError("output_dir must be a nonempty path")
    return config
