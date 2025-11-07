# app/controller.py
import os
import subprocess
import webbrowser
import urllib.parse
from .utils import log

def run_exe_commands(cmd_text):
    """
    cmd_text: 多行命令，每行独立执行
    """
    cmds = [ln.strip() for ln in cmd_text.splitlines() if ln.strip()]
    def _run():
        for idx, cmd in enumerate(cmds):
            try:
                # 使用 shell=True 以保留原命令习惯（Windows 常用）
                subprocess.Popen(cmd, shell=True)
                log(f"执行命令: {cmd}")
            except Exception as e:
                log(f"执行命令失败: {cmd} => {e}")
    # 异步执行由调用方决定：在 routes 中直接调用 run_in_thread
    return _run

def run_music(item):
    """
    对于 music 类型：
     - 如果 cmd 是 URI（以 scheme:// 开头），直接用 webbrowser.open
     - 否则尝试解析为 JSON，并根据 uri_scheme 组合启动参数（尽量兼容原逻辑）
    """
    try:
        cmd_data = item.get("cmd", "")
        scheme = item.get("uri_scheme", "")
        if isinstance(cmd_data, str) and (cmd_data.startswith("http://") or cmd_data.startswith("https://") or "://" in cmd_data):
            webbrowser.open(cmd_data)
            log(f"音乐打开（URI）: {cmd_data}")
            return True, "音乐已尝试打开（URI）"
        # 其它情况：构造一个 scheme?json 的方式并通过浏览器打开（与原逻辑兼容）
        import json
        try:
            music_json = json.loads(cmd_data)
        except Exception:
            try:
                music_json = eval(cmd_data) if cmd_data else {}
            except Exception:
                music_json = {}
        json_str = json.dumps(music_json, ensure_ascii=False)
        encoded = urllib.parse.quote(json_str, safe='')
        final = f"{scheme}?{encoded}" if scheme else json_str
        webbrowser.open(final)
        log(f"音乐打开（组合URI）: {final}")
        return True, "音乐已尝试打开（组合URI）"
    except Exception as e:
        log(f"音乐启动失败: {e}")
        return False, f"音乐启动失败: {e}"

def set_brightness(cmd_template, value):
    try:
        cmd = cmd_template.replace("XXX", str(value))
        subprocess.Popen(cmd, shell=True)
        log(f"设置亮度: {value}")
        return True, "亮度命令已发送"
    except Exception as e:
        log(f"设置亮度失败: {e}")
        return False, f"亮度命令失败: {e}"
