# 迁移与修复说明 (Migration Notes)

本文档说明本 fork 相对于原始 `biliDownloader_GUI` 项目所做的关键迁移与修复，帮助使用者和后续开发者理解当前版本与三年前原始版本的差异。

## 为什么需要迁移

- 原项目依赖 `PySide2 5.15.2`，该版本没有针对 Python 3.11+ 的官方 wheel，导致在现代 Python 环境下**完全无法安装、无法启动**。
- 原项目调用的 B 站接口部分已随官方 API 变更（例如 WBI 签名机制）而失效，播放地址、番剧信息等请求会直接报错。

## 迁移到了什么

- GUI 框架从 `PySide2` 全面迁移到 `PySide6 6.11.2`：全部 `.ui` 文件用 `pyside6-uic`/`pyside6-rcc` 重新编译，业务代码同步更新到 PySide6 的新枚举写法（如 `Qt.LeftButton` -> `Qt.MouseButton.LeftButton` 等由生成器自动处理）与新 API（如 `globalPosition().toPoint()` 取代已废弃的 `globalPos()`）。
- 引入了适配新版 B 站 API 的 `Lib/bili_api` 模块（源自 Majjcom/BiliDownloader，MIT 协议，许可证见 `Lib/bili_api/LICENSE`），并新增 `BiliWorker/api_adapter.py` 作为新旧接口之间的适配层，让旧版 GUI 代码无需大改就能对接新 API。

## 修复的问题

- **B 站接口恢复可用**：视频信息、播放地址、番剧信息等请求改走新版 API 适配层，解决了原项目因 WBI 签名等接口变更导致的功能失效问题。
- **下载进度条精度**：修正了 `.ui` 编译产物与业务代码中进度条满值不一致的问题（原先满值 1000 但业务代码按更精细的刻度计算，导致进度条最多只能显示到十分之一）。
- **互动视频节点递归探查**：
  - 原实现使用 Python 原生递归遍历节点，深度较大或存在环形节点结构时会触发 `RecursionError` 导致后台线程静默崩溃、界面卡死无响应；现已改为显式栈迭代实现深度优先遍历，从根源消除该风险。
  - 新增已访问节点去重机制，遇到互动视频中的环形节点结构时会标记并跳过，不再无限重复展开。
  - 递归探查窗口的日志由“每条新消息覆盖之前内容”改为“累计追加”，可以看到完整的探查路径历史；新增一个忙碌状态的进度条，让用户能感知到探查仍在进行中。
- **窗口拖动重绘警告**：修正了全部自定义窗口在拖动时因阴影特效与透明背景组合导致的 `UpdateLayeredWindowIndirect` 控制台警告（拖动瞬间临时禁用阴影特效，松开后恢复）。
- **字体警告**：修正了 `.ui` 文件中字体磅值配置为无效值导致的 `QFont::setPointSize` 控制台警告。

## 如何安装运行

```powershell
pip install -r requirements.txt
python biliDownloader_GUI.py
```

## 如何运行离线测试

项目自带一套不依赖真实网络请求、不需要账号 Cookie 的离线单元测试：

```powershell
python -m unittest discover -s tests -v
```

## V1.8.1 补丁修复

- **FFMPEG 音画合成失败**：发布包现已内置对应平台的 FFmpeg 静态编译可执行文件（Windows/Linux/macOS 三平台的发布包都自带），不需要用户另外安装 FFmpeg 或手动加入 PATH，默认勾选的“FFMPEG合成”功能现在可以正常工作。
- **下拉框暗色模式配色**：修复了主界面视频/音频质量选择下拉框在系统暗色主题下弹出列表难以辨认的问题，下拉列表弹窗现在固定为白底黑字，不受系统主题影响。

## 已知限制

- 全部自定义窗口均使用绝对坐标布局，未使用 Qt 布局管理器；标题栏的“最大化”按钮未接入任何逻辑，点击无效果。这是历史遗留限制，需重构为布局管理器后才能实现，暂未在本次迁移中处理。
- `UI/bilidLive.py` 与 `UI/bilidLive.ui`（直播下载窗口）未被任何模块引用，主界面也没有入口能打开该窗口，是一个从未完工、未接入主流程的孤立功能模块。
- 大文件、多线程分片下载等下载速度优化暂未纳入本次改动范围。

## 许可与致谢

- 本项目遵循原仓库的 GPL-3.0 许可协议，仅供学习交流，请勿用于商业用途。
- `Lib/bili_api` 源自 [Majjcom/BiliDownloader](https://github.com/Majjcom/BiliDownloader)，按 MIT License 使用。
