# ui/query/traceability.py — 試劑庫存追溯查詢

import csv
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton,
    QDateEdit, QTableWidgetItem, QLineEdit, QFileDialog, QCheckBox,
    QDialog, QRadioButton, QGroupBox, QMessageBox
)
from PyQt6.QtCore import QDate, Qt
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.inventory import InventoryModel
from services.label_printer import (
    print_receive_label_large, print_receive_label_qr,
    print_issue_label_large, print_issue_label_qr
)


class PrintLabelDialog(QDialog):
    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("補印標籤")
        self.setFixedWidth(300)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 1. 標籤種類
        group_type = QGroupBox("標籤種類")
        type_layout = QVBoxLayout(group_type)
        self.rb_receive = QRadioButton("入庫標籤")
        self.rb_issue = QRadioButton("出庫標籤")
        
        # 智慧判斷：如果沒出庫日期，則出庫標籤反灰
        if not self.item.get("issued_at"):
            self.rb_issue.setEnabled(False)
            self.rb_issue.setText("出庫標籤 (尚未出庫)")
            self.rb_issue.setStyleSheet("color: gray;")
            self.rb_receive.setChecked(True)
        else:
            self.rb_issue.setChecked(True) # 已出庫則預設印出庫標籤
            
        type_layout.addWidget(self.rb_receive)
        type_layout.addWidget(self.rb_issue)
        layout.addWidget(group_type)

        # 2. 標籤格式
        group_fmt = QGroupBox("標籤格式")
        fmt_layout = QVBoxLayout(group_fmt)
        self.rb_text = QRadioButton("一般文字標籤")
        self.rb_qr = QRadioButton("QR code標籤")
        self.rb_text.setChecked(True)
        fmt_layout.addWidget(self.rb_text)
        fmt_layout.addWidget(self.rb_qr)
        layout.addWidget(group_fmt)

        # 按鈕
        btns = QHBoxLayout()
        btn_ok = QPushButton("確認列印")
        btn_ok.setObjectName("btn_primary")
        btn_ok.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        layout.addLayout(btns)

    def get_selection(self):
        return {
            "type": "issue" if self.rb_issue.isChecked() else "receive",
            "format": "qr" if self.rb_qr.isChecked() else "text"
        }


class TraceabilityPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("庫存追溯", "查詢試劑完整入出庫歷程", user)
        self._last_results = []
        self._build()

    def _build(self):
        filter_area = QVBoxLayout()
        filter_area.setSpacing(15) # 增加行距
        
        # 第一排：基本篩選
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addWidget(QLabel("廠商："))
        self.cb_vendor = QComboBox()
        self.cb_vendor.addItem("全部", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        self.cb_vendor.currentIndexChanged.connect(self._update_reagents)
        row1.addWidget(self.cb_vendor)

        row1.addWidget(QLabel("試劑名稱："))
        self.cb_reagent = QComboBox()
        self.cb_reagent.setFixedWidth(160)
        row1.addWidget(self.cb_reagent)
        self._update_reagents() # 初始化

        row1.addWidget(QLabel("狀態："))
        self.cb_status = QComboBox()
        self.cb_status.addItem("全部", None)
        self.cb_status.addItem("在庫", 0)
        self.cb_status.addItem("已出庫", 1)
        self.cb_status.addItem("已調整刪除", 2)
        row1.addWidget(self.cb_status)
        
        row1.addWidget(QLabel("RID："))
        self.f_rid = QLineEdit()
        self.f_rid.setPlaceholderText("搜尋")
        self.f_rid.setFixedWidth(100)
        row1.addWidget(self.f_rid)

        row1.addWidget(QLabel("批號："))
        self.f_lot = QLineEdit()
        self.f_lot.setPlaceholderText("搜尋")
        self.f_lot.setFixedWidth(100)
        row1.addWidget(self.f_lot)
        row1.addStretch()
        filter_area.addLayout(row1)

        # 第二排：日期篩選 (獨立一排以確保寬度充足)
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        row2.addWidget(QLabel("入庫日期："))
        self.f_from = QDateEdit()
        self.f_from.setCalendarPopup(True)
        self.f_from.setDate(QDate.currentDate().addMonths(-3))
        self.f_from.setDisplayFormat("yyyy / MM / dd")
        self.f_from.setFixedWidth(160)
        row2.addWidget(self.f_from)
        
        row2.addWidget(QLabel("至"))
        self.f_to = QDateEdit()
        self.f_to.setCalendarPopup(True)
        self.f_to.setDate(QDate.currentDate())
        self.f_to.setDisplayFormat("yyyy / MM / dd")
        self.f_to.setFixedWidth(160)
        row2.addWidget(self.f_to)

        row2.addSpacing(30)
        self.chk_issue_date = QCheckBox("出庫日期篩選")
        row2.addWidget(self.chk_issue_date)
        
        self.f_issue_from = QDateEdit()
        self.f_issue_from.setCalendarPopup(True)
        self.f_issue_from.setDate(QDate.currentDate().addMonths(-1))
        self.f_issue_from.setDisplayFormat("yyyy / MM / dd")
        self.f_issue_from.setFixedWidth(160)
        row2.addWidget(self.f_issue_from)
        
        row2.addWidget(QLabel("至"))
        self.f_issue_to = QDateEdit()
        self.f_issue_to.setCalendarPopup(True)
        self.f_issue_to.setDate(QDate.currentDate())
        self.f_issue_to.setDisplayFormat("yyyy / MM / dd")
        self.f_issue_to.setFixedWidth(160)
        row2.addWidget(self.f_issue_to)
        row2.addStretch()
        filter_area.addLayout(row2)

        # 第三排：操作按鈕
        row3 = QHBoxLayout()
        row3.addStretch()
        
        btn_search = QPushButton("🔍  查詢")
        btn_search.setObjectName("btn_primary")
        btn_search.setFixedWidth(100)
        btn_search.clicked.connect(self._search)
        row3.addWidget(btn_search)

        btn_print = QPushButton("🖨️  補印標籤")
        btn_print.setObjectName("btn_success")
        btn_print.setFixedWidth(120)
        btn_print.clicked.connect(self._print_label)
        row3.addWidget(btn_print)

        btn_export = QPushButton("📤  匯出 CSV")
        btn_export.setObjectName("btn_secondary")
        btn_export.setFixedWidth(120)
        btn_export.clicked.connect(self._export_csv)
        row3.addWidget(btn_export)
        
        row3.addStretch()
        filter_area.addLayout(row3)
        self.content_layout.addLayout(filter_area)

        headers = ["試劑名稱", "RID", "批號", "穩定效期", "入庫日期", "狀態", "出庫時間"]
        self.table = self.make_table(headers)
        self.content_layout.addWidget(self.table)

    def _update_reagents(self):
        """根據廠商連動更新試劑清單。"""
        vendor_id = self.cb_vendor.currentData()
        self.cb_reagent.clear()
        self.cb_reagent.addItem("全部", None)
        
        reagents = ReagentModel.get_all(vendor_id=vendor_id)
        for r in reagents:
            self.cb_reagent.addItem(r["reagent_name"], r["reagent_id"])

    def _search(self):
        issue_from = self.f_issue_from.date().toPyDate() if self.chk_issue_date.isChecked() else None
        issue_to = self.f_issue_to.date().toPyDate() if self.chk_issue_date.isChecked() else None
        
        rows = InventoryModel.trace_query(
            vendor_id=self.cb_vendor.currentData(),
            reagent_id=self.cb_reagent.currentData(),
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
                inv["expiry_date"].strftime("%Y / %m / %d") if inv["expiry_date"] else "",
                inv["received_date"].strftime("%Y / %m / %d") if inv["received_date"] else "",
                status_map.get(inv["status"], "?"),
                inv["issued_at"].strftime("%Y / %m / %d %H:%M") if inv["issued_at"] else "",
            ]):
                self.table.setItem(r, c_idx, QTableWidgetItem(val))

    def _export_csv(self):
        if not self._last_results:
            self.warn( "提示", "請先進行查詢再匯出資料")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "匯出 CSV", f"庫存追蹤_{QDate.currentDate().toString('yyyyMMdd')}.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            status_map = {0: "在庫", 1: "已出庫", 2: "已調整刪除"}
            receive_modes = {1: "一般入庫", 2: "廠商還貨", 3: "體系轉入"}
            issue_modes = {1: "一般領用", 2: "過期報廢", 3: "其他調整"}
            
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 重新排列欄位：依據入庫 -> 出庫的進程
                headers = [
                    "試劑名稱", "RID", "廠商", "批號", "穩定效期", 
                    "入庫日期", "入庫模式", "入庫人員", 
                    "狀態", "出庫日期", "出庫模式", "出庫人員"
                ]
                writer.writerow(headers)
                
                for inv in self._last_results:
                    writer.writerow([
                        inv["reagent_name"],
                        inv["rid"],
                        inv["vendor_name"],
                        inv["lot_number"],
                        str(inv["expiry_date"]),
                        str(inv["received_date"]),
                        receive_modes.get(inv["receive_mode"], "未知"),
                        inv.get("received_by_name", ""),
                        status_map.get(inv["status"], "?"),
                        str(inv["issued_at"]) if inv["issued_at"] else "",
                        issue_modes.get(inv["issue_mode"], "") if inv["issued_at"] else "",
                        inv.get("issued_by_name", ""),
                    ])
            self.alert("匯出成功", f"資料已成功儲存至：\n{path}")
        except Exception as e:
            self.warn("匯出失敗", str(e))

    def _print_label(self):
        row = self.table.currentRow()
        if row < 0:
            self.warn("未選取資料", "請先點選表格中想要補印的試劑資料列。")
            return
            
        # 取得選定行的原始資料
        item = self._last_results[row]
        
        dlg = PrintLabelDialog(item, self)
        if dlg.exec():
            sel = dlg.get_selection()
            try:
                if sel["type"] == "receive":
                    if sel["format"] == "text":
                        print_receive_label_large(
                            item["rid"], item["reagent_name"], item["lot_number"],
                            str(item["expiry_date"]), str(item["received_date"])
                        )
                    else:
                        print_receive_label_qr(
                            item["rid"], item["reagent_name"], item["lot_number"],
                            str(item["expiry_date"]), str(item["received_date"])
                        )
                else:
                    # 出庫標籤
                    if sel["format"] == "text":
                        print_issue_label_large(
                            item["rid"], item["reagent_name"], item["lot_number"],
                            str(item["open_expiry_date"]), str(item.get("issued_at", "")),
                            item.get("issued_by_name", "N/A")
                        )
                    else:
                        print_issue_label_qr(
                            item["rid"], item["reagent_name"], item["lot_number"],
                            str(item["open_expiry_date"]), str(item.get("issued_at", "")),
                            item.get("issued_by_name", "N/A")
                        )
                self.alert("列印指令已送出", f"正在補印 RID: {item['rid']} 的{ '出庫' if sel['type']=='issue' else '入庫'}標籤。")
            except Exception as e:
                self.warn("列印失敗", f"傳送列印指令時發生錯誤：\n{str(e)}")
