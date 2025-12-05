# app/tray.py
import sys
import os
import threading
import webbrowser
from pathlib import Path
from .config import cfg, save_cfg, load_cfg
from .utils import log

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# 全局变量
tray_icon = None
tray_thread = None

def get_icon_path():
    """获取图标文件路径（支持打包后运行）"""
    # if getattr(sys, 'frozen', False):
    #     # PyInstaller 打包时，图标文件在exe同目录
    #     icon_dir = Path(sys.executable).parent
    # else:
    #     # 开发时，图标文件在项目根目录
    icon_dir = Path(__file__).parent.parent
    
    # 尝试多个可能的图标文件名
    icon_names = ['winlink.ico', 'app.ico', 'tray.ico']
    for icon_name in icon_names:
        icon_path = icon_dir / icon_name
        if icon_path.exists():
            return icon_path
    return None

def create_icon():
    """创建托盘图标"""
    # 优先尝试加载ico文件
    icon_path = get_icon_path()
    if icon_path and icon_path.exists():
        try:
            # 尝试加载ico文件
            image = Image.open(icon_path)
            # 转换为RGBA模式（如果需要）
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            # 调整大小到合适的尺寸（系统托盘通常需要16x16或32x32）
            if image.size[0] > 64 or image.size[1] > 64:
                # 兼容不同版本的PIL
                try:
                    image = image.resize((64, 64), Image.Resampling.LANCZOS)
                except AttributeError:
                    image = image.resize((64, 64), Image.LANCZOS)
            log(f"已加载图标文件: {icon_path}")
            return image
        except Exception as e:
            log(f"加载图标文件失败: {e}，使用默认三角形图标")
    
    # 如果ico文件不存在或加载失败，绘制一个简单的三角形
    image = Image.new('RGBA', (64, 64), color=(255, 255, 255, 0))  # 透明背景
    draw = ImageDraw.Draw(image)
    
    # 绘制一个三角形（向上箭头）
    triangle_points = [
        (32, 12),   # 顶点
        (20, 48),   # 左下角
        (44, 48)    # 右下角
    ]
    draw.polygon(triangle_points, fill='#1e90ff', outline='#0d6efd', width=2)
    
    return image

def open_settings():
    """打开设置页面（前端）"""
    host = cfg.get("http_host", "127.0.0.1")
    port = int(cfg.get("http_port", 5000))
    url = f"http://{host}:{port}"
    webbrowser.open(url)
    log(f"打开设置页面: {url}")

def toggle_server():
    """切换Web服务器开关（动态控制）"""
    global cfg
    cfg = load_cfg()  # 重新加载配置
    current = cfg.get("enable_server", True)
    cfg["enable_server"] = not current
    save_cfg(cfg)
    log(f"Web服务器已{'开启' if not current else '关闭'}")
    return not current

def toggle_auto_start():
    """切换开机自启动"""
    global cfg
    cfg = load_cfg()  # 重新加载配置
    current = cfg.get("auto_start", False)
    new_value = not current
    cfg["auto_start"] = new_value
    save_cfg(cfg)
    
    # 设置Windows开机自启动
    try:
        # 获取当前程序路径
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            # 如果是开发模式，使用python运行WinLinkXiaoai.py
            run_py = Path(__file__).parent.parent / "WinLinkXiaoai.py"
            python_exe = sys.executable
            exe_path = f'"{python_exe}" "{run_py}"'
        
        # 注册表路径
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "WinLinkXiaoai"
        
        if new_value:
            # 添加开机自启动
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
                log(f"已设置开机自启动: {exe_path}")
            except Exception as e:
                log(f"设置开机自启动失败: {e}")
        else:
            # 删除开机自启动
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                try:
                    winreg.DeleteValue(key, app_name)
                    log("已取消开机自启动")
                except FileNotFoundError:
                    log("开机自启动项不存在")
                winreg.CloseKey(key)
            except Exception as e:
                log(f"取消开机自启动失败: {e}")
    except ImportError:
        log("需要安装pywin32才能设置开机自启动")
    except Exception as e:
        log(f"设置开机自启动时出错: {e}")
    
    return new_value


def exit_app():
    """退出程序"""
    global tray_icon
    log("正在退出程序...")
    if tray_icon:
        tray_icon.stop()
    # 使用os._exit确保完全退出
    import os
    os._exit(0)

def get_menu():
    """获取动态菜单"""
    cfg_current = load_cfg()
    server_enabled = cfg_current.get("enable_server", True)
    auto_start_enabled = cfg_current.get("auto_start", False)
    
    def on_server_toggle(icon, item):
        toggle_server()
        icon.menu = get_menu()
    
    def on_auto_start_toggle(icon, item):
        toggle_auto_start()
        icon.menu = get_menu()
    
    return pystray.Menu(
        pystray.MenuItem("设置", open_settings, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            lambda text: f"Web服务器: {'开启' if server_enabled else '关闭'}",
            on_server_toggle
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            lambda text: f"开机自启动: {'开启' if auto_start_enabled else '关闭'}",
            on_auto_start_toggle
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", lambda icon, item: exit_app())
    )

def create_tray():
    """创建系统托盘，返回托盘线程"""
    global tray_icon, tray_thread
    
    if not TRAY_AVAILABLE:
        log("托盘功能不可用，请安装pystray和Pillow")
        return None
    
    # 创建图标
    image = create_icon()
    
    # 创建菜单
    menu = get_menu()
    
    # 创建托盘图标
    tray_icon = pystray.Icon("WinLinkXiaoai", image, "WinLinkXiaoai", menu)
    
    # 在单独线程中运行托盘（非daemon，保持程序运行）
    def run_tray():
        tray_icon.run()
    
    tray_thread = threading.Thread(target=run_tray, daemon=False)
    tray_thread.start()
    log("系统托盘已启动")
    return tray_thread

