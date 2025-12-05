# app/mqtt_listener.py
import json
import time
import traceback
from .config import load_cfg
from .utils import run_in_thread, log, atomic_read_json, build_command
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
        cfg = load_cfg()
        items = cfg.get("launcher_items", {})
        for name, info in items.items():
            if not isinstance(info, dict):
                continue
            if info.get("bafy_topic") == topic:
                # 解析 payload 参数
                try:
                    payload_lower = payload.lower()
                    payload_param = None
                    # 解析 payload
                    if '#' in payload:
                        parts = payload.split('#', 1)
                        if len(parts) == 2:
                            action = parts[0].strip().lower()
                            payload_param = parts[1].strip()
                            if action in ["on", "off"]:
                                # 使用 payload 中的参数
                                pass
                            else:
                                # 如果第一部分不是 on/off，整个作为参数
                                payload_param = payload
                    elif payload_lower in ["on", "off"]:
                        # 纯 on/off，使用配置中的 para
                        payload_param = None
                    
                    # 构建命令
                    cmd = info.get("cmd", "").strip()
                    para = info.get("para", "").strip()
                    
                    # 如果 payload 中有参数，优先使用 payload 参数
                    if payload_param:
                        para = payload_param

                    if name == '电脑音量':
                        para = str(655 * int(para))
                        print(para)
                    # 构建最终命令
                    full_cmd = build_command(cmd, para)
                    
                    # 执行命令
                    run_in_thread(lambda: __run_cmds_sync(full_cmd))
                    log(f"[MQTT] 触发操作: {name}, payload: {payload}, 命令: {full_cmd}")
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
                # 重新加载配置以支持动态变化
                from .config import load_cfg
                cfg_current = load_cfg()
                
                # MQTT监听永远保持启动，不检查enable_backend
                # 读取配置
                cfg_now = cfg_current.get("launcher_items", {})
                mqtt_uid_now = cfg_current.get("mqtt_uid", "")

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
                    broker = cfg_current.get("mqtt_broker")
                    port = int(cfg_current.get("mqtt_port", 9501))
                    keepalive = int(cfg_current.get("mqtt_keepalive", 60))
                    client.connect(broker, port, keepalive)
                    log(f"[MQTT] 连接到 {broker}:{port} UID: {mqtt_uid_now[:6] if mqtt_uid_now else 'None'}")
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
