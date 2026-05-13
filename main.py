# main.py — 程式進入點

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont, QPalette, QColor
from PyQt6.QtCore import Qt
from config import APP_NAME, DEFAULT_FONT
from database.connection import test_connection, DatabasePool


def _apply_dark_palette(app: QApplication):
    """套用全域深色 QPalette，確保 Qt 內建元件（滾動條、對話框等）一致。"""
    palette = QPalette()
    c = {
        "window":       QColor("#0A0F1E"),
        "window_text":  QColor("#E2E8F0"),
        "base":         QColor("#0D1117"),
        "alt_base":     QColor("#0F1628"),
        "tooltip_base": QColor("#141E30"),
        "tooltip_text": QColor("#E2E8F0"),
        "text":         QColor("#E2E8F0"),
        "button":       QColor("#141E30"),
        "button_text":  QColor("#94A3B8"),
        "bright_text":  QColor("#FFFFFF"),
        "link":         QColor("#60A5FA"),
        "highlight":    QColor("#1D4ED8"),
        "highlight_text": QColor("#FFFFFF"),
        "dark":         QColor("#060C18"),
        "mid":          QColor("#0F1628"),
        "mid_light":    QColor("#141E30"),
        "shadow":       QColor("#04080F"),
        "light":        QColor("#1A2540"),
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
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    
    # 全域字型
    font = QFont(DEFAULT_FONT, 10)
    app.setFont(font)

    # 套用深色 Palette
    _apply_dark_palette(app)

    # 測試資料庫連線
    if not test_connection():
        err = QMessageBox()
        err.setWindowTitle("資料庫連線失敗")
        err.setText(
            "無法連線至 MySQL 資料庫伺服器，請確認：\n\n"
            "1. MySQL 伺服器是否已啟動\n"
            "2. config.py 中的 host / user / password 是否正確\n"
            "3. 區域網路連線是否正常"
        )
        err.setIcon(QMessageBox.Icon.Critical)
        err.exec()
        sys.exit(1)

    from ui.login_window import LoginWindow
    from ui.main_window import MainWindow

    login = LoginWindow()

    def on_login(user: dict):
        win = MainWindow(user)
        win.show()

    login.login_success.connect(on_login)
    login.show()

    code = app.exec()
    DatabasePool.close_pool()
    sys.exit(code)


if __name__ == "__main__":
    main()
 