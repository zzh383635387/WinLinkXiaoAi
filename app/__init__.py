# app/__init__.py
from flask import Flask
from .routes import bp as main_bp
from .config import cfg
from .mqtt_listener import start_mqtt_listener
import os
import sys

def create_app():
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包时
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    app = Flask(__name__,template_folder=os.path.join(base_path, "templates"),)
    app.secret_key = "SmartLinkSecretKey"
    app.config['JSON_AS_ASCII'] = False

    app.register_blueprint(main_bp)
    # 启动 MQTT 监听（后台线程）
    start_mqtt_listener(cfg)
    return app
