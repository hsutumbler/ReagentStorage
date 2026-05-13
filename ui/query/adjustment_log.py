# ui/query/adjustment_log.py — 庫存修改查詢

from PyQt6.QtWidgets import QTableWidgetItem
from ui.base_page import BasePage
from database.models.stock_adjustment import StockAdjustmentModel


class AdjustmentLogPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("庫存調整記錄", "查詢所有庫存調整的稽核記錄", user)
        self._build()

    def _build(self):
        from PyQt6.QtWidgets import QHBoxLayout, QPushButton
        row = QHBoxLayout()
        btn = QPushButton("載入記錄")
        btn.setObjectName("btn_primary")
        btn.clicked.connect(self._load)
        row.addWidget(btn)
        row.addStretch()
        self.content_layout.addLayout(row)

        headers = ["試劑名稱", "RID", "批號", "穩定效期",
                   "入庫日期", "調整時間", "調整人員", "原因"]
        self.table = self.make_table(headers)
        self.content_layout.addWidget(self.table)
        self._load()

    def _load(self):
        rows = StockAdjustmentModel.query_all()
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
