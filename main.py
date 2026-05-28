# main.py — 程式進入點

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from config import APP_NAME, DEFAULT_FONT
from database.connection import test_connection, DatabasePool
from services.logger import setup_global_logger


def _apply_light_palette(app: QApplication):
    """套用全域亮色 QPalette，確保所有底層元件與背景風格統一。"""
    palette = QPalette()
    c = {
        "window":       QColor("#F8F9FA"),
        "window_text":  QColor("#2D3436"),
        "base":         QColor("#FFFFFF"),
        "alt_base":     QColor("#FDFBF7"),
        "tooltip_base": QColor("#FFFFFF"),
        "tooltip_text": QColor("#2D3436"),
        "text":         QColor("#2D3436"),
        "button":       QColor("#F1F3F5"),
        "button_text":  QColor("#2D3436"),
        "bright_text":  QColor("#FFFFFF"),
        "link":         QColor("#0066CC"),
        "highlight":    QColor("#0066CC"),
        "highlight_text": QColor("#FFFFFF"),
        "dark":         QColor("#CED4DA"),
        "mid":          QColor("#DEE2E6"),
        "mid_light":    QColor("#E9ECEF"),
        "shadow":       QColor("#ADB5BD"),
        "light":        QColor("#F8F9FA"),
    }
    palette.setColor(QPalette.ColorRole.Window,          c["window"])
    palette.setColor(QPalette.ColorRole.WindowText,      c["window_text"])
    palette.setColor(QPalette.ColorRole.Base,            c["base"])
    palette.setColor(QPalette.ColorRole.AlternateBase,   c["alt_base"])
    palette.setColor(QPalette.ColorRole.ToolTipBase,     c["tooltip_base"])
    palette.setColor(QPalette.ColorRole.ToolTipText,     c["tooltip_text"])
    palette.setColor(QPalette.ColorRole.Text,            c["text"])
    palette.setColor(QPalette.ColorRole.Button,          c["button"])
    palette.setColor(QPalette.ColorRole.ButtonText,      c["button_text"])
    palette.setColor(QPalette.ColorRole.BrightText,      c["bright_text"])
    palette.setColor(QPalette.ColorRole.Link,            c["link"])
    palette.setColor(QPalette.ColorRole.Highlight,       c["highlight"])
    palette.setColor(QPalette.ColorRole.HighlightedText, c["highlight_text"])
    palette.setColor(QPalette.ColorRole.Dark,            c["dark"])
    palette.setColor(QPalette.ColorRole.Mid,             c["mid"])
    palette.setColor(QPalette.ColorRole.Midlight,        c["mid_light"])
    palette.setColor(QPalette.ColorRole.Shadow,          c["shadow"])
    palette.setColor(QPalette.ColorRole.Light,           c["light"])
    app.setPalette(palette)


def main():
    logger = setup_global_logger()
    logger.info("====== ReagentStorage Application Started ======")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    
    # 全域字型
    font = QFont(DEFAULT_FONT, 10)
    app.setFont(font)

    # 套用亮色 # 調色盤
    _apply_light_palette(app)

    # 測試資料庫連線
    test_connection()

    from ui.login_window import LoginWindow
    from ui.main_window import MainWindow

    login = LoginWindow()

    def on_login(user: dict):
        win = MainWindow(user)
        win.show()
        MainWindow._active_windows.append(win)

    login.login_success.connect(on_login)
    login.show()

    code = app.exec()
    DatabasePool.close_pool()
    sys.exit(code)


if __name__ == "__main__":
    main()
 