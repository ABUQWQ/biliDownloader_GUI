from etc import *
from PySide6.QtWidgets import QApplication
from BiliModule.Main import MainWindow


######################################################################
# 程序入口
app = QApplication(sys.argv)
MainWindow = MainWindow()
MainWindow.show()
sys.exit(app.exec())