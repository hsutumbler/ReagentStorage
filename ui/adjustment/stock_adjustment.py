# ui/adjustment/stock_adjustment.py — 調整庫存頁面（試劑負責人、組長以上）

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidgetItem, QInputDialog,
)
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.inventory import InventoryModel
from database.models.stock_adjustment import StockAdjustmentModel


class StockAdjustmentPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("調整庫存",
                         "篩選並刪除異常庫存項目（操作將留下稽核記錄）", user)
        self._build()

    def _build(self):
        # ── 篩選器 ──
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("廠商："))
        self.cb_vendor = QComboBox()
        self.cb_vendor.addItem("全部", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        filter_row.addWidget(self.cb_vendor)

        filter_row.addWidget(QLabel("組別："))
        self.cb_dept = QComboBox()
        self.cb_dept.addItem("全部", None)
        for d in ReagentModel.get_all_departments():
            self.cb_dept.addItem(d["dept_name"], d["dept_id"])
        filter_row.addWidget(self.cb_dept)

        filter_row.addWidget(QLabel("試劑："))
        self.cb_reagent = QComboBox()
        self.cb_reagent.addItem("全部", None)
        for r in ReagentModel.get_all():
            self.cb_reagent.addItem(r["reagent_name"], r["reagent_id"])
        filter_row.addWidget(self.cb_reagent)

        btn_search = QPushButton("查詢")
        btn_search.setObjectName("btn_primary")
        btn_search.clicked.connect(self._search)
        filter_row.addWidget(btn_search)
        filter_row.addStretch()
        self.content_layout.addLayout(filter_row)

        # ── 結果表格 ──
        headers = ["試劑名稱", "RID", "批號", "穩定效期", "入庫日期", "廠商", "操作"]
        self.table = self.make_table(headers)
        self.table.horizontalHeader().setSectionResizeMode(
            6, self.table.horizontalHeader().ResizeMode.Fixed
        )
        self.table.setColumnWidth(6, 80)
        self.content_layout.addWidget(self.table)

        self._rows = []

    def _search(self):
        vendor_id  = self.cb_vendor.currentData()
        dept_id    = self.cb_dept.currentData()
        reagent_id = self.cb_reagent.currentData()

        rows = InventoryModel.filter_inventory(vendor_id, dept_id, reagent_id, status=0)
        self._rows = rows
        self.table.setRowCount(0)

        for r, inv in enumerate(rows):
            self.table.insertRow(r)
            for c_idx, val in enumerate([
                inv["reagent_name"], inv["rid"], inv["lot_number"],
                str(inv["expiry_date"]), str(inv["received_date"]),
                inv["vendor_name"],
            ]):
                self.table.setItem(r, c_idx, QTableWidgetItem(val))

            btn_del = self.make_table_btn("刪除", "danger")
            btn_del.clicked.connect(lambda _, idx=r: self._delete(idx))
            self.table.setCellWidget(r, 6, btn_del)

    def _delete(self, row_idx: int):
        if row_idx >= len(self._rows):
            return
        inv = self._rows[row_idx]

        reason, ok = QInputDialog.getText(
            self, "調整原因",
            f"請輸入刪除「{inv['reagent_name']}」（RID: {inv['rid']}）的原因："
        )
        if not ok:
            return

        if not self.confirm(self, "確認刪除",
                            f"確定要刪除 RID：{inv['rid']} 嗎？\n此操作將留下稽核記錄。"):
            return

        StockAdjustmentModel.record(
            inventory_id=inv["inventory_id"],
            rid=inv["rid"],
            reagent_name=inv["reagent_name"],
            lot_number=inv["lot_number"],
            expiry_date=inv["expiry_date"],
            received_date=inv["received_date"],
            adjusted_by=self.user["user_id"],
            reason=reason,
        )
        InventoryModel.mark_adjusted(inv["inventory_id"])
        self.alert(self, "完成", f"RID {inv['rid']} 已調整刪除")
        self._search()
