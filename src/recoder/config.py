import json
from pathlib import Path
from gi.repository import GLib

CONFIG_PATH = Path(GLib.get_user_config_dir()) / "recoder" / "config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}
