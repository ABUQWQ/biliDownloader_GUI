# 互动视频界面可复用的纯函数与浅色对话框样式。
# 本模块不在导入时依赖 PySide6，便于离线测试直接引用。

LIGHT_DIALOG_STYLE = """
QMessageBox, QMessageBox QLabel, QMessageBox QPushButton{
    color: rgb(0, 0, 0);
    background-color: rgb(255, 255, 255);
}
QMessageBox QPushButton{
    background-color: rgb(255, 153, 153);
    color: rgb(255, 255, 255);
    border-radius: 8px;
    padding: 4px 12px;
}
"""


def count_chosen_nodes(tree: dict) -> int:
    """递归统计树中 isChoose 为真的节点数量。"""
    if not tree:
        return 0
    count = 0
    for node in tree.values():
        if not isinstance(node, dict):
            continue
        if node.get("isChoose"):
            count += 1
        choices = node.get("choices")
        if isinstance(choices, dict):
            count += count_chosen_nodes(choices)
    return count


def show_light_message(parent, title, text, icon="information", buttons=None):
    """弹出强制浅色的 QMessageBox，避免系统暗色下看不清。"""
    from PySide6.QtWidgets import QMessageBox

    icon_map = {
        "information": QMessageBox.Icon.Information,
        "warning": QMessageBox.Icon.Warning,
        "critical": QMessageBox.Icon.Critical,
        "question": QMessageBox.Icon.Question,
    }
    box = QMessageBox(parent)
    box.setIcon(icon_map.get(icon, QMessageBox.Icon.Information))
    box.setWindowTitle(title)
    box.setText(text)
    box.setStyleSheet(LIGHT_DIALOG_STYLE)
    if buttons is None:
        buttons = QMessageBox.StandardButton.Ok
    box.setStandardButtons(buttons)
    return box.exec()
