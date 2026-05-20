# ui/dashboard.py — 儀表板主頁

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QPushButton, QTabWidget,
)
from PyQt6.QtCore import Qt
from database.models.inventory import InventoryModel
from ui.base_page import CenterDelegate

class DashboardPage(QWidget):
    """登入後的首頁儀表板，顯示庫存警示摘要與明細。"""

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self._build_ui()

    def _build_ui(self):
        # 可捲動的外層
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        inner = QWidget()
        inner.setObjectName("dashboard_inner")
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(32, 28, 32, 28)
        self._inner_layout.setSpacing(24)

        # 標題列
        title_row = QHBoxLayout()
        title = QLabel("儀表板")
        title.setObjectName("dashboard_title")
        subtitle = QLabel("庫存警示摘要 · 切換此頁面時自動更新")
        subtitle.setObjectName("dashboard_subtitle")
        title_row.addWidget(title)
        title_row.addSpacing(16)
        title_row.addWidget(subtitle)
        title_row.addStretch()

        btn_refresh = QPushButton("↻  立即更新")
        btn_refresh.setObjectName("btn_refresh")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setFixedHeight(32)
        btn_refresh.clicked.connect(self.refresh)
        title_row.addWidget(btn_refresh)
        self._inner_layout.addLayout(title_row)

        # 摘要卡片列
        self._card_row = QHBoxLayout()
        self._card_row.setSpacing(18)
        self._card_expired  = self._make_summary_card("已過期試劑", "0", "瓶", "#DC3545", "#FFF5F5", "🚫")
        self._card_expiring = self._make_summary_card("即將到期（30天內）", "0", "瓶", "#FF8C00", "#FFF9F0", "⏳")
        self._card_low      = self._make_summary_card("低於安全庫存", "0", "種試劑", "#E67E22", "#FFF7F2", "⚠️")
        self._card_row.addWidget(self._card_expired)
        self._card_row.addWidget(self._card_expiring)
        self._card_row.addWidget(self._card_low)
        self._inner_layout.addLayout(self._card_row)

        # ── 頁籤明細區 (方案 A) ──
        self.tabs = QTabWidget()
        self.tabs.setObjectName("dashboard_tabs")
        
        # 1. 已過期頁籤
        self._tbl_expired = self._make_table(["試劑名稱", "料號", "組別", "批號", "效期", "已過期天數"])
        self.tabs.addTab(self._tbl_expired, " 已過期明細 ")
        
        # 2. 即將到期頁籤
        self._tbl_expiring = self._make_table(["試劑名稱", "料號", "組別", "批號", "效期", "剩餘天數"])
        self.tabs.addTab(self._tbl_expiring, " 即將到期明細 ")
        
        # 3. 低庫存頁籤
        self._tbl_low = self._make_table(["試劑名稱", "料號", "組別", "目前庫存", "安全庫存", "缺少數量"])
        self.tabs.addTab(self._tbl_low, " 低庫存明細 ")
        
        self.tabs.setMinimumHeight(450) # 設定足夠的高度
        self._inner_layout.addWidget(self.tabs)

        self._inner_layout.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._apply_style()

    # ── 元件工廠 ───────────────────────────────────────────

    def _make_summary_card(self, label: str, count: str, unit: str,
                           accent: str, bg: str, icon: str) -> QFrame:
        card = QFrame()
        card.setObjectName("summary_card")
        card.setStyleSheet(
            f"#summary_card {{ background: {bg}; border: 1px solid {accent}44; "
            f"border-radius: 12px; }}"
        )
        card.setMinimumHeight(135)

        main_layout = QHBoxLayout(card)
        main_layout.setContentsMargins(20, 15, 20, 15)
        
        # 左側大圖示
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 48px; background: transparent;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(icon_lbl)

        # 右側資訊區
        right_layout = QVBoxLayout()
        
        # 標題 (大字、靠右)
        lbl_label = QLabel(label)
        lbl_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        lbl_label.setStyleSheet(f"color: {accent}; font-size: 20px; font-weight: 700; background: transparent;")
        right_layout.addWidget(lbl_label)
        
        right_layout.addStretch()
        
        # 數字與單位 (靠右下)
        num_row = QHBoxLayout()
        num_row.addStretch()
        
        num_lbl = QLabel(count)
        num_lbl.setStyleSheet(f"color: #2D3436; font-size: 44px; font-weight: 700; background: transparent;")
        card._num_label = num_lbl
        
        unit_lbl = QLabel(unit)
        unit_lbl.setStyleSheet(f"color: #2D3436; font-size: 14px; font-weight: 600; background: transparent; margin-bottom: 6px;")
        
        num_row.addWidget(num_lbl, 0, Qt.AlignmentFlag.AlignBottom)
        num_row.addSpacing(4)
        num_row.addWidget(unit_lbl, 0, Qt.AlignmentFlag.AlignBottom)
        right_layout.addLayout(num_row)
        
        main_layout.addLayout(right_layout)
        
        return card

    def _make_section_header(self, title: str, color: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: 700; "
            f"border-left: 3px solid {color}; padding-left: 10px; "
            f"background: transparent;"
        )
        return lbl

    def _make_table(self, headers: list[str]) -> QTableWidget:
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        # 移除固定高度，由 QTabWidget 控制
        tbl.verticalHeader().setDefaultSectionSize(36)
        tbl.setStyleSheet(
            "alternate-background-color:#FDFBF7; background:#FFFFFF; "
            "border:1px solid #DEE2E6; border-radius:6px; "
            "color:#2D3436; gridline-color:#DEE2E6; font-size: 13px;"
        )
        tbl.horizontalHeader().setStyleSheet(
            "QHeaderView::section{background:#F1F3F5; color:#2D3436; "
            "border:none; border-right:1px solid #DEE2E6; "
            "border-bottom:1px solid #DEE2E6; padding:8px 6px; font-weight:bold;}"
        )
        tbl.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        tbl.setItemDelegate(CenterDelegate(tbl))
        return tbl

    # ── 資料刷新 ───────────────────────────────────────────

    def refresh(self):
        """重新從資料庫載入所有儀表板資料。"""
        try:
            self._load_expired()
            self._load_expiring()
            self._load_low_stock()
        except Exception as e:
            print(f"[Dashboard] 資料載入錯誤：{e}")

    def showEvent(self, event):
        """每次頁面切換顯示時自動刷新。"""
        super().showEvent(event)
        self.refresh()

    def _load_expired(self):
        rows = InventoryModel.get_expired_in_stock()
        count = len(rows)
        self._card_expired._num_label.setText(str(count))
        self._card_expired._num_label.setStyleSheet(f"color: {'#DC3545' if count > 0 else '#2D3436'}; font-size: 32px; font-weight: 800;")
        self._fill_table(
            self._tbl_expired, rows,
            lambda r: [
                r["reagent_name"],
                r["item_number"] or "",
                r["dept_name"],
                r["lot_number"],
                str(r["expiry_date"]),
                f"{r['days_overdue']} 天",
            ],
            highlight_col=5,
            highlight_color="#e05555",
        )

    def _load_expiring(self):
        rows = InventoryModel.get_expiring_soon_in_stock(days=30)
        count = len(rows)
        self._card_expiring._num_label.setText(str(count))
        self._card_expiring._num_label.setStyleSheet(f"color: {'#DC3545' if count > 0 else '#2D3436'}; font-size: 32px; font-weight: 800;")
        self._fill_table(
            self._tbl_expiring, rows,
            lambda r: [
                r["reagent_name"],
                r["item_number"] or "",
                r["dept_name"],
                r["lot_number"],
                str(r["expiry_date"]),
                f"{r['days_remaining']} 天",
            ],
            highlight_col=5,
            highlight_color="#d4a72c",
        )

    def _load_low_stock(self):
        rows = InventoryModel.get_low_stock_reagents()
        count = len(rows)
        self._card_low._num_label.setText(str(count))
        self._card_low._num_label.setStyleSheet(f"color: {'#DC3545' if count > 0 else '#2D3436'}; font-size: 32px; font-weight: 800;")
        unit_map = {r["reagent_id"]: r.get("count_unit") or "瓶" for r in rows}
        self._fill_table(
            self._tbl_low, rows,
            lambda r: [
                r["reagent_name"],
                r["item_number"] or "",
                r["dept_name"],
                f"{r['current_stock_count']:.1f} {r.get('count_unit') or '瓶'}",
                f"{float(r['safety_stock'] or 0):.1f} {r.get('count_unit') or '瓶'}",
                f"-{float(r['safety_stock'] or 0) - float(r['current_stock_count']):.1f} {r.get('count_unit') or '瓶'}",
            ],
            highlight_col=5,
            highlight_color="#d4702c",
        )

    def _fill_table(self, tbl: QTableWidget, rows: list,
                    row_fn, highlight_col: int = -1, highlight_color: str = ""):
        from PyQt6.QtGui import QColor
        tbl.setRowCount(0)
        if not rows:
            tbl.insertRow(0)
            placeholder = QTableWidgetItem("— 無資料 —")
            placeholder.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setForeground(QColor("#B2BEC3"))
            tbl.setItem(0, 0, placeholder)
            tbl.setSpan(0, 0, 1, tbl.columnCount())
            return

        for r_idx, row in enumerate(rows):
            tbl.insertRow(r_idx)
            for c_idx, val in enumerate(row_fn(row)):
                item = QTableWidgetItem(str(val))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if c_idx == highlight_col and highlight_color:
                    item.setForeground(QColor(highlight_color))
                tbl.setItem(r_idx, c_idx, item)

    # ── 樣式 ───────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet("""
            #dashboard_inner {
                background: #FDFBF7;
            }
            #dashboard_title {
                color: #2D3436;
                font-size: 22px;
                font-weight: 700;
            }
            #dashboard_subtitle {
                color: #636E72;
                font-size: 12px;
            }
            #btn_refresh {
                background: #F1F3F5;
                color: #2D3436;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 0 12px;
                font-size: 12px;
            }
            #btn_refresh:hover {
                background: #E2E8F0;
            }
            /* 頁籤樣式 */
            QTabWidget::pane {
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                top: -1px;
                background: #FFFFFF;
            }
            QTabBar::tab {
                background: #F1F3F5;
                color: #636E72;
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #DEE2E6;
                border-bottom: none;
                margin-right: 4px;
                font-size: 13px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #0066CC;
                border-bottom: 2px solid #0066CC;
            }
            QTabBar::tab:hover {
                background: #E2E8F0;
                color: #2D3436;
            }
        """)
