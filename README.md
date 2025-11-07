# SmartLink 重构版（Windows）

## 简介
基于你原始 `SmartLink.py` 重构。保留：Web 界面、MQTT 触发、启动项管理、运行命令、音乐 URI 打开、亮度设置等。删除：ADB/安卓、读卡器功能。前后端同源，前端使用纯 HTML+JS。

## 目录


TODO LIST
1.托盘
2.优化config的各种问题，路径，多余字段，config.json打包后有bug，不能修改
3.打包问题 
pyinstaller -F --add-data "templates;templates" --add-data "config.json;." --add-data "launcher_config.json;." run.py 
4.优化性能  减少冗余代码；前后端在大多时间可以不开启，只监听巴法。