# ui/base_page.py — 所有功能頁面的基礎樣式（現代化重設計）

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QComboBox, QDateEdit,
    QMessageBox, QSizePolicy, QStyledItemDelegate,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor
from config import APP_NAME, DEFAULT_FONT

# ── 自定義 Delegate 實作全域置中 ───────────────────────────
class CenterDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter

# ─────────────────────────────────────────────────────────
# 統一設計 Token
# ─────────────────────────────────────────────────────────

COLORS = {
    # 背景層次
    "bg_base":    "#0A0F1E",   # 最底層
    "bg_surface": "#0F1628",   # 卡片/面板
    "bg_elevated":"#141E30",   # 浮出卡片
    "bg_input":   "#0D1117",   # 輸入框

    # 邊框
    "border":     "#1A2540",
    "border_focus":"#3B82F6",

    # 文字
    "text_primary":  "#E2E8F0",
    "text_secondary":"#94A3B8",
    "text_muted":    "#475569",
    "text_disabled": "#2D3748",

    # 強調色
    "accent":        "#3B82F6",   # blue-500
    "accent_hover":  "#2563EB",   # blue-600
    "accent_light":  "#1E3A8A",   # blue-900（選取背景）

    # 功能色
    "success":   "#10B981",
    "warning":   "#F59E0B",
    "danger":    "#EF4444",
    "danger_bg": "#1C0A0A",
    "danger_border": "#7F1D1D",

    # 表格
    "table_bg":    "#0D1117",
    "table_alt":   "#0F1628",
    "table_head":  "#111827",
    "table_select":"#172554",
    "grid":        "#1A2540",
}

