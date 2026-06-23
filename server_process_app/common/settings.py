from pathlib import Path
import yaml
import os
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(ROOT_DIR / ".env")

def load_settings():

    with open(ROOT_DIR / "config/server.yaml") as f:
        server_cfg = yaml.safe_load(f)

    with open(ROOT_DIR / "config/devices.yaml") as f:
        devices_cfg = yaml.safe_load(f)

    return {
        "root": ROOT_DIR,

        "paths": server_cfg["paths"],

        "pipeline": server_cfg["pipeline"],

        "processing": server_cfg["processing"],

        "mysql": {
            "host": os.getenv("MYSQL_HOST"),
            "port": os.getenv("MYSQL_PORT"),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
        },

        "mqtt": {
            "host": os.getenv("MQTT_HOST"),
            "port": os.getenv("MQTT_PORT"),
            "user": os.getenv("MQTT_USER"),
            "password": os.getenv("MQTT_PASSWORD"),
        },

        "devices": devices_cfg["devices"],
    }

settings = load_settings()