# WinLinkXiaoai 重构版

## 简介
基于你原始 `WinLinkXiaoai.py` 重构。保留：Web 界面、MQTT 触发、启动项管理、运行命令、音乐 URI 打开、亮度设置等。删除：ADB/安卓、读卡器功能。前后端同源，前端使用纯 HTML+JS。

## 目录


## 功能特性

- ✅ 系统托盘：运行后显示托盘，包括设置、开/关前后端、开机自启动设置
- ✅ 前后端控制：可以独立控制前后端的开关
- ✅ 统一配置：config.json和launcher_config.json已合并，优化了路径问题
- ✅ 开机自启动：支持Windows开机自启动设置

## 打包命令

```bash
pyinstaller -F --add-data "templates;templates" --add-data "config.json;." --add-data "winink.ico;." WinLinkXiaoai.py
```

注意：
- launcher_config.json已合并到config.json中，不再需要单独打包
- 图标文件：如果项目根目录有 `winink.ico`、`app.ico` 或 `tray.ico`，打包时需要包含（使用 `--add-data "winink.ico;."`）
- 如果没有ico文件，系统托盘会显示默认的三角形图标