# ── 全域 QSS ──────────────────────────────────────────────
PAGE_STYLE = f"""
    /* ── 基底 ── */
    QWidget {{
        background: {COLORS['bg_base']};
        color: {COLORS['text_primary']};
        font-family: {DEFAULT_FONT};
        font-size: 13px;
    }}

    /* ── 頁面標題 ── */
    #page_title {{
        color: {COLORS['text_primary']};
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    #page_subtitle {{
        color: {COLORS['text_muted']};
        font-size: 12px;
        letter-spacing: 0.5px;
    }}
    #header_divider {{
        background: {COLORS['border']};
        max-height: 1px;
        border: none;
    }}

    /* ── 卡片 ── */
    #section_card {{
        background: {COLORS['bg_surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 20px;
    }}

    /* ── Label ── */
    QLabel {{
        color: {COLORS['text_secondary']};
        font-size: 13px;
        background: transparent;
    }}

    /* ── 輸入框 ── */
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit {{
        background: {COLORS['bg_input']};
        border: 1.5px solid {COLORS['border']};
        border-radius: 8px;
        color: {COLORS['text_primary']};
        font-size: 13px;
        padding: 8px 12px;
        min-height: 32px;
        selection-background-color: {COLORS['accent_light']};
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
        border-color: {COLORS['border_focus']};
        background: #0C1422;
    }}
    QLineEdit::placeholder, QTextEdit::placeholder {{
        color: {COLORS['text_disabled']};
    }}

    /* ── ComboBox ── */
    QComboBox::drop-down {{
        border: none;
        width: 28px;
        border-radius: 0 8px 8px 0;
    }}
    QComboBox::down-arrow {{
        width: 12px;
        height: 12px;
    }}
    QComboBox QAbstractItemView {{
        background: {COLORS['bg_elevated']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        color: {COLORS['text_primary']};
        selection-background-color: {COLORS['accent_light']};
        selection-color: {COLORS['accent']};
        outline: none;
    }}

    /* ── SpinBox ── */
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background: {COLORS['border']};
        border: none;
        width: 18px;
        border-radius: 3px;
    }}

    /* ── DateEdit ── */
    QDateEdit::drop-down {{
        border: none;
        width: 24px;
    }}
    QCalendarWidget {{
        background: {COLORS['bg_elevated']};
        color: {COLORS['text_primary']};
    }}

    /* ── 按鈕 ── */
    QPushButton {{
        background: {COLORS['bg_elevated']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 500;
        min-height: 34px;
    }}
    QPushButton:hover {{
        background: #1A2540;
        color: {COLORS['text_primary']};
        border-color: #2A3A56;
    }}
    QPushButton:pressed {{
        background: #111928;
    }}
    QPushButton:disabled {{
        color: {COLORS['text_disabled']};
        border-color: {COLORS['bg_elevated']};
        background: {COLORS['bg_surface']};
    }}

    /* ── 主要按鈕 ── */
    QPushButton#btn_primary {{
        background: {COLORS['accent']};
        color: #FFFFFF;
        border: none;
        font-weight: 600;
    }}
    QPushButton#btn_primary:hover {{
        background: {COLORS['accent_hover']};
    }}
    QPushButton#btn_primary:pressed {{
        background: #1D4ED8;
    }}

    /* ── 危險按鈕 ── */
    QPushButton#btn_danger {{
        background: {COLORS['danger_bg']};
        color: {COLORS['danger']};
        border: 1px solid {COLORS['danger_border']};
    }}
    QPushButton#btn_danger:hover {{
        background: #2A0A0A;
        color: #FCA5A5;
        border-color: #991B1B;
    }}

    /* ── 成功按鈕 ── */
    QPushButton#btn_success {{
        background: #0D2A1E;
        color: {COLORS['success']};
        border: 1px solid #134E2A;
    }}
    QPushButton#btn_success:hover {{
        background: #0F3524;
        color: #34D399;
    }}

    /* ── 表格 ── */
    QTableWidget {{
        background: {COLORS['table_bg']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        gridline-color: {COLORS['grid']};
        color: {COLORS['text_primary']};
        font-size: 13px;
        outline: none;
    }}
    QTableWidget::item {{
        padding: 10px 14px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background: {COLORS['table_select']};
        color: #93C5FD;
    }}
    QTableWidget::item:alternate {{
        background: {COLORS['table_alt']};
    }}

    QHeaderView::section {{
        background: {COLORS['table_head']};
        color: {COLORS['text_muted']};
        border: none;
        border-right: 1px solid {COLORS['grid']};
        border-bottom: 1px solid {COLORS['grid']};
        padding: 10px 14px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }}
    QHeaderView::section:last {{
        border-right: none;
    }}

    /* ── 垂直捲軸 ── */
    QScrollBar:vertical {{
        background: {COLORS['bg_surface']};
        width: 6px;
        border-radius: 3px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: #2D3A50;
        border-radius: 3px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #3D4A60;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: {COLORS['bg_surface']};
        height: 6px;
        border-radius: 3px;
    }}
    QScrollBar::handle:horizontal {{
        background: #2D3A50;
        border-radius: 3px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ── 對話框 ── */
    QDialog {{
        background: {COLORS['bg_elevated']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
    }}
    QMessageBox {{
        background: {COLORS['bg_elevated']};
        color: {COLORS['text_primary']};
    }}

    /* ── CheckBox ── */
    QCheckBox {{
        color: {COLORS['text_secondary']};
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1.5px solid {COLORS['border']};
        background: {COLORS['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background: {COLORS['accent']};
        border-color: {COLORS['accent']};
    }}

    /* ── GroupBox ── */
    QGroupBox {{
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        margin-top: 14px;
        padding: 12px;
        color: {COLORS['text_secondary']};
        font-size: 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: {COLORS['text_muted']};
        letter-spacing: 1px;
    }}

    /* ── InputDialog ── */
    QInputDialog {{
        background: {COLORS['bg_elevated']};
        color: {COLORS['text_primary']};
    }}
"""


