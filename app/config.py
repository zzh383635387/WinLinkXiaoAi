# app/config.py
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
CFG_PATH = ROOT / "config.json"

# 默认配置（会被 config.json 覆盖）
DEFAULT = {
    "mqtt_broker": "bemfa.com",
    "mqtt_port": 9501,
    "mqtt_uid": "",
    "mqtt_keepalive": 60,
    "listen_topics": [],

    "http_host": "127.0.0.1",
    "http_port": 5000,

    "launcher_config_path": str(ROOT / "launcher_config.json")
}

def load_cfg():
    if CFG_PATH.exists():
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                DEFAULT.update(data)
        except Exception:
            pass
    return DEFAULT

cfg = load_cfg()
