# ui/query/nc_query.py — 不合格試劑查詢

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QComboBox, QPushButton,
    QDateEdit, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import QDate
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.nonconforming import NonConformingModel


class NcQueryPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("不合格試劑查詢", "查詢歷史不合格試劑記錄", user)
        self._build()

    def _build(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("廠商："))
        self.cb_vendor = QComboBox()
        self.cb_vendor.addItem("全部", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        row.addWidget(self.cb_vendor)

        row.addWidget(QLabel("試劑："))
        self.cb_reagent = QComboBox()
        self.cb_reagent.addItem("全部", None)
        for r in ReagentModel.get_all():
            self.cb_reagent.addItem(r["reagent_name"], r["reagent_id"])
        row.addWidget(self.cb_reagent)

        row.addWidget(QLabel("記錄日期從："))
        self.f_from = QDateEdit()
        self.f_from.setCalendarPopup(True)
        self.f_from.setDate(QDate.currentDate().addMonths(-6))
        self.f_from.setDisplayFormat("yyyy-MM-dd")
        row.addWidget(self.f_from)
        row.addWidget(QLabel("至："))
        self.f_to = QDateEdit()
        self.f_to.setCalendarPopup(True)
        self.f_to.setDate(QDate.currentDate())
        self.f_to.setDisplayFormat("yyyy-MM-dd")
        row.addWidget(self.f_to)

        btn = QPushButton("查詢")
        btn.setObjectName("btn_primary")
        btn.clicked.connect(self._search)
        row.addWidget(btn)
        row.addStretch()
        self.content_layout.addLayout(row)

        headers = ["廠商", "試劑名稱", "批號", "穩定效期",
                   "不合格原因", "紀錄時間", "紀錄人員"]
        self.table = self.make_table(headers)
        
        # 調整欄位寬度比例
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive) # 先改為互動模式，避免全域 Stretch 覆蓋
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 廠商
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)      # 試劑名稱
        self.table.setColumnWidth(1, 180)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # 批號
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # 效期
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # 不合格原因 (佔據剩餘空間)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # 紀錄時間
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # 紀錄人員

        self.content_layout.addWidget(self.table)

    def _search(self):
        rows = NonConformingModel.query(
            vendor_id=self.cb_vendor.currentData(),
            reagent_id=self.cb_reagent.currentData(),
            date_from=self.f_from.date().toPyDate(),
            date_to=self.f_to.date().toPyDate(),
        )
        self.table.setRowCount(0)
        for r, nc in enumerate(rows):
            self.table.insertRow(r)
            for c_idx, val in enumerate([
                nc["vendor_name"], nc["reagent_name"], nc["lot_number"],
                str(nc["expiry_date"] or ""), nc["nc_reason"],
                str(nc["recorded_at"]), nc["recorder_name"],
            ]):
                self.table.setItem(r, c_idx, QTableWidgetItem(str(val)))
