# app/config.py
import json
import os
import sys
from pathlib import Path

# 获取配置文件的路径（支持打包后运行）
def get_config_path():
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包时，配置文件在exe同目录
        return Path(sys.executable).parent / "config.json"
    else:
        # 开发时，配置文件在项目根目录
        return Path(__file__).parent.parent / "config.json"

ROOT = Path(__file__).parent.parent
CFG_PATH = get_config_path()

# 默认配置（会被 config.json 覆盖）
DEFAULT = {
    "mqtt_broker": "bemfa.com",
    "mqtt_port": 9501,
    "mqtt_uid": "",
    "mqtt_keepalive": 60,
    "listen_topics": [],

    "http_host": "127.0.0.1",
    "http_port": 5000,

    "launcher_items": {},
    "enable_server": True,
    "auto_start": False
}

def load_cfg():
    """加载配置文件"""
    config = DEFAULT.copy()
    if CFG_PATH.exists():
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                config.update(data)
                # 兼容旧版本：如果有launcher_config_path，尝试加载
                if "launcher_config_path" in data and "launcher_items" not in data:
                    launcher_path = Path(data["launcher_config_path"])
                    if not launcher_path.is_absolute():
                        launcher_path = ROOT / launcher_path
                    if launcher_path.exists():
                        try:
                            with open(launcher_path, "r", encoding="utf-8") as lf:
                                config["launcher_items"] = json.load(lf)
                        except Exception:
                            pass
        except Exception:
            pass
    return config

def save_cfg(config):
    """保存配置文件"""
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

cfg = load_cfg()
