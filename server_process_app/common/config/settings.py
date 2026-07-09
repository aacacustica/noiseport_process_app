from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[3]

load_dotenv(ROOT_DIR / ".env")


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_settings() -> dict:
    server = _read_yaml(ROOT_DIR / "config" / "server.yaml")
    devices = _read_yaml(ROOT_DIR / "config" / "devices.yaml")

    return {
        "root": ROOT_DIR,
        "paths": server.get("paths", {}),
        "processing": server.get("processing", {}),
        "pipeline": server.get("pipeline", {}),
        "models": server.get("models", {}),
        "visualization": server.get("visualization", {}),
        "peaks": server.get("peaks", {}),
        "alarms": server.get("alarms",{}),
        "queries": server.get("queries", {}),

        "mqtt": {
            "host": os.getenv("MQTT_HOST"),
            "port": int(os.getenv("MQTT_PORT", "1883")),
            "user": os.getenv("MQTT_USER"),
            "password": os.getenv("MQTT_PASSWORD"),
            "enabled": os.getenv("MQTT_ENABLED", "false").lower() == "true",
        },
        
        "mysql": {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
            "local_infile": os.getenv("MYSQL_LOCAL_INFILE", "0") == "1",
            "local_infile": os.getenv("MYSQL_LOCAL_INFILE", "0") == "1"
        },
        "devices": devices.get("devices", []),
    }


config = load_settings()


def enabled_devices() -> list[dict]:
    return [d for d in config["devices"] if d.get("enabled", True)]


def device_ids() -> list[str]:
    return [d["id"] for d in enabled_devices()]


def device_by_id(device_id: str) -> dict:
    for d in config["devices"]:
        if d["id"] == device_id:
            return d
    raise KeyError(f"Device not found in devices.yaml: {device_id}")