class BasePage(QWidget):
    """所有功能頁面的基礎類別。"""

    def __init__(self, title: str, subtitle: str = "", user: dict = None):
        super().__init__()
        self.user = user or {}
        self.setStyleSheet(PAGE_STYLE)
        self._build_base(title, subtitle)

    def _build_base(self, title: str, subtitle: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)

        # ── 頁面標題列 ──
        header = QHBoxLayout()
        header.setSpacing(0)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("page_title")
        title_col.addWidget(lbl_title)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setObjectName("page_subtitle")
            title_col.addWidget(lbl_sub)

        header.addLayout(title_col)
        header.addStretch()
        layout.addLayout(header)
        layout.addSpacing(20)

        # 分隔線
        divider = QFrame()
        divider.setObjectName("header_divider")
        divider.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(divider)
        layout.addSpacing(24)

        # 內容區
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(16)
        layout.addLayout(self.content_layout)

    # ── 共用 helper ───────────────────────────────────────
    @staticmethod
    def make_table(headers: list[str]) -> QTableWidget:
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        # 設定表頭置中
        t.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        t.setShowGrid(True)
        t.setWordWrap(False)
        t.verticalHeader().setDefaultSectionSize(42)
        
        # 套用全域置中 Delegate
        t.setItemDelegate(CenterDelegate(t))
        return t

    @staticmethod
    def fill_table(table: QTableWidget, rows: list[list], center_cols: list[int] = None):
        table.setRowCount(0)
        for r, row_data in enumerate(rows):
            table.insertRow(r)
            for c, val in enumerate(row_data):
                item = QTableWidgetItem(str(val) if val is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(r, c, item)

    @staticmethod
    def make_filter_row() -> tuple[QHBoxLayout, "FilterRow"]:
        """建立標準篩選器列。"""
        row = QHBoxLayout()
        row.setSpacing(12)
        return row

    def confirm(self, title: str, message: str) -> bool:
        # 使用 None 作為 parent 以避免在 Mac 上的生命週期問題
        dlg = QMessageBox(None)
        dlg.setWindowTitle(title)
        dlg.setText(message)
        dlg.setIcon(QMessageBox.Icon.Question)
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dlg.setDefaultButton(QMessageBox.StandardButton.No)
        dlg.setStyleSheet(PAGE_STYLE)
        return dlg.exec() == QMessageBox.StandardButton.Yes

    def alert(self, title: str, message: str):
        dlg = QMessageBox(None)
        dlg.setWindowTitle(title)
        dlg.setText(message)
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.setStyleSheet(PAGE_STYLE)
        dlg.exec()

    def warn(self, title: str, message: str):
        dlg = QMessageBox(None)
        dlg.setWindowTitle(title)
        dlg.setText(message)
        dlg.setIcon(QMessageBox.Icon.Warning)
        dlg.setStyleSheet(PAGE_STYLE)
        dlg.exec()

    # ── 標準 Badge 標籤 ───────────────────────────────────
    @staticmethod
    def make_table_btn(label: str, style: str = "default") -> QPushButton:
        """
        建立適合放入表格 cell 的小型按鈕。
        style: 'default' | 'primary' | 'danger'
        """
        from PyQt6.QtWidgets import QSizePolicy
        btn = QPushButton(label)
        # 固定寬高，確保文字能顯示且按鈕不變形
        btn.setFixedSize(64, 26) 
        btn.setCursor(__import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
        
        if style == "primary":
            btn.setObjectName("btn_primary")
        elif style == "danger":
            btn.setObjectName("btn_danger")
            
        # 覆寫全域樣式的 min-height 與 padding，確保在 26px 高度下文字能垂直置中且不被遮蔽
        btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                padding: 0px;
                margin: 0px;
                min-height: 0px;
                max-height: 26px;
                border-radius: 4px;
            }
        """)
        return btn

    @staticmethod
    def make_badge(text: str, color: str = "blue") -> QLabel:
        """回傳一個小型 badge 標籤（用於狀態顯示）。"""
        lbl = QLabel(text)
        palette = {
            "blue":    ("color:#93C5FD; background:#172554;"),
            "green":   ("color:#6EE7B7; background:#064E3B;"),
            "yellow":  ("color:#FCD34D; background:#451A03;"),
            "red":     ("color:#FCA5A5; background:#450A0A;"),
        }
        style = palette.get(color, palette["blue"])
        lbl.setStyleSheet(
            f"{style} border-radius:4px; padding:2px 8px; "
            f"font-size:11px; font-weight:600;"
        )
        lbl.setFixedHeight(20)
        return lbl
