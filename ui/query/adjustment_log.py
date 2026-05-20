from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QDateEdit, QTableWidgetItem, QFrame
)
from PyQt6.QtCore import QDate, Qt
from ui.base_page import BasePage
from database.models.stock_adjustment import StockAdjustmentModel


class AdjustmentLogPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("調整庫存查詢", "查詢所有庫存調整的稽核記錄", user)
        self._build()

    def _build(self):
        # ── 篩選器 ──
        filter_area = QFrame()
        filter_area.setObjectName("section_card")
        filter_layout = QHBoxLayout(filter_area)
        filter_layout.setSpacing(15)

        filter_layout.addWidget(QLabel("項目："))
        self.f_query = QLineEdit()
        self.f_query.setPlaceholderText("輸入試劑名稱或 RID...")
        self.f_query.setFixedWidth(200)
        filter_layout.addWidget(self.f_query)

        filter_layout.addWidget(QLabel("調整時間："))
        self.f_from = QDateEdit()
        self.f_from.setCalendarPopup(True)
        self.f_from.setDate(QDate.currentDate().addMonths(-3))
        self.f_from.setDisplayFormat("yyyy-MM-dd")
        self.f_from.setFixedWidth(140)
        filter_layout.addWidget(self.f_from)

        filter_layout.addWidget(QLabel("至"))
        self.f_to = QDateEdit()
        self.f_to.setCalendarPopup(True)
        self.f_to.setDate(QDate.currentDate())
        self.f_to.setDisplayFormat("yyyy-MM-dd")
        self.f_to.setFixedWidth(140)
        filter_layout.addWidget(self.f_to)

        filter_layout.addStretch()

        btn_search = QPushButton("🔍  查詢")
        btn_search.setObjectName("btn_primary")
        btn_search.setFixedWidth(100)
        btn_search.clicked.connect(self._load)
        filter_layout.addWidget(btn_search)

        self.content_layout.addWidget(filter_area)

        # ── 表格 ──
        headers = ["試劑名稱", "RID", "批號", "穩定效期",
                   "入庫日期", "調整時間", "調整人員", "原因"]
        self.table = self.make_table(headers)
        self.content_layout.addWidget(self.table)
        self._load()

    def _load(self):
        query = self.f_query.text().strip()
        date_from = self.f_from.date().toString("yyyy-MM-dd")
        date_to = self.f_to.date().toString("yyyy-MM-dd")

        rows = StockAdjustmentModel.query_all(query, date_from, date_to)
        self.table.setRowCount(0)
        for r, adj in enumerate(rows):
            self.table.insertRow(r)
            for c_idx, val in enumerate([
                adj["reagent_name"], adj["rid"], adj["lot_number"],
                str(adj["expiry_date"]), str(adj["received_date"]),
                str(adj["adjusted_at"]), adj["adjuster_name"],
                adj["reason"] or "",
            ]):
                self.table.setItem(r, c_idx, QTableWidgetItem(str(val)))
