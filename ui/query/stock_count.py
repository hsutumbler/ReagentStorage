# ui/query/stock_count.py — 庫存盤點頁面（以盤點單位顯示）

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QComboBox, QPushButton, QTableWidgetItem,
)
from PyQt6.QtGui import QColor
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.inventory import InventoryModel


class StockCountPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("庫存盤點", "查詢各試劑目前庫存（以盤點單位顯示）", user)
        self._build()

    def _build(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("廠商："))
        self.cb_vendor = QComboBox()
        self.cb_vendor.addItem("全部", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        row.addWidget(self.cb_vendor)

        row.addWidget(QLabel("組別："))
        self.cb_dept = QComboBox()
        self.cb_dept.addItem("全部", None)
        for d in ReagentModel.get_all_departments():
            self.cb_dept.addItem(d["dept_name"], d["dept_id"])
        row.addWidget(self.cb_dept)

        btn = QPushButton("查詢")
        btn.setObjectName("btn_primary")
        btn.clicked.connect(self._search)
        row.addWidget(btn)
        row.addStretch()
        self.content_layout.addLayout(row)

        headers = ["試劑名稱", "料號", "組別", "廠商", "目前庫存", "安全庫存", "盤點單位"]
        self.table = self.make_table(headers)
        self.content_layout.addWidget(self.table)

    def _search(self):
        vendor_id = self.cb_vendor.currentData()
        dept_id = self.cb_dept.currentData()
        reagents = ReagentModel.get_all()
        if vendor_id:
            reagents = [r for r in reagents if r["vendor_id"] == vendor_id]
        if dept_id:
            reagents = [r for r in reagents if r["dept_id"] == dept_id]

        self.table.setRowCount(0)
        for r_idx, rg in enumerate(reagents):
            self.table.insertRow(r_idx)
            stock = InventoryModel.get_current_stock_count(rg["reagent_id"])
            s2c = float(rg.get("stock_to_count") or 1)
            stock_count = stock * s2c
            stock_unit = rg.get("stock_unit") or "未設單位"
            unit = rg.get("count_unit") or "未設單位"

            # 安全庫存換算為盤點單位
            safety_stock_base = float(rg.get("safety_stock") or 0)
            safety_count = safety_stock_base * s2c
            low = stock_count < safety_count and safety_count > 0

            for c_idx, val in enumerate([
                rg["reagent_name"], rg["item_number"] or "",
                rg["dept_name"], rg["vendor_name"],
                f"{stock_count:.1f}", f"{safety_count:.1f}", unit,
            ]):
                item = QTableWidgetItem(str(val))
                if low:
                    item.setForeground(QColor("#e07820"))
                self.table.setItem(r_idx, c_idx, item)
