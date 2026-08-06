"""
Loads config.json (falls back to config.sample.json if config.json is not
present, so the app runs out of the box in SIMULATE mode).
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config() -> dict:
    cfg_path = os.path.join(BASE_DIR, "config.json")
    sample_path = os.path.join(BASE_DIR, "config.sample.json")

    path = cfg_path if os.path.exists(cfg_path) else sample_path
    with open(path, "r") as f:
        return json.load(f)


CONFIG = load_config()
