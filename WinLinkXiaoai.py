# run.py
from app import create_app
from app.config import cfg, save_cfg, load_cfg
import os
import sys
import threading
import time
from pathlib import Path
from app.utils import log

# 初始化配置，确保launcher_items存在
if "launcher_items" not in cfg or not cfg.get("launcher_items"):
    cfg["launcher_items"] = {
        "关机": {
            "type": "exe",
            "cmd": "shutdown -s -t 60",
            "uri_scheme": "",
            "card_id": "",
            "bafy_topic": "off001"
        }
    }
    save_cfg(cfg)
    log("已初始化启动项配置")

# 全局变量
app = None
server_thread = None
server_running = False
server_instance = None

def start_server():
    """启动Flask服务器"""
    global app, server_running, server_instance
    try:
        if app is None:
            app = create_app()
        if not server_running:
            from werkzeug.serving import make_server
            host = cfg.get("http_host", "127.0.0.1")
            port = int(cfg.get("http_port", 5000))
            log(f"启动 WinLinkXiaoai Web: http://{host}:{port}")
            server_running = True
            # 使用werkzeug的WSGIServer，支持shutdown
            server_instance = make_server(host, port, app, threaded=True)
            try:
                server_instance.serve_forever()
            except Exception as e:
                # 服务器被关闭时的异常是正常的
                if "shutdown" in str(e).lower() or "closed" in str(e).lower():
                    log("服务器已正常关闭")
                else:
                    log(f"服务器运行错误: {e}")
            finally:
                server_running = False
                server_instance = None
    except Exception as e:
        log(f"服务器启动错误: {e}")
        server_running = False
        server_instance = None

def stop_server():
    """停止Flask服务器"""
    global server_running, server_instance, server_thread
    if server_running and server_instance:
        try:
            log("正在关闭服务器...")
            # 使用werkzeug的shutdown方法
            server_instance.shutdown()
            
            # 等待服务器线程结束（最多等待5秒）
            if server_thread and server_thread.is_alive():
                server_thread.join(timeout=5)
                if server_thread.is_alive():
                    log("警告：服务器线程未在5秒内结束，强制标记为已停止")
            
            server_running = False
            server_instance = None
            server_thread = None
            log("服务器已停止")
        except Exception as e:
            log(f"停止服务器时出错: {e}")
            # 即使出错也标记为已停止
            server_running = False
            server_instance = None
            server_thread = None

def check_and_control_server():
    """检查配置并动态控制服务器"""
    global server_thread, server_running
    last_state = None
    while True:
        try:
            current_cfg = load_cfg()
            enable_server = current_cfg.get("enable_server", True)
            
            if last_state != enable_server:
                if enable_server and not server_running:
                    # 启动服务器
                    server_thread = threading.Thread(target=start_server, daemon=True)
                    server_thread.start()
                    # 等待一下确保服务器启动
                    time.sleep(0.5)
                    log("Web服务器已启动")
                elif not enable_server and server_running:
                    # 停止服务器
                    stop_server()
                    # 等待一下确保服务器完全停止
                    time.sleep(1)
                    log("Web服务器已停止")
                last_state = enable_server
            
            time.sleep(2)  # 每2秒检查一次配置
        except Exception as e:
            log(f"检查服务器状态时出错: {e}")
            time.sleep(2)

if __name__ == "__main__":
    # 启动MQTT监听（在create_app中会自动启动）
    # 先创建app以启动MQTT监听
    app = create_app()
    
    # 检查是否启用服务器
    if cfg.get("enable_server", True):
        # 启动服务器线程（daemon，后台运行）
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
    else:
        log("Web服务器已禁用")
    
    # 启动配置监控线程（动态控制服务器）
    config_monitor_thread = threading.Thread(target=check_and_control_server, daemon=True)
    config_monitor_thread.start()
    
    # 导入托盘模块（如果可用）
    try:
        from app.tray import create_tray
        tray_thread = create_tray()
        # 等待托盘线程（托盘线程是非daemon，会保持程序运行）
        if tray_thread:
            tray_thread.join()
    except ImportError:
        log("托盘功能不可用，请安装pystray和Pillow")
        # 如果没有托盘，保持程序运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log("程序已退出")
    except Exception as e:
        log(f"启动托盘时出错: {e}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log("程序已退出")
