# ui/receiving/manual_receive.py — 手工入庫頁面

from datetime import date
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDateEdit, QSpinBox,
    QFrame, QMessageBox, QCheckBox, QTableWidgetItem, QButtonGroup
)
from PyQt6.QtCore import QDate
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.inventory import InventoryModel
from services.rid_generator import generate_rid
from services.label_printer import (
    print_receive_label_large, print_receive_label_qr,
    print_receive_batch_qr
)
from ui.receiving.label_preview import LabelPreviewDialog

RECEIVE_MODES = {1: "一般入庫", 2: "廠商還貨", 3: "體系轉入"}


class ManualReceivePage(BasePage):
    def __init__(self, user: dict):
        super().__init__("手工入庫", "逐筆輸入試劑資料進行入庫", user)
        self._pending_qr = None
        self._build()

    def _build(self):
        # ── 入庫表單 ──
        card = QFrame()
        card.setObjectName("section_card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("廠商 *"))
        self.cb_vendor = QComboBox()
        self.cb_vendor.setMinimumWidth(180)
        self.cb_vendor.addItem("— 請選擇廠商 —", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        self.cb_vendor.currentIndexChanged.connect(self._load_reagents)
        row1.addWidget(self.cb_vendor)

        row1.addWidget(QLabel("試劑 *"))
        self.cb_reagent = QComboBox()
        self.cb_reagent.setMinimumWidth(240)
        self._load_reagents()
        row1.addWidget(self.cb_reagent)

        row1.addWidget(QLabel("批號 *"))
        self.f_lot = QLineEdit()
        self.f_lot.setPlaceholderText("請輸入批號")
        self.f_lot.setMaxLength(50)
        row1.addWidget(self.f_lot)
        row1.addStretch()
        card_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("穩定效期 *"))
        self.f_expiry = QDateEdit()
        self.f_expiry.setCalendarPopup(True)
        self.f_expiry.setDate(QDate.currentDate().addMonths(6))
        self.f_expiry.setDisplayFormat("yyyy-MM-dd")
        row2.addWidget(self.f_expiry)

        row2.addWidget(QLabel("數量（瓶） *"))
        self.f_qty = QSpinBox()
        self.f_qty.setRange(1, 999)
        self.f_qty.setValue(1)
        self.f_qty.setStyleSheet(
            "background:#1a2535; border:1px solid #2d4060; border-radius:6px; "
            "color:#d0e8ff; padding:7px 10px;"
        )
        row2.addWidget(self.f_qty)

        row2.addWidget(QLabel("入庫模式"))
        self.cb_mode = QComboBox()
        for k, v in RECEIVE_MODES.items():
            self.cb_mode.addItem(v, k)
        row2.addWidget(self.cb_mode)
        row2.addStretch()
        card_layout.addLayout(row2)

        # 列印選項
        print_row = QHBoxLayout()
        self.chk_print_large = QCheckBox("列印一般標籤")
        self.chk_print_large.setChecked(True)
        self.chk_print_large.setStyleSheet("color:#a0c0dc;")
        self.chk_print_qr = QCheckBox("列印 QR Code 標籤")
        self.chk_print_qr.setStyleSheet("color:#a0c0dc;")

        # 使標籤選項互斥
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.chk_print_large)
        self.btn_group.addButton(self.chk_print_qr)
        self.btn_group.setExclusive(True)

        print_row.addWidget(self.chk_print_large)
        print_row.addWidget(self.chk_print_qr)
        
        print_row.addStretch()

        btn_receive = QPushButton("✔  確認入庫")
        btn_receive.setObjectName("btn_primary")
        btn_receive.clicked.connect(self._do_receive)
        print_row.addWidget(btn_receive)
        card_layout.addLayout(print_row)

        self.content_layout.addWidget(card)

        # ── 本次入庫記錄 ──
        lbl = QLabel("本次入庫記錄")
        lbl.setStyleSheet("color:#60c0ff; font-weight:bold; font-size:14px;")
        self.content_layout.addWidget(lbl)

        headers = ["RID", "試劑名稱", "批號", "穩定效期", "入庫日期", "入庫模式"]
        self.table = self.make_table(headers)
        self.content_layout.addWidget(self.table)

    def _load_reagents(self):
        vendor_id = self.cb_vendor.currentData()
        self.cb_reagent.clear()
        self.cb_reagent.addItem("— 請選擇試劑 —", None)
        
        reagents = ReagentModel.get_all()
        if vendor_id:
            reagents = [r for r in reagents if r["vendor_id"] == vendor_id]
        
        for r in reagents:
            label = r['reagent_name']
            self.cb_reagent.addItem(label, r["reagent_id"])

    def _do_receive(self):
        reagent_id = self.cb_reagent.currentData()
        lot_number = self.f_lot.text().strip()
        expiry = self.f_expiry.date().toPyDate()
        qty = self.f_qty.value()
        mode = self.cb_mode.currentData()

        if not reagent_id:
            self.warn( "驗證", "請選擇試劑")
            return
        if not lot_number:
            self.warn( "驗證", "請輸入批號")
            return
        if expiry <= date.today():
            if not self.confirm(self, "效期警告", "穩定效期已過或為今日，確定要入庫嗎？"):
                return

        # 批號重複警示
        if InventoryModel.check_lot_duplicate(reagent_id, lot_number):
            if not self.confirm(self, "批號警示",
                                f"批號「{lot_number}」曾使用過，確定要入庫嗎？"):
                return

        # 效期比現存更早的警示
        if InventoryModel.check_expiry_earlier(reagent_id, expiry):
            if not self.confirm(self, "效期警示",
                                "新批號的穩定效期比現有庫存更早，確定要入庫嗎？"):
                return

        # 檢查是否為新批號 (若資料庫中尚無此試劑的此批號，則為新批號)
        is_new_lot = not InventoryModel.check_lot_duplicate(reagent_id, lot_number)

        # 批次產生 RID 並入庫
        today_str = date.today().isoformat()
        new_rows = []
        for _ in range(qty):
            rid = generate_rid()
            InventoryModel.insert(
                rid=rid, reagent_id=reagent_id, lot_number=lot_number,
                expiry_date=expiry, received_date=date.today(),
                received_by=self.user["user_id"], receive_mode=mode,
            )
            new_rows.append(rid)

        # 取試劑名稱供列印
        reagent = ReagentModel.get_by_id(reagent_id)
        name = reagent["reagent_name"]
        expiry_str = expiry.isoformat()

        # 列印
        if self.chk_print_large.isChecked():
            for idx, rid in enumerate(new_rows):
                try:
                    # 只有該批次的第一張標籤標註「新批號」
                    print_receive_label_large(
                        rid, name, lot_number, expiry_str, today_str,
                        is_new_lot=(is_new_lot and idx == 0)
                    )
                except Exception as e:
                    self.warn( "列印錯誤", str(e))
                    break

        if self.chk_print_qr.isChecked():
            qr_queue = []
            for idx, rid in enumerate(new_rows):
                qr_queue.append({
                    "rid": rid, "name": name, "lot": lot_number,
                    "exp": expiry_str, "recv": today_str,
                    "is_new": (is_new_lot and idx == 0)
                })
            
            # 若有上次留下的暫存，接在最前面
            if self._pending_qr:
                qr_queue.insert(0, self._pending_qr)
                self._pending_qr = None

            # 兩兩成對列印
            while len(qr_queue) >= 2:
                pair = [qr_queue.pop(0), qr_queue.pop(0)]
                try:
                    print_receive_batch_qr(pair)
                except Exception as e:
                    self.warn( "列印錯誤", f"QR 批次列印失敗：{str(e)}")

            # 剩下最後一瓶（單數）
            if qr_queue:
                remaining = qr_queue[0]
                reply = self.confirm(self, "列印詢問", "入庫數量為單數，最後一瓶要等待下一筆併案列印嗎？\n(點擊「是」則暫存，點擊「否」則立即印出單張)")
                if reply:
                    self._pending_qr = remaining
                    self.alert(self, "等待中", "最後一瓶標籤已暫存，請繼續下一筆入庫...")
                else:
                    try:
                        print_receive_batch_qr([remaining])
                    except Exception as e:
                        self.warn( "列印錯誤", str(e))

        # 更新記錄表格
        mode_label = RECEIVE_MODES.get(mode, "")
        for rid in new_rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            for c_idx, val in enumerate([rid, name, lot_number, expiry_str, today_str, mode_label]):
                self.table.setItem(r, c_idx, QTableWidgetItem(val))

        self.alert(self, "入庫完成", f"已入庫 {qty} 瓶，RID：{new_rows[0]}～{new_rows[-1]}")

        # 清除表單
        self.f_lot.clear()
        self.f_qty.setValue(1)

    def _show_preview(self):
        reagent_id = self.cb_reagent.currentData()
        if not reagent_id:
            self.warn( "驗證", "請先選擇試劑以進行預覽")
            return
        
        reagent = ReagentModel.get_by_id(reagent_id)
        lot = self.f_lot.text().strip() or "LOT123456"
        expiry = self.f_expiry.date().toString("yyyy-MM-dd")
        
        dlg = LabelPreviewDialog(self, reagent["reagent_name"], lot, expiry)
        dlg.exec()
