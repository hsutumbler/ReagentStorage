# ui/login_window.py — 登入畫面（現代化重設計）

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QLinearGradient, QColor, QPainter, QPainterPath
from services.auth_service import AuthService
from config import APP_NAME, APP_VERSION, DEFAULT_FONT


class LoginWindow(QDialog):
    login_success = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(440, 560)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None
        self._build_ui()
        self._apply_style()

    # ── UI ─────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)   # 留邊當陰影空間

        card = QFrame()
        card.setObjectName("login_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(44, 44, 44, 44)
        layout.setSpacing(0)

        # ── 頂部品牌區 ──
        icon_label = QLabel("🧪")
        icon_label.setObjectName("brand_icon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(APP_NAME)
        title.setObjectName("brand_title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("醫院檢驗科 · 試劑庫存管理")
        subtitle.setObjectName("brand_subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_label)
        layout.addSpacing(10)
        layout.addWidget(title)
        layout.addSpacing(4)
        layout.addWidget(subtitle)
        layout.addSpacing(36)

        # ── 工號輸入 ──
        lbl_id = QLabel("工號")
        lbl_id.setObjectName("input_label")
        self.input_id = _StyledInput("請輸入工號", False)
        layout.addWidget(lbl_id)
        layout.addSpacing(6)
        layout.addWidget(self.input_id)
        layout.addSpacing(18)

        # ── 密碼輸入 ──
        lbl_pw = QLabel("密碼")
        lbl_pw.setObjectName("input_label")
        self.input_pw = _StyledInput("請輸入密碼", True)
        layout.addWidget(lbl_pw)
        layout.addSpacing(6)
        layout.addWidget(self.input_pw)
        layout.addSpacing(28)

        # ── 登入按鈕 ──
        self.btn_login = QPushButton("登 入")
        self.btn_login.setObjectName("btn_login")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setFixedHeight(46)
        layout.addWidget(self.btn_login)
        layout.addSpacing(14)

        # ── 狀態訊息 ──
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("status_label")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setFixedHeight(20)
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # ── 版本 ──
        ver = QLabel(f"v{APP_VERSION}")
        ver.setObjectName("version_label")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        outer.addWidget(card)

        # 連線
        self.btn_login.clicked.connect(self._do_login)
        self.input_pw.returnPressed.connect(self._do_login)
        self.input_id.returnPressed.connect(lambda: self.input_pw.setFocus())

    def _apply_style(self):
        self.setStyleSheet(f"""
            QDialog {{ background: #F8F9FA; }}

            #login_card {{
                background: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #DEE2E6;
            }}

            #brand_icon {{
                font-size: 36px;
                color: #0066CC;
            }}

            #brand_title {{
                color: #2D3436;
                font-size: 20px;
                font-weight: 700;
                font-family: {DEFAULT_FONT};
                letter-spacing: 2px;
            }}

            #brand_subtitle {{
                color: #636E72;
                font-size: 12px;
                font-family: {DEFAULT_FONT};
                letter-spacing: 1px;
            }}

            #input_label {{
                color: #2D3436;
                font-size: 14px;
                font-weight: 700;
                font-family: {DEFAULT_FONT};
            }}

            #btn_login {{
                background: #0066CC;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
                font-family: {DEFAULT_FONT};
                letter-spacing: 6px;
            }}
            #btn_login:hover {{
                background: #0055AA;
            }}
            #btn_login:disabled {{
                background: #B2BEC3;
            }}

            #status_label {{
                color: #DC3545;
                font-size: 12px;
                font-family: {DEFAULT_FONT};
            }}

            #version_label {{
                color: #B2BEC3;
                font-size: 11px;
            }}
        """)

    # ── 登入邏輯 ───────────────────────────────────────────
    def _do_login(self):
        emp_id = self.input_id.text().strip()
        password = self.input_pw.text()

        if not emp_id or not password:
            self._show_status("請輸入工號與密碼")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("驗 證 中 …")

        try:
            user = AuthService.login(emp_id, password)
        except Exception as e:
            self._show_status(f"連線錯誤：{e}")
            self._reset_btn()
            return

        if user is None:
            self._show_status("工號或密碼錯誤")
            self.input_pw.clear()
            self._reset_btn()
            return

        self.login_success.emit(user)
        self.accept()

    def _show_status(self, msg: str):
        self.lbl_status.setText(msg)

    def _reset_btn(self):
        self.btn_login.setEnabled(True)
        self.btn_login.setText("登 入")

    # ── 可拖曳 ─────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class _StyledInput(QLineEdit):
    """自訂外框輸入框，focus 時藍色邊框。"""
    def __init__(self, placeholder: str, is_password: bool):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(46)
        if is_password:
            self.setEchoMode(QLineEdit.EchoMode.Password)
        self.setStyleSheet("""
            QLineEdit {
                background: #F8F9FA;
                border: 1.5px solid #DEE2E6;
                border-radius: 8px;
                color: #2D3436;
                font-size: 14px;
                padding: 0 16px;
                font-family: {DEFAULT_FONT};
            }
            QLineEdit:focus {
                border-color: #0066CC;
                background: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #B2BEC3;
            }
        """)
