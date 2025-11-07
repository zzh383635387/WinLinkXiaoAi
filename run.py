# run.py
from app import create_app
from app.config import cfg
from app.routes import bp_state
import os
from pathlib import Path
from app.utils import atomic_write_json, atomic_read_json, log

app = create_app()

# 将 launcher_config_path 注入 routes 模块状态
launcher_path = cfg.get("launcher_config_path") or str(Path.cwd() / "launcher_config.json")
bp_state["launcher_config_path"] = launcher_path

# 如果没有 launcher 配置文件则写入示例默认（以免前端报错）
if not Path(launcher_path).exists():
    sample = atomic_read_json(Path(__file__).parent / "launcher_config.json")  # try sample in repo
    if not sample:
        sample = {
            "关机": {
                "type": "exe",
                "cmd": "shutdown -s -t 60",
                "uri_scheme": "",
                "card_id": "",
                "bafy_topic": "off001"
            }
        }
    atomic_write_json(launcher_path, sample)
    log(f"已生成启动项文件: {launcher_path}")

if __name__ == "__main__":
    host = cfg.get("http_host", "127.0.0.1")
    port = int(cfg.get("http_port", 5000))
    log(f"启动 SmartLink Web: http://{host}:{port}")
    app.run(host=host, port=port, threaded=True)
