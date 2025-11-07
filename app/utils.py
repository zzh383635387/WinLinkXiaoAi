# app/utils.py
import threading
import datetime
import json
from pathlib import Path

_lock = threading.Lock()

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    print(f"[{now()}] {msg}")

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
