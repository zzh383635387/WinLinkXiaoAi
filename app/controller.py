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
        import sys
        import threading
        
        for idx, cmd in enumerate(cmds):
            try:
                # 使用 shell=True 以保留原命令习惯（Windows 常用）
                if sys.platform == 'win32':
                    # Windows下使用GBK编码捕获输出
                    process = subprocess.Popen(
                        cmd, 
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        encoding='gbk',
                        errors='replace'
                    )
                    
                    # 异步读取输出和错误（不阻塞）
                    def read_output():
                        import time
                        # 等待进程完成（最多等待5秒）
                        max_wait = 5  # 最多等待5秒
                        check_interval = 0.1  # 每0.1秒检查一次
                        max_checks = int(max_wait / check_interval)
                        
                        for _ in range(max_checks):
                            if process.poll() is not None:
                                # 进程已完成，读取输出和错误
                                try:
                                    stdout, stderr = process.communicate()
                                    if stdout:
                                        output_msg = stdout.strip()
                                        if output_msg:
                                            log(f"命令输出: {output_msg}")
                                    if stderr:
                                        error_msg = stderr.strip()
                                        if error_msg:
                                            log(f"命令错误: {error_msg}")
                                except Exception as e:
                                    log(f"读取命令输出时出错: {e}")
                                break
                            time.sleep(check_interval)
                        else:
                            # 5秒后进程还在运行，让它后台运行
                            # 不等待，命令继续后台执行
                            pass
                    
                    # 在后台线程中读取输出
                    output_thread = threading.Thread(target=read_output, daemon=True)
                    output_thread.start()
                    
                    log(f"执行命令: {cmd}")
                else:
                    # 非Windows系统使用默认编码
                    subprocess.Popen(cmd, shell=True)
                    log(f"执行命令: {cmd}")
            except Exception as e:
                # 确保异常信息正确编码
                error_msg = str(e)
                try:
                    if sys.platform == 'win32':
                        # Windows下尝试GBK解码
                        if isinstance(error_msg, bytes):
                            error_msg = error_msg.decode('gbk', errors='replace')
                except:
                    pass
                log(f"执行命令失败: {cmd} => {error_msg}")
    # 异步执行由调用方决定：在 routes 中直接调用 run_in_thread
    return _run

