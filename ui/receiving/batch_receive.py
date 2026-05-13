# ui/receiving/batch_receive.py — 整批入庫頁面（掃描訂購單條碼）

from datetime import date
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSpinBox, QDateEdit,
    QComboBox, QCheckBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QWidget, QButtonGroup
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QIntValidator
from ui.base_page import BasePage
from database.models.inventory import InventoryModel
from database.models.purchase_order import PurchaseOrderModel
from database.models.reagent import ReagentModel
from services.rid_generator import generate_rid
from services.label_printer import (
    print_receive_label_large, print_receive_label_qr,
    print_receive_batch_qr
)

RECEIVE_MODES = {1: "一般入庫", 2: "廠商還貨", 3: "體系轉入"}


class BatchReceivePage(BasePage):
    def __init__(self, user: dict):
        super().__init__("整批入庫", "掃描訂購單條碼後批次確認入庫", user)
        self._po = None
        self._po_items = []
        self._build()

    def _build(self):
        # ── 掃描區 ──
        scan_card = QFrame()
        scan_card.setObjectName("section_card")
        scan_layout = QHBoxLayout(scan_card)

        scan_layout.addWidget(QLabel("訂購單條碼："))
        self.f_po_code = QLineEdit()
        self.f_po_code.setPlaceholderText("請掃描或輸入訂購單條碼（PO+yyyyMMDD+XX）")
        self.f_po_code.setMinimumWidth(320)
        self.f_po_code.returnPressed.connect(self._load_po)
        scan_layout.addWidget(self.f_po_code)

        btn_scan = QPushButton("查詢")
        btn_scan.setObjectName("btn_primary")
        btn_scan.clicked.connect(self._load_po)
        scan_layout.addWidget(btn_scan)

        self.lbl_po_info = QLabel("")
        self.lbl_po_info.setStyleSheet("color:#60c0ff; font-size:13px;")
        scan_layout.addWidget(self.lbl_po_info)
        scan_layout.addStretch()
        self.content_layout.addWidget(scan_card)

        # ── 入庫明細表格 ──
        lbl = QLabel("訂購單明細（可修改入庫數量、批號、效期）")
        lbl.setStyleSheet("color:#7ea8c9; font-size:12px;")
        self.content_layout.addWidget(lbl)

        headers = ["試劑名稱", "料號", "訂購數量", "入庫數量", "批號", "穩定效期"]
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # 平均分配所有欄寬
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # 設定預設行高
        self.table.verticalHeader().setDefaultSectionSize(45)
        
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "alternate-background-color: #131c2a; background:#111b28; "
            "border:1px solid #1e2d42; border-radius:6px; "
            "color:#c0d8f0; gridline-color:#1e2d42; font-size: 13px;"
        )
        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section{background:#1a2535; color:#7ea8c9; "
            "border:none; border-right:1px solid #2d4060; "
            "border-bottom:1px solid #2d4060; padding:8px 10px;}"
        )
        self.table.verticalHeader().setVisible(False)
        self.content_layout.addWidget(self.table)

        # ── 設定 & 確認列 ──
        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("入庫模式："))
        self.cb_mode = QComboBox()
        for k, v in RECEIVE_MODES.items():
            self.cb_mode.addItem(v, k)
        bottom.addWidget(self.cb_mode)

        self.chk_large = QCheckBox("列印一般標籤")
        self.chk_large.setChecked(True)
        self.chk_large.setStyleSheet("color:#a0c0dc;")
        self.chk_qr = QCheckBox("列印 QR Code 標籤")
        self.chk_qr.setStyleSheet("color:#a0c0dc;")

        # 使標籤選項互斥
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.chk_large)
        self.btn_group.addButton(self.chk_qr)
        self.btn_group.setExclusive(True)

        bottom.addWidget(self.chk_large)
        bottom.addWidget(self.chk_qr)
        bottom.addStretch()

        self.btn_confirm = QPushButton("✔  確認整批入庫")
        self.btn_confirm.setObjectName("btn_primary")
        self.btn_confirm.clicked.connect(self._do_batch_receive)
        bottom.addWidget(self.btn_confirm)
        self.content_layout.addLayout(bottom)

    def _load_po(self):
        code = self.f_po_code.text().strip().upper()
        if not code:
            return
        po = PurchaseOrderModel.get_by_code(code)
        if not po:
            self.warn(self, "查無資料", f"找不到訂購單：{code}")
            return

        self._po = po
        if po["status"] == 2:
            recv_date = str(po.get("received_date") or "未知日期")
            self.lbl_po_info.setText(
                f"⚠️ <b style='color:#ff6b6b;'>此單已於 {recv_date} 入庫完成，禁止重複入庫</b>"
            )
            self.btn_confirm.setEnabled(False)
            self.btn_confirm.setToolTip("此單據已完成入庫")
        else:
            self.lbl_po_info.setText(
                f"廠商：{po['vendor_name']}  |  組別：{po['dept_name']}  |  "
                f"建立時間：{po['created_at']}"
            )
            self.btn_confirm.setEnabled(True)
            self.btn_confirm.setToolTip("")

        items = PurchaseOrderModel.get_items(po["po_id"])
        self._po_items = items
        self.table.setRowCount(0)

        for r, item in enumerate(items):
            self.table.insertRow(r)
            self.table.setRowHeight(r, 45) # 強制行高

            # 試劑名稱、料號、訂購數量（唯讀）
            for c_idx, val in enumerate([
                item["reagent_name"], 
                item["item_number"] or "",
                str(item["ordered_qty"])
            ]):
                it = QTableWidgetItem(str(val))
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(r, c_idx, it)

            # ── 共通樣式 ──
            input_style = (
                "background: transparent; border: none; "
                "color:#d0e8ff; selection-background-color: #3d5a80; "
                "font-size: 13px; padding: 0px;"
            )

            # 1. 入庫數量 (QLineEdit + IntValidator)
            e_qty = QLineEdit(str(item["ordered_qty"]))
            e_qty.setValidator(QIntValidator(0, 9999))
            e_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_qty.setFixedHeight(32)
            e_qty.setStyleSheet(input_style)
            
            c_qty = QWidget(); l_qty = QHBoxLayout(c_qty)
            l_qty.addWidget(e_qty); l_qty.setContentsMargins(5,0,5,0); l_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(r, 3, c_qty)

            # 2. 批號 (QLineEdit)
            e_lot = QLineEdit("")
            e_lot.setPlaceholderText("請輸入批號")
            e_lot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e_lot.setFixedHeight(32)
            e_lot.setStyleSheet(input_style)
            
            c_lot = QWidget(); l_lot = QHBoxLayout(c_lot)
            l_lot.addWidget(e_lot); l_lot.setContentsMargins(5,0,5,0); l_lot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(r, 4, c_lot)

            # 3. 穩定效期 (QLineEdit + yyyy-MM-dd)
            # 使用 QDateEdit 但包裝在容器中，並調整為簡約樣式
            de = QDateEdit()
            de.setCalendarPopup(True)
            de.setDate(QDate.currentDate().addMonths(6))
            de.setDisplayFormat("yyyy-MM-dd")
            de.setAlignment(Qt.AlignmentFlag.AlignCenter)
            de.setFixedHeight(32)
            de.setStyleSheet(input_style + "background: #1a2535; border-radius: 4px;") # 日期保留一點背景以便識別
            
            c_de = QWidget(); l_de = QHBoxLayout(c_de)
            l_de.addWidget(de); l_de.setContentsMargins(5,0,5,0); l_de.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(r, 5, c_de)

    def _do_batch_receive(self):
        if not self._po:
            self.warn(self, "提示", "請先掃描訂購單條碼")
            return

        try:
            mode = self.cb_mode.currentData()
            today = date.today()
            today_str = today.isoformat()
            total = 0

            for r in range(self.table.rowCount()):
                item = self._po_items[r]
                reagent_id = item["reagent_id"]
                reagent_name = item["reagent_name"]

                # 讀取容器中的數值
                c_qty = self.table.cellWidget(r, 3); e_qty = c_qty.findChild(QLineEdit)
                try:
                    qty = int(float(e_qty.text() or 0)) if e_qty else 0
                except ValueError:
                    qty = 0
                
                if qty == 0:
                    continue

                c_lot = self.table.cellWidget(r, 4); e_lot = c_lot.findChild(QLineEdit)
                lot_number = e_lot.text().strip() if e_lot else ""
                if not lot_number:
                    self.warn(self, "驗證", f"請填寫「{reagent_name}」的批號")
                    return

                c_de = self.table.cellWidget(r, 5); de = c_de.findChild(QDateEdit)
                expiry = de.date().toPyDate() if de else today
                expiry_str = expiry.isoformat()

                # 批號/效期警示
                if InventoryModel.check_lot_duplicate(reagent_id, lot_number):
                    if not self.confirm(self, "批號警示",
                                        f"「{reagent_name}」批號「{lot_number}」曾使用過，繼續嗎？"):
                        continue
                if InventoryModel.check_expiry_earlier(reagent_id, expiry):
                    if not self.confirm(self, "效期警示",
                                        f"「{reagent_name}」新批號效期比現有庫存更早，繼續嗎？"):
                        continue

                for _ in range(qty):
                    rid = generate_rid()
                    InventoryModel.insert(
                        rid=rid, reagent_id=reagent_id, lot_number=lot_number,
                        expiry_date=expiry, received_date=today,
                        received_by=self.user["user_id"], receive_mode=mode,
                        po_id=self._po["po_id"],
                    )
                    # 列印標籤
                    if self.chk_large.isChecked():
                        try:
                            print_receive_label_large(rid, reagent_name, lot_number, expiry_str, today_str)
                        except Exception as e:
                            self.warn(self, "列印錯誤", f"一般標籤列印失敗：{str(e)}")

                    if self.chk_qr.isChecked():
                        qr_print_queue.append({
                            "rid": rid, "name": reagent_name, "lot": lot_number,
                            "exp": expiry_str, "recv": today_str, "is_new": False
                        })

                PurchaseOrderModel.update_received_qty(item["po_item_id"], qty)
                total += qty

            # 執行批次 QR 列印
            if qr_print_queue:
                try:
                    print_receive_batch_qr(qr_print_queue)
                except Exception as e:
                    self.warn(self, "列印錯誤", f"QR Code 批次列印失敗：{str(e)}")

            if total > 0:
                PurchaseOrderModel.set_status(self._po["po_id"], 2)
                self.alert(self, "整批入庫完成", f"共入庫 {total} 瓶")
                self.table.setRowCount(0)
                self._po = None
                self.f_po_code.clear()
                self.lbl_po_info.setText("")
            else:
                self.warn(self, "提示", "未輸入任何入庫數量")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.warn(self, "系統錯誤", f"入庫過程中發生錯誤，請截圖給開發者：\n{str(e)}\n\n{error_details}")
