# ui/receiving/manual_receive.py — 手工入庫頁面

from datetime import date
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDateEdit, QSpinBox,
    QFrame, QMessageBox, QCheckBox, QTableWidgetItem, QButtonGroup
)
from PyQt6.QtCore import QDate, Qt, QObject, QEvent
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

        # ── 入庫表單 (使用 Grid 以達成上下對齊) ──
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.setContentsMargins(10, 10, 10, 10)

        # 第一排
        grid.addWidget(QLabel("廠商 *"), 0, 0)
        self.cb_vendor = QComboBox()
        self.cb_vendor.setMinimumWidth(180)
        self.cb_vendor.addItem("— 請選擇廠商 —", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        self.cb_vendor.currentIndexChanged.connect(self._load_reagents)
        grid.addWidget(self.cb_vendor, 0, 1)

        grid.addWidget(QLabel("試劑 *"), 0, 2)
        self.cb_reagent = QComboBox()
        self.cb_reagent.setMinimumWidth(240)
        self._load_reagents()
        grid.addWidget(self.cb_reagent, 0, 3)

        grid.addWidget(QLabel("批號 *"), 0, 4)
        self.f_lot = QLineEdit()
        self.f_lot.setPlaceholderText("請輸入批號")
        self.f_lot.setMaxLength(50)
        self.f_lot.setMinimumWidth(180)
        grid.addWidget(self.f_lot, 0, 5)

        # 第二排
        grid.addWidget(QLabel("穩定效期 *"), 1, 0)
        self.f_expiry = QDateEdit()
        self.f_expiry.setCalendarPopup(True)
        self.f_expiry.setDate(QDate.currentDate().addMonths(6))
        self.f_expiry.setDisplayFormat("yyyy / MM / dd")
        self.f_expiry.setFixedWidth(200)
        grid.addWidget(self.f_expiry, 1, 1)

        grid.addWidget(QLabel("數量（瓶） *"), 1, 2)
        self.f_qty = QSpinBox()
        self.f_qty.setRange(1, 999)
        self.f_qty.setValue(1)
        self.f_qty.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.f_qty.setMinimumWidth(240)
        grid.addWidget(self.f_qty, 1, 3)

        grid.addWidget(QLabel("入庫模式"), 1, 4)
        self.cb_mode = QComboBox()
        for k, v in RECEIVE_MODES.items():
            self.cb_mode.addItem(v, k)
        self.cb_mode.setMinimumWidth(180)
        grid.addWidget(self.cb_mode, 1, 5)

        # 第三排：列印選項與入庫按鈕
        self.chk_print_large = QCheckBox("列印一般標籤")
        self.chk_print_large.setChecked(True)
        # padding-left: 8px 讓文字與框框拉開一個字元左右的距離
        self.chk_print_large.setStyleSheet("color:#2D3436; padding-left: 8px; background: transparent;")
        
        self.chk_print_qr = QCheckBox("列印 QR Code 標籤")
        self.chk_print_qr.setStyleSheet("color:#2D3436; padding-left: 8px; background: transparent;")

        # 使標籤選項互斥
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.chk_print_large)
        self.btn_group.addButton(self.chk_print_qr)
        self.btn_group.setExclusive(True)

        grid.addWidget(self.chk_print_large, 2, 0, 1, 2)
        grid.addWidget(self.chk_print_qr, 2, 2, 1, 2)

        self.btn_receive = QPushButton("✔  確認入庫")
        self.btn_receive.setObjectName("btn_primary")
        self.btn_receive.clicked.connect(self._do_receive)
        self.btn_receive.setFixedWidth(180)
        grid.addWidget(self.btn_receive, 2, 5)

        card_layout.addLayout(grid)

        self.content_layout.addWidget(card)
        
        # ── 設定 Enter 鍵自動跳轉邏輯 ──
        # 下拉選單在使用者選擇選項 (滑鼠點擊或鍵盤 Enter) 時觸發
        self.cb_vendor.activated.connect(lambda: self.cb_reagent.setFocus())
        self.cb_reagent.activated.connect(lambda: self.f_lot.setFocus())
        # 輸入框與效期(LineEdit)在按下 Enter 時觸發
        self.f_lot.returnPressed.connect(lambda: self.f_expiry.setFocus())
        self.f_expiry.lineEdit().returnPressed.connect(lambda: self.f_qty.setFocus())

        # QSpinBox 與 QPushButton 對 Enter 鍵有內部攔截機制，使用 EventFilter 確保精準觸發
        class EnterJumpFilter(QObject):
            def __init__(self, target):
                super().__init__()
                self.target = target
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.target.setFocus()
                    return True
                return super().eventFilter(obj, event)

        class EnterClickFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    obj.click()
                    return True
                return super().eventFilter(obj, event)

        # 數量框按下 Enter -> 跳到確認按鈕
        self._qty_filter = EnterJumpFilter(self.btn_receive)
        self.f_qty.installEventFilter(self._qty_filter)
        
        # 按鈕獲得焦點時，按下 Enter -> 視同點擊
        self._btn_filter = EnterClickFilter()
        self.btn_receive.installEventFilter(self._btn_filter)

        # ── 本次入庫記錄 ──
        lbl = QLabel("本次入庫記錄")
        lbl.setStyleSheet("color:#2D3436; font-weight:bold; font-size:14px;")
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
            if not self.confirm("效期警告", "穩定效期已過 or 為今日，確定要入庫嗎？"):
                return

        # 批號重複警示
        if InventoryModel.check_lot_duplicate(reagent_id, lot_number):
            if not self.confirm("批號警示",
                                f"批號「{lot_number}」曾使用過，確定要入庫嗎？"):
                return

        # 效期比現存更早的警示
        if InventoryModel.check_expiry_earlier(reagent_id, expiry):
            if not self.confirm("效期警示",
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
                reply = self.confirm("列印詢問", "入庫數量為單數，最後一瓶要等待下一筆併案列印嗎？\n(點擊「是」則暫存，點擊「否」則立即印出單張)")
                if reply:
                    self._pending_qr = remaining
                    # self.alert("等待中", "最後一瓶標籤已暫存，請繼續下一筆入庫...") # 移除等待彈窗
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

        # self.alert("入庫完成", f"已入庫 {qty} 瓶，RID：{new_rows[0]}～{new_rows[-1]}") # 移除完成彈窗

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
