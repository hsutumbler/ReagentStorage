# ui/nonconforming/nc_reagent.py — 不合格試劑處理頁面

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDateEdit, QTextEdit,
    QFrame, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import QDate
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.nonconforming import NonConformingModel


class NonConformingPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("不合格試劑處理", "記錄不合格試劑資訊（ISO 15189 要求）", user)
        self._build()

    def _build(self):
        # ── 新增表單 ──
        card = QFrame()
        card.setObjectName("section_card")
        form_layout = QVBoxLayout(card)
        form_layout.setSpacing(10)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("廠商 *"))
        self.cb_vendor = QComboBox()
        self.cb_vendor.addItem("— 請選擇廠商 —", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        self.cb_vendor.currentIndexChanged.connect(self._load_reagents)
        row1.addWidget(self.cb_vendor)

        row1.addWidget(QLabel("試劑 *"))
        self.cb_reagent = QComboBox()
        self.cb_reagent.setMinimumWidth(200)
        row1.addWidget(self.cb_reagent)
        row1.addStretch()
        form_layout.addLayout(row1)

        self._load_reagents()

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("批號 *"))
        self.f_lot = QLineEdit()
        self.f_lot.setPlaceholderText("批號")
        row2.addWidget(self.f_lot)
        row2.addWidget(QLabel("穩定效期"))
        self.f_expiry = QDateEdit()
        self.f_expiry.setCalendarPopup(True)
        self.f_expiry.setDate(QDate.currentDate())
        self.f_expiry.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self.f_expiry)
        row2.addStretch()
        form_layout.addLayout(row2)

        form_layout.addWidget(QLabel("不合格原因 *"))
        self.f_reason = QTextEdit()
        self.f_reason.setPlaceholderText("請詳述不合格原因…")
        self.f_reason.setFixedHeight(80)
        self.f_reason.setStyleSheet(
            "background:#1a2535; border:1px solid #2d4060; border-radius:6px; "
            "color:#d0e8ff; padding:8px; font-size:13px;"
        )
        form_layout.addWidget(self.f_reason)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("✔  儲存記錄")
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)
        form_layout.addLayout(btn_row)

        self.content_layout.addWidget(card)

        # ── 最近記錄 ──
        lbl = QLabel("最近不合格記錄")
        lbl.setStyleSheet("color:#60c0ff; font-weight:bold; font-size:14px;")
        self.content_layout.addWidget(lbl)

        headers = ["廠商", "試劑名稱", "批號", "穩定效期", "不合格原因", "紀錄時間", "紀錄人員"]
        self.table = self.make_table(headers)
        
        # 調整欄位寬度比例
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 廠商
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)      # 試劑名稱
        self.table.setColumnWidth(1, 160)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # 批號
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # 效期
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # 不合格原因
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents) # 紀錄時間
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents) # 紀錄人員

        self.content_layout.addWidget(self.table)
        self._load_recent()

    def _load_reagents(self):
        vendor_id = self.cb_vendor.currentData()
        self.cb_reagent.clear()
        self.cb_reagent.addItem("— 請選擇試劑 —", None)
        
        reagents = ReagentModel.get_all()
        if vendor_id:
            reagents = [r for r in reagents if r["vendor_id"] == vendor_id]
        
        for r in reagents:
            self.cb_reagent.addItem(r["reagent_name"], r["reagent_id"])

    def _save(self):
        vendor_id  = self.cb_vendor.currentData()
        reagent_id = self.cb_reagent.currentData()
        lot_number = self.f_lot.text().strip()
        expiry     = self.f_expiry.date().toPyDate()
        reason     = self.f_reason.toPlainText().strip()

        if not lot_number or not reason:
            self.warn( "驗證", "批號與不合格原因為必填")
            return

        NonConformingModel.create(
            vendor_id=vendor_id, reagent_id=reagent_id,
            lot_number=lot_number, expiry_date=expiry,
            nc_reason=reason, recorded_by=self.user["user_id"],
        )
        self.alert(self, "完成", "不合格試劑記錄已儲存")
        self.f_lot.clear()
        self.f_reason.clear()
        self._load_recent()

    def _load_recent(self):
        rows = NonConformingModel.query()[:20]
        self.table.setRowCount(0)
        for r, nc in enumerate(rows):
            self.table.insertRow(r)
            for c_idx, val in enumerate([
                nc["vendor_name"], nc["reagent_name"], nc["lot_number"],
                str(nc["expiry_date"] or ""), nc["nc_reason"],
                str(nc["recorded_at"]), nc["recorder_name"],
            ]):
                self.table.setItem(r, c_idx, QTableWidgetItem(str(val)))
