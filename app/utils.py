# app/utils.py
import threading
import datetime
import json
import sys
import os
from pathlib import Path

_lock = threading.Lock()
_log_file = None
_log_file_path = None

def get_log_path():
    """获取日志文件路径"""
    global _log_file_path
    if _log_file_path:
        return _log_file_path
    
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包时，日志文件在exe同目录
        log_dir = Path(sys.executable).parent
    else:
        # 开发时，日志文件在项目根目录
        log_dir = Path(__file__).parent.parent
    
    # 按日期创建日志文件
    # today = datetime.datetime.now().strftime("%Y-%m-%d")
    _log_file_path = log_dir / f"WinLinkXiaoai.log"
    return _log_file_path

def log(msg):
    """记录日志到控制台和文件"""
    global _log_file
    timestamp = now()
    log_msg = f"[{timestamp}] {msg}"
    
    # 输出到控制台
    print(log_msg)
    
    # 输出到文件
    try:
        log_path = get_log_path()
        with _lock:
            # 使用追加模式，UTF-8编码
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_msg + "\n")
                f.flush()  # 立即刷新到文件
    except Exception as e:
        # 如果写入文件失败，只输出到控制台
        print(f"[{timestamp}] 日志写入失败: {e}")

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def run_in_thread(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t

def atomic_read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with _lock:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return {}

def atomic_write_json(path, data):
    path = Path(path)
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def build_command(cmd, para):
    """
    构建命令：如果 cmd 中包含 'XXX'，则用 para 替换；否则将 para 作为参数追加
    """
    cmd = cmd.strip() if cmd else ""
    para = para.strip() if para else ""
    
    if not cmd:
        return ""
    
    # 如果 cmd 中包含 'XXX'，则替换为 para
    if 'XXX' in cmd:
        if para:
            full_cmd = cmd.replace('XXX', para)
        else:
            # 如果没有 para，保留 XXX
            full_cmd = cmd
    else:
        # 如果 cmd 中不包含 'XXX'，则将 para 作为参数追加
        if para:
            full_cmd = f"{cmd} {para}"
        else:
            full_cmd = cmd
    
    return full_cmd
