# BiliDownloader: BiliBili Media Downloader

> 基于Python开发的可视化B站视频专用下载器（支持交互视频下载）
> 
> Visualized Media Downloader for BiliBili Based on Python

[![maven](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/)  [![mavel](https://img.shields.io/badge/GPL-3.0-red.svg)](https://github.com/JimmyLiang-lzm/biliDownloader/blob/master/LICENSE) ![mavel](https://img.shields.io/badge/requests-2.27.1-green.svg) ![mavel](https://img.shields.io/badge/PySide6-6.11.2-green.svg) [![mavel](https://img.shields.io/badge/BiliDownloader-Command-pink.svg)](https://github.com/JimmyLiang-lzm/biliDownloader)

查看软件教程请访问（Use tutorial address）：[https://zmtblog.xdkd.ltd/2021/10/07/bilid_GUI_help/](https://zmtblog.xdkd.ltd/2021/10/07/bilid_GUI_help/)


## ✨特性 Feature

* 漂亮的界面，友好的人机交互体验
* Beautiful screen, friendly interactive experience
* 下载兼容性好，若主下载线路阻塞，软件将自动选择备用线路进行下载
* Well download compatibility, automatically select the alternate line when the main line is blocked
* 可自动合并音画分离的视频流（支持杜比视界视频合成）
* Merge the stream of video and audio, automatically.(Dolby Vision Video is supported)
* 可获取并下载不同清晰度的音视频流，从360P到8K全部支持下载（包含杜比视界）
* Can obtain and download audio and video streams of different definitions.(Include 360P to Dolby Vision)
* 已接入新版 WBI API，可使用账号 Cookie 获取账号有权访问的番剧与高质量视频
* Uses the current WBI API and the configured account Cookie for authorized resources
* 可进行分P视频批量下载
* Downloadable segmented video batches
* 可下载任意交互视频！（2022-04-07更新）
* Downloadable interactive video (Updated 2022-04-07)
* 解除区域访问限制，可利用代理IP或科学上网工具下载非内陆视频资源（2021-10-30更新）
* You can use IP proxy or SSR to remove regional resource access restrictions (Updated 2021-10-30)

## 🖥系统要求 System Requirements

* Windows操作系统：Windows 10 或以上
* Windows: Windows 10 or above
* Linux操作系统：Ubuntu 20.04 桌面版 或以上
* Linux: Ubuntu 20.04 Desktop or above
* Mac OS：Mac OS X 10.15 Catalina 或以上
* Mac OS: Mac OS X 10.15 Catalina or above

## 🎨软件界面 GUI

![mainGUI](https://zmtblog.xdkd.ltd/2021/10/07/bilid_GUI_help/mainGUI.jpg)

## API 与测试

* 迁移与修复说明见 `MIGRATION.md`
* 离线测试命令：`python -m unittest discover -s "tests" -v`
* 当前 GUI 已迁移至 PySide6

## 🚀发版 Release

版本号以 git tag（如 `V1.8.2`）为唯一来源，无需手动修改代码中的版本号：

* 推送 `V*` 标签或在 Actions 手动触发 `Build and Release`，CI 会先运行 `make/sync_version.py` 自动同步版本号与构建日期（取构建当天），再构建并发布 Windows/Linux/macOS 三平台安装包
* 本地打包 Windows 安装器（`win32setup.nsi`）前，先运行一次 `python make/sync_version.py V<x.y.z>` 同步版本号
* 若为补丁版本，记得在 `MIGRATION.md` 补充对应版本的发版说明（同步脚本会自动检查并提醒）

## ⚖声明 Declaration

* 本项目受GPL-3.0许可协议保护，所有程序仅用于学习与交流，请勿用于任何商业用途！
* This project is protected by the GPL-3.0 license agreement, all programs are only used for learning and communication, please do not use it for any commercial purposes!

## 🤝致谢 Gratitude

* 💖💖如果您觉得此程序有用，请不吝留下一个**Star**或者**fork**呗，感激不尽！💖💖
* 💖💖If you find this program useful, please don’t hesitate to leave a **Star** or **fork**, thank you very much!💖💖
* `Lib/bili_api` 源自 Majjcom/BiliDownloader，按 MIT License 使用，许可证见 `Lib/bili_api/LICENSE`
