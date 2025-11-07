# app/mqtt_listener.py
import json
import time
import traceback
from .config import cfg
from .utils import run_in_thread, log, atomic_read_json
try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

def _on_message(client, userdata, msg):
    payload = msg.payload.decode(errors="ignore").strip()
    topic = msg.topic
    log(f"[MQTT] 收到消息: topic={topic} payload={payload}")
    # 读取当前启动项配置并匹配 topic
    try:
        items = atomic_read_json(cfg["launcher_config_path"])
        for name, info in items.items():
            if not isinstance(info, dict):
                continue
            if info.get("bafy_topic") == topic:
                item_type = info.get("type", "").strip().lower()
                # 支持三种触发：关机专门处理 / brightness带数值 / 普通on触发
                try:
                    if name == "关机" and payload.lower() == "off":
                        # 执行关机
                        run_cmd = info.get("cmd", "")
                        run_in_thread(lambda: __run_cmds_sync(run_cmd))
                        log(f"[MQTT] 触发关机: {name}")
                    elif item_type in ["brightness", "value", "number"]:
                        # payload 可能是 "on#50" 或 "50"
                        value = None
                        if payload.startswith("on#"):
                            try:
                                value = int(payload.split("#", 1)[1])
                            except Exception:
                                pass
                        elif payload.isdigit():
                            value = int(payload)
                        if value is not None:
                            from .controller import set_brightness
                            set_brightness(info.get("cmd", ""), value)
                            log(f"[MQTT] 设置数值项 {name}={value}")
                    elif payload.lower() == "on":
                        # 普通触发运行
                        from .routes import trigger_run_item_by_name
                        trigger_run_item_by_name(name)
                        log(f"[MQTT] 触发操作: {name}")
                except Exception as ex:
                    log(f"[MQTT] 执行启动项出错: {ex}")
                    traceback.print_exc()
                break
    except Exception as e:
        log(f"[MQTT] 处理消息出错: {e}")

def __run_cmds_sync(cmd_text):
    from .controller import run_exe_commands
    f = run_exe_commands(cmd_text)
    f()

def start_mqtt_listener(cfg_local):
    # cfg_local 是 app.config.py 中读取的 cfg
    if mqtt is None:
        log("[MQTT] paho-mqtt 未安装，MQTT 功能不可用")
        return

    def _run():
        client = None
        last_cfg = {}
        while True:
            try:
                # 读取配置
                cfg_now = atomic_read_json(cfg_local["launcher_config_path"])
                mqtt_uid_now = cfg_local.get("mqtt_uid", "")

                # 检查是否配置有变化
                if cfg_now != last_cfg or (client and client._client_id.decode() != mqtt_uid_now):
                    if client:
                        try:
                            client.disconnect()
                            log("[MQTT] 配置变化，断开原连接")
                        except Exception:
                            pass
                    # 创建新客户端
                    client_id = mqtt_uid_now if mqtt_uid_now else None
                    client = mqtt.Client(client_id=client_id, clean_session=True)
                    client.on_message = _on_message
                    broker = cfg_local.get("mqtt_broker")
                    port = int(cfg_local.get("mqtt_port", 9501))
                    keepalive = int(cfg_local.get("mqtt_keepalive", 60))
                    client.connect(broker, port, keepalive)
                    log(f"[MQTT] 重新连接到 {broker}:{port} UID: {mqtt_uid_now[:6]}")
                    # 订阅 topics
                    topics = {info.get("bafy_topic") for n, info in cfg_now.items() if
                              isinstance(info, dict) and info.get("bafy_topic")}
                    for t in topics:
                        client.subscribe(t)
                        log(f"[MQTT] 已订阅 {t}")
                    client.loop_start()
                    last_cfg = cfg_now
                time.sleep(5)  # 每 5 秒检查一次
            except Exception as e:
                log(f"[MQTT] 监听线程异常: {e}")
                time.sleep(5)

    run_in_thread(_run)
