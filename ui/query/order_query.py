# ui/query/order_query.py — 訂購單查詢

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QComboBox, QPushButton,
    QDateEdit, QTableWidgetItem, QFileDialog, QWidget, QHeaderView
)
from PyQt6.QtCore import QDate, Qt
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.purchase_order import PurchaseOrderModel
from services.label_printer import print_po_label
from services.report_generator import ReportGenerator


class OrderQueryPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("訂購單查詢", "查詢歷史訂購單", user)
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

        row.addWidget(QLabel("建立日期從："))
        self.f_from = QDateEdit()
        self.f_from.setCalendarPopup(True)
        self.f_from.setDate(QDate.currentDate().addMonths(-3))
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

        headers = ["訂購單條碼", "廠商", "組別", "建立人員", "建立時間", "狀態", "操作"]
        self.table = self.make_table(headers)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 100)  # 固定寬度防止裁切
        self.content_layout.addWidget(self.table)

    def _search(self):
        status_map = {0: "草稿", 1: "已送出", 2: "已入庫"}
        rows = PurchaseOrderModel.query_orders(
            vendor_id=self.cb_vendor.currentData(),
            dept_id=self.cb_dept.currentData(),
            date_from=self.f_from.date().toPyDate(),
            date_to=self.f_to.date().toPyDate(),
        )
        self.table.setRowCount(0)
        for r, po in enumerate(rows):
            self.table.insertRow(r)
            data = [
                po["po_code"], po["vendor_name"], po["dept_name"],
                po["creator_name"], str(po["created_at"]),
                status_map.get(po["status"], "?"),
            ]
            for c_idx, val in enumerate(data):
                self.table.setItem(r, c_idx, QTableWidgetItem(str(val)))
            
            # A4 列印按鈕 (比照庫存調整的按鈕方式)
            btn_a4 = self.make_table_btn("A4 列印", "primary")
            btn_a4.clicked.connect(lambda checked, p=po: self._print_a4(p))

            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(5, 2, 5, 2)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(btn_a4)
            self.table.setCellWidget(r, 6, container)

    def _reprint_po(self, po):
        try:
            print_po_label(po["po_code"], po["vendor_name"])
            self.alert(self, "成功", f"標籤已送至 Zebra 印表機")
        except Exception as e:
            self.warn( "列印失敗", str(e))

    def _print_a4(self, po):
        filename, _ = QFileDialog.getSaveFileName(
            self, "儲存訂購單 PDF", f"PO_{po['po_code']}.pdf", "PDF Files (*.pdf)"
        )
        if filename:
            success = ReportGenerator.generate_po_pdf(po, filename)
            if success:
                self.alert(self, "成功", f"訂購單 PDF 已儲存至：\n{filename}")
                import os
                # macOS 開啟 PDF
                os.system(f"open '{filename}'")
            else:
                self.warn( "失敗", "產生 PDF 時發生錯誤")
