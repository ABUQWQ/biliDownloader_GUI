from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Signal, Qt, QPoint
from UI.biliRecurInfo import Ui_Form
from BiliWorker.extra import biliWorker_interact
from BiliModule.interact_utils import show_light_message


##############################################################################
# 递归探查线程反馈主界面
class RecurThreadWindow(QWidget, Ui_Form):
    _RSignal = Signal(dict)

    def __init__(self, mode: int, module: biliWorker_interact, st_node: str, deep: int = -1, parent=None):
        super(RecurThreadWindow, self).__init__(parent)
        self.setupUi(self)
        self.Move = False
        # 初始化信息
        self.mode = mode
        self.rtmodule = module
        self.start_node = st_node
        self.search_deep = deep
        self.feedback = {}
        self.bs_info_count = 0
        # 清除 Qt Designer 遗留的示例占位文本，避免追加日志时在开头残留一行无关内容
        self.plainTextEdit.setPlainText("")
        # 设置父窗口阻塞与窗口透明
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # 设置鼠标动作位置
        self.m_Position = QPoint(0, 0)
        # 添加阴影
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(30)
        effect.setOffset(0, 0)
        effect.setColor(Qt.gray)
        self.setGraphicsEffect(effect)
        # 连接器
        self.btnmin.clicked.connect(lambda: self.showMinimized())
        self.pushButton.clicked.connect(self.stop_thread)
        # 开始运行
        self.run_thread()

    # ###################### RW Part ##########################
    # 鼠标点击事件产生
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.Move = True
            if self.graphicsEffect():
                self.graphicsEffect().setEnabled(False)
            self.m_Position = event.globalPosition().toPoint() - self.pos()
            event.accept()

    # 鼠标移动事件
    def mouseMoveEvent(self, QMouseEvent):
        if Qt.LeftButton and self.Move:
            self.move(QMouseEvent.globalPosition().toPoint() - self.m_Position)
            QMouseEvent.accept()

    # 鼠标释放事件
    def mouseReleaseEvent(self, QMouseEvent):
        if self.graphicsEffect():
            self.graphicsEffect().setEnabled(True)
        self.Move = False

    # 定义关闭事件
    def closeEvent(self, QCloseEvent):
        self._RSignal.emit(self.feedback)

    # ###################### BS Part ##########################
    # 开始运行线程
    def run_thread(self):
        self.rtmodule.change_method(2, cur_node_id=self.start_node, deep=self.search_deep)
        self.rtmodule.business_info.connect(self.RTSlot_bsinfo)
        self.rtmodule.rthread_status.connect(self.RTSlot_status)
        self.rtmodule.start()

    # 停止递归
    def stop_thread(self):
        self.rtmodule.kill_rthread()

    # ###################### 槽函数 ############################
    # 接收递归线程反馈字符
    # 采用追加方式，保留已探查过的历史路径，避免每条新消息覆盖之前内容；
    # 超过一定行数后清空重置，避免长时间递归时日志无限增长占用内存。
    def RTSlot_bsinfo(self, instr):
        if self.bs_info_count >= 2233:
            self.plainTextEdit.setPlainText("")
            self.bs_info_count = 0
        self.plainTextEdit.appendPlainText(instr)
        self.bs_info_count += 1

    # 接收线程反馈字典
    def RTSlot_status(self, indic):
        if indic['code'] == 0:
            self.label_5.setText(indic['node_id'])
            self.label_6.setText(str(indic['deep']))
            self.label_4.setText(indic['node_name'])
        elif indic['code'] == 1:
            self._stop_progress()
            self.feedback['status'] = self.mode
            self.feedback['data'] = indic['node_dict']
            self.close()
        else:
            self._stop_progress()
            show_light_message(self, '探查反馈', indic['data'])
            self.close()

    # 停止进度条忙碌动画，探查结束后满进度展示
    def _stop_progress(self):
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(100)
