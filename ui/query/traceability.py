# ui/query/traceability.py — 試劑庫存追溯查詢

import csv
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton,
    QDateEdit, QTableWidgetItem, QLineEdit, QFileDialog, QCheckBox,
)
from PyQt6.QtCore import QDate, Qt
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.inventory import InventoryModel


class TraceabilityPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("試劑庫存追溯", "查詢試劑完整入出庫歷程", user)
        self._last_results = []
        self._build()

    def _build(self):
        filter_area = QVBoxLayout()
        
        # 第一排：基本篩選
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("廠商："))
        self.cb_vendor = QComboBox()
        self.cb_vendor.addItem("全部", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        row1.addWidget(self.cb_vendor)

        row1.addWidget(QLabel("組別："))
        self.cb_dept = QComboBox()
        self.cb_dept.addItem("全部", None)
        for d in ReagentModel.get_all_departments():
            self.cb_dept.addItem(d["dept_name"], d["dept_id"])
        row1.addWidget(self.cb_dept)

        row1.addWidget(QLabel("狀態："))
        self.cb_status = QComboBox()
        self.cb_status.addItem("全部", None)
        self.cb_status.addItem("在庫", 0)
        self.cb_status.addItem("已出庫", 1)
        self.cb_status.addItem("已調整刪除", 2)
        row1.addWidget(self.cb_status)
        
        row1.addWidget(QLabel("RID："))
        self.f_rid = QLineEdit()
        self.f_rid.setPlaceholderText("模糊搜尋")
        self.f_rid.setFixedWidth(120)
        row1.addWidget(self.f_rid)

        row1.addWidget(QLabel("批號："))
        self.f_lot = QLineEdit()
        self.f_lot.setPlaceholderText("模糊搜尋")
        self.f_lot.setFixedWidth(120)
        row1.addWidget(self.f_lot)
        row1.addStretch()
        filter_area.addLayout(row1)

        # 第二排：日期篩選
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("入庫日期："))
        self.f_from = QDateEdit()
        self.f_from.setCalendarPopup(True)
        self.f_from.setDate(QDate.currentDate().addMonths(-3))
        self.f_from.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self.f_from)
        row2.addWidget(QLabel("至"))
        self.f_to = QDateEdit()
        self.f_to.setCalendarPopup(True)
        self.f_to.setDate(QDate.currentDate())
        self.f_to.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self.f_to)

        row2.addSpacing(20)
        self.chk_issue_date = QCheckBox("出庫日期篩選：")
        row2.addWidget(self.chk_issue_date)
        self.f_issue_from = QDateEdit()
        self.f_issue_from.setCalendarPopup(True)
        self.f_issue_from.setDate(QDate.currentDate().addMonths(-1))
        self.f_issue_from.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self.f_issue_from)
        row2.addWidget(QLabel("至"))
        self.f_issue_to = QDateEdit()
        self.f_issue_to.setCalendarPopup(True)
        self.f_issue_to.setDate(QDate.currentDate())
        self.f_issue_to.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self.f_issue_to)

        row2.addStretch()
        
        btn_search = QPushButton("🔍 查詢")
        btn_search.setObjectName("btn_primary")
        btn_search.clicked.connect(self._search)
        row2.addWidget(btn_search)

        btn_export = QPushButton("📤 匯出 CSV")
        btn_export.setObjectName("btn_secondary")
        btn_export.clicked.connect(self._export_csv)
        row2.addWidget(btn_export)
        
        filter_area.addLayout(row2)
        self.content_layout.addLayout(filter_area)

        headers = ["試劑名稱", "RID", "批號", "穩定效期", "入庫日期", "狀態", "出庫時間"]
        self.table = self.make_table(headers)
        self.content_layout.addWidget(self.table)

    def _search(self):
        issue_from = self.f_issue_from.date().toPyDate() if self.chk_issue_date.isChecked() else None
        issue_to = self.f_issue_to.date().toPyDate() if self.chk_issue_date.isChecked() else None
        
        rows = InventoryModel.trace_query(
            vendor_id=self.cb_vendor.currentData(),
            dept_id=self.cb_dept.currentData(),
            status=self.cb_status.currentData(),
            rid=self.f_rid.text().strip(),
            lot_number=self.f_lot.text().strip(),
            date_from=self.f_from.date().toPyDate(),
            date_to=self.f_to.date().toPyDate(),
            issue_from=issue_from,
            issue_to=issue_to,
        )
        self._last_results = rows
        status_map = {0: "在庫", 1: "已出庫", 2: "已調整刪除"}
        self.table.setRowCount(0)
        for r, inv in enumerate(rows):
            self.table.insertRow(r)
            for c_idx, val in enumerate([
                inv["reagent_name"], inv["rid"], inv["lot_number"],
                str(inv["expiry_date"]), str(inv["received_date"]),
                status_map.get(inv["status"], "?"),
                str(inv["issued_at"]) if inv["issued_at"] else "",
            ]):
                self.table.setItem(r, c_idx, QTableWidgetItem(val))

    def _export_csv(self):
        if not self._last_results:
            self.warn(self, "提示", "請先進行查詢再匯出資料")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "匯出 CSV", f"庫存追蹤_{QDate.currentDate().toString('yyyyMMdd')}.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            status_map = {0: "在庫", 1: "已出庫", 2: "已調整刪除"}
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["試劑名稱", "RID", "批號", "穩定效期", "入庫日期", "狀態", "出庫時間"])
                for inv in self._last_results:
                    writer.writerow([
                        inv["reagent_name"], inv["rid"], inv["lot_number"],
                        str(inv["expiry_date"]), str(inv["received_date"]),
                        status_map.get(inv["status"], "?"),
                        str(inv["issued_at"]) if inv["issued_at"] else "",
                    ])
            self.alert(self, "匯出成功", f"資料已成功儲存至：\n{path}")
        except Exception as e:
            self.warn(self, "匯出失敗", str(e))
