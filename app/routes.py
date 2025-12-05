# app/routes.py
import json
import urllib.parse
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .utils import atomic_read_json, atomic_write_json, run_in_thread, log, build_command
from .controller import run_exe_commands
import os
bp = Blueprint("main", __name__, template_folder="../templates")

# 辅助：在 MQTT 或其它地方触发运行同一函数
def trigger_run_item_by_name(name):
    from .config import cfg
    launcher_items = cfg.get("launcher_items", {})
    info = launcher_items.get(name)
    if not info:
        log(f"触发失败，未找到启动项：{name}")
        return False, "未找到启动项"
    return _run_item_by_info(name, info)

# 将 blueprint 需要的一些共享状态注入（在 create_app 后设置）
bp_state = {}

def _run_item_by_info(name, info, payload_param=None):
    """
    执行启动项
    payload_param: 从 MQTT payload 中解析出的参数（如 "on#100" 中的 "100"）
    """
    # 获取命令和参数
    cmd = info.get("cmd", "").strip()
    para = info.get("para", "").strip()
    
    # 如果 payload 中有参数，优先使用 payload 参数
    if payload_param:
        para = payload_param
    
    # 构建最终命令
    full_cmd = build_command(cmd, para)
    
    if not full_cmd:
        return False, "命令为空"
    
    runner = run_exe_commands(full_cmd)
    run_in_thread(runner)
    return True, "已执行命令"

@bp.route("/", methods=["GET"])
def index():
    # 读取 launcher 配置（重新加载以确保获取最新值）
    from .config import load_cfg, save_cfg
    cfg = load_cfg()  # 重新加载配置，不使用缓存的全局变量
    
    launcher_items = cfg.get("launcher_items", {})
    if not launcher_items:
        launcher_items = {}
        cfg["launcher_items"] = launcher_items
        save_cfg(cfg)

    # 提取启动项 items（排除下划线开头字段）
    items = [(n, info) for n, info in launcher_items.items() if not n.startswith("_")]

    # categories
    categories = sorted({info.get("type", "exe") for n, info in items})

    # 读取 config.json 里的 mqtt_uid（从最新加载的配置中读取）
    mqtt_uid = cfg.get("mqtt_uid", "") or ""

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
    from .config import load_cfg, save_cfg
    cfg = load_cfg()
    launcher_items = cfg.get("launcher_items", {})
    old_name = request.form.get("old_name", "").strip()
    name = request.form.get("name", "").strip()
    info = {
        "cmd": request.form.get("cmd", ""),
        "para": request.form.get("para", ""),
        "bafy_topic": request.form.get("bafy_topic", "")
    }
    if old_name and old_name != name and old_name in launcher_items:
        launcher_items.pop(old_name, None)
    if not name:
        flash("名称不能为空")
        return redirect(url_for("main.index"))
    launcher_items[name] = info
    cfg["launcher_items"] = launcher_items
    save_cfg(cfg)
    flash(f"已保存启动项 {name}")
    return redirect(url_for("main.index"))

@bp.route("/delete_item/<name>", methods=["POST"])
def delete_item(name):
    from .config import load_cfg, save_cfg
    cfg = load_cfg()
    launcher_items = cfg.get("launcher_items", {})
    if name in launcher_items:
        launcher_items.pop(name)
        cfg["launcher_items"] = launcher_items
        save_cfg(cfg)
        flash(f"已删除启动项 {name}")
    return redirect(url_for("main.index"))

@bp.route("/run_item/<name>", methods=["POST"])
def run_item_api(name):
    from .config import load_cfg, save_cfg
    cfg = load_cfg()
    launcher_items = cfg.get("launcher_items", {})
    info = launcher_items.get(name)
    if not info:
        flash("未找到启动项")
        return redirect(url_for("main.index"))
    ok, msg = _run_item_by_info(name, info)
    flash(msg)
    return redirect(url_for("main.index"))

@bp.route("/save_mqtt_uid", methods=["POST"])
def save_mqtt_uid():
    try:
        # 获取参数，允许空字符串（用于清空配置）
        uid = request.form.get("mqtt_uid", "").strip()

        from .config import load_cfg,save_cfg
        cfg = load_cfg()
        
        # 保存 mqtt_uid（允许为空字符串）
        cfg["mqtt_uid"] = uid
        if save_cfg(cfg):
            flash(f"MQTT UID 已保存: {uid if uid else '已清空'}")
            return redirect(url_for("main.index"))
        else:
            flash("保存失败", "error")
            return redirect(url_for("main.index"))
    except Exception as e:
        flash(f"保存失败: {e}", "error")
        return redirect(url_for("main.index"))



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
