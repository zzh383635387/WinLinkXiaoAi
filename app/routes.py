# app/routes.py
import json
import urllib.parse
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .utils import atomic_read_json, atomic_write_json, run_in_thread, log
from .controller import run_exe_commands, run_music, set_brightness
import os
bp = Blueprint("main", __name__, template_folder="../templates")

# 辅助：在 MQTT 或其它地方触发运行同一函数
def trigger_run_item_by_name(name):
    cfg = atomic_read_json(bp_state["launcher_config_path"])
    info = cfg.get(name)
    if not info:
        log(f"触发失败，未找到启动项：{name}")
        return False, "未找到启动项"
    return _run_item_by_info(name, info)

# 将 blueprint 需要的一些共享状态注入（在 create_app 后设置）
bp_state = {
    "launcher_config_path": None
}

def _run_item_by_info(name, info, brightness_value=None):
    item_type = info.get("type", "").strip().lower()
    if item_type == "exe":
        runner = run_exe_commands(info.get("cmd", ""))
        run_in_thread(runner)
        return True, "已执行EXE命令"
    elif item_type == "music":
        ok, msg = run_music(info)
        return ok, msg
    elif item_type == "brightness":
        value = brightness_value if brightness_value is not None else 50
        return set_brightness(info.get("cmd", ""), value)
    else:
        return False, "未知类型"

@bp.route("/", methods=["GET"])
def index():
    # 读取 launcher 配置
    cfg = atomic_read_json(bp_state["launcher_config_path"])
    if not cfg:
        atomic_write_json(bp_state["launcher_config_path"], {})
        cfg = {}

    # 提取启动项 items（排除下划线开头字段）
    items = [(n, info) for n, info in cfg.items() if not n.startswith("_")]

    # categories
    categories = sorted({info.get("type", "exe") for n, info in items})

    # 读取 config.json 里的 mqtt_uid
    mqtt_uid = ""
    with open("../config.json", "r", encoding="utf-8") as f:
        cfg_json = json.load(f)
        mqtt_uid = cfg_json.get("mqtt_uid", "")

    # 构造 item_json_map
    item_json_map = {n: json.dumps(i, ensure_ascii=False) for n, i in items}

    return render_template(
        "index.html",
        items=items,
        all_items=items,
        settings={"mqtt_uid": mqtt_uid},  # 这里传给模板
        categories=categories,
        query_type=request.args.get("type", ""),
        keyword=request.args.get("kw", "").strip(),
        item_json_map=item_json_map
    )

@bp.route("/save_item", methods=["POST"])
def save_item():
    cfg = atomic_read_json(bp_state["launcher_config_path"])
    old_name = request.form.get("old_name", "").strip()
    name = request.form.get("name", "").strip()
    info = {
        "type": request.form.get("type", "exe"),
        "cmd": request.form.get("cmd", ""),
        "uri_scheme": request.form.get("uri_scheme", ""),
        "card_id": request.form.get("card_id", ""),
        "bafy_topic": request.form.get("bafy_topic", "")
    }
    if old_name and old_name != name and old_name in cfg:
        cfg.pop(old_name, None)
    if not name:
        flash("名称不能为空")
        return redirect(url_for("main.index"))
    cfg[name] = info
    atomic_write_json(bp_state["launcher_config_path"], cfg)
    if request.form.get("run_after_save", "") == "1":
        _run_item_by_info(name, info)
    flash(f"已保存启动项 {name}")
    return redirect(url_for("main.index"))

@bp.route("/delete_item/<name>", methods=["POST"])
def delete_item(name):
    cfg = atomic_read_json(bp_state["launcher_config_path"])
    if name in cfg:
        cfg.pop(name)
        atomic_write_json(bp_state["launcher_config_path"], cfg)
        flash(f"已删除启动项 {name}")
    return redirect(url_for("main.index"))

@bp.route("/run_item/<name>", methods=["POST"])
def run_item_api(name):
    value = request.form.get("brightness_value", None)
    if value is not None and value.isdigit():
        value = int(value)
    else:
        value = None
    cfg = atomic_read_json(bp_state["launcher_config_path"])
    info = cfg.get(name)
    if not info:
        flash("未找到启动项")
        return redirect(url_for("main.index"))
    ok, msg = _run_item_by_info(name, info, brightness_value=value)
    flash(msg)
    return redirect(url_for("main.index"))

@bp.route("/save_mqtt_uid", methods=["POST"])
def save_mqtt_uid():
    uid = request.form.get("mqtt_uid", None)
    if not uid:
        return jsonify({"status": "error", "msg": "缺少参数 mqtt_uid"}), 400
    try:
        CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config.json")
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            cfg["mqtt_uid"] = uid
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return redirect(url_for("main.index"))
    except Exception as e:
        return jsonify({"status": "error", "msg": f"保存失败: {e}"}), 500



@bp.route("/save_settings", methods=["POST"])
def save_settings():
    # 本版将全局设置放在 config.json，Web 仅用于更新 launcher_config
    flash("已保存设置（请手动编辑 config.json 以更改 MQTT/HTTP 等全局设置）")
    return redirect(url_for("main.index"))

@bp.route("/parse_music", methods=["POST"])
def parse_music():
    text = request.form.get("music_link", "").strip()
    import re, urllib.parse, json
    match = re.search(r'\?(.*)$', text)
    if not match:
        result = "未找到 ? 后的内容"
    else:
        encoded = match.group(1).strip()
        try:
            decoded = urllib.parse.unquote(encoded)
            decoded = decoded.replace('\\', '')
            try:
                obj = json.loads(decoded)
            except Exception:
                obj = eval(decoded)
            result = json.dumps(obj, ensure_ascii=False, indent=4)
        except Exception as e:
            result = f"解析失败: {e}"
    flash(result)
    return redirect(url_for("main.index"))

@bp.route("/adb_action/<action>", methods=["POST"])
def adb_action(action):
    # 保留接口兼容前端，但安卓逻辑已被删除
    return jsonify({"msg": "本程序已移除 ADB/安卓 支持，仅支持 Windows 操作"})
