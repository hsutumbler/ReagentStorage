# ui/receiving/batch_receive.py — 整批入庫頁面（掃描訂購單條碼）

from datetime import date
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QSpinBox, QDateEdit,
    QComboBox, QCheckBox, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QWidget, QButtonGroup
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QIntValidator, QIcon
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
        self.lbl_po_info.setStyleSheet("color:#0066CC; font-size:13px;")
        scan_layout.addWidget(self.lbl_po_info)
        scan_layout.addStretch()
        self.content_layout.addWidget(scan_card)

        # ── 入庫明細表格 ──
        lbl = QLabel("訂購單明細（可修改入庫數量、批號、效期）")
        lbl.setStyleSheet("color:#2D3436; font-weight:bold; font-size:14px;")
        self.content_layout.addWidget(lbl)

        headers = ["試劑名稱", "料號", "訂購數量", "入庫數量", "批號", "穩定效期", "操作"]
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # 平均分配所有欄寬，但操作欄固定
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 90)
        
        # 設定預設行高
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "alternate-background-color: #FDFBF7; background:#FFFFFF; "
            "border:1px solid #DEE2E6; border-radius:6px; "
            "color:#2D3436; gridline-color:#DEE2E6; font-size: 13px;"
        )
        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section{background:#F1F3F5; color:#2D3436; "
            "border:none; border-right:1px solid #DEE2E6; "
            "border-bottom:1px solid #DEE2E6; padding:8px 10px;}"
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
        self.chk_large.setStyleSheet("color:#636E72;")
        self.chk_qr = QCheckBox("列印 QR Code 標籤")
        self.chk_qr.setStyleSheet("color:#636E72;")

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
            self.warn("查無資料", f"找不到訂購單：{code}")
            return

        self._po = po
        if po["status"] == 2:
            recv_date = str(po.get("received_date") or "未知日期")
            self.lbl_po_info.setText(
                f"⚠️ <b style='color:#ff6b6b;'>此訂購單 ({code}) 已於 {recv_date} 全數入庫結案</b>"
            )
        elif po["status"] == 1:
            self.lbl_po_info.setText(
                f"⚠️ <b style='color:#ff9f43;'>此訂購單 ({code}) 為「部分入庫」狀態，請繼續補齊剩餘試劑</b>"
            )
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

        for item in items:
            ordered = item["ordered_qty"]
            received = item.get("received_qty") or 0
            
            # 如果已有入庫紀錄，先產生一行唯讀的歷史紀錄
            if received > 0:
                self._add_item_row(item, received, is_readonly=True, lot=item.get("lot_number") or "", exp=item.get("expiry_date"))
            
            # 如果還沒收滿，且未結案，產生待收數量行
            if po["status"] != 2 and received < ordered:
                self._add_item_row(item, ordered - received, is_readonly=False)
                
            # 若為 status=2 但 received=0 (可能是被強制結案的品項)，補上一行空的唯讀紀錄避免畫面留白
            if po["status"] == 2 and received == 0:
                self._add_item_row(item, 0, is_readonly=True)

    def _add_item_row(self, item, qty, is_readonly, lot="", exp=None):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setRowHeight(r, 45)

        # 試劑名稱、料號、訂購數量（唯讀）
        for c_idx, val in enumerate([
            item["reagent_name"], 
            item["item_number"] or "",
            str(item["ordered_qty"])
        ]):
            it = QTableWidgetItem(str(val))
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if c_idx == 0:
                # 關鍵：將 item 綁定在第一格，解開行號限制
                it.setData(Qt.ItemDataRole.UserRole, item)
            self.table.setItem(r, c_idx, it)

        input_style = """
            QLineEdit, QDateEdit {
                background: transparent;
                border: none;
                outline: none;
                color: #2D3436;
                font-size: 14px;
                padding: 0px;
                margin: 0px;
            }
            QLineEdit:hover, QDateEdit:hover { background: rgba(0, 0, 0, 0.03); }
            QLineEdit:focus, QDateEdit:focus {
                background: rgba(255, 255, 255, 0.8);
                border-bottom: 2px solid #0066CC;
            }
        """

        # 1. 入庫數量
        e_qty = QLineEdit(str(qty))
        e_qty.setValidator(QIntValidator(0, 9999))
        e_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_qty.setStyleSheet(input_style)
        e_qty.setFixedHeight(45)
        if is_readonly:
            e_qty.setReadOnly(True)
        self.table.setCellWidget(r, 3, e_qty)

        # 2. 批號
        e_lot = QLineEdit(lot)
        if not is_readonly and not lot:
            e_lot.setPlaceholderText("請輸入批號")
        e_lot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_lot.setStyleSheet(input_style)
        e_lot.setFixedHeight(45)
        if is_readonly:
            e_lot.setReadOnly(True)
        self.table.setCellWidget(r, 4, e_lot)

        # 3. 穩定效期
        de = QDateEdit()
        de.setDisplayFormat("yyyy / MM / dd")
        de.setAlignment(Qt.AlignmentFlag.AlignCenter)
        de.setStyleSheet(input_style + "QDateEdit::drop-down { width: 0px; border: none; }")
        de.setFixedHeight(45)
        if exp:
            if isinstance(exp, date):
                de.setDate(exp)
            else:
                de.setDate(QDate.fromString(str(exp), Qt.DateFormat.ISODate))
        else:
            de.setCalendarPopup(True)
            de.setDate(QDate.currentDate().addMonths(6))
            
        if is_readonly:
            de.setReadOnly(True)
            de.setButtonSymbols(QDateEdit.ButtonSymbols.NoButtons)
        self.table.setCellWidget(r, 5, de)
        
        # 4. 操作 (拆分按鈕)
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not is_readonly:
            btn_split = QPushButton("➕ 拆分")
            btn_split.setStyleSheet("""
                QPushButton { color: #0066CC; font-weight: bold; border: none; background: transparent; }
                QPushButton:hover { background: rgba(0, 102, 204, 0.1); border-radius: 4px; }
            """)
            btn_split.clicked.connect(lambda _, current_item=item: self._split_row(current_item))
            action_layout.addWidget(btn_split)
        else:
            lbl_history = QLabel("歷史紀錄")
            lbl_history.setStyleSheet("color: #B2BEC3; font-size: 12px;")
            action_layout.addWidget(lbl_history)
            
        self.table.setCellWidget(r, 6, action_widget)

    def _split_row(self, item):
        # 找到被點擊按鈕所屬的 item，在表格最後新增一行
        self._add_item_row(item, 0, is_readonly=False)

    def _do_batch_receive(self):
        if not self._po:
            self.warn("提示", "請先掃描訂購單條碼")
            return

        if self._po["status"] == 2:
            code = self._po["po_code"]
            self.warn("重複入庫", f"此訂購單 ({code}) 已全數入庫結案，禁止修改！")
            return

        try:
            mode = self.cb_mode.currentData()
            today = date.today()
            today_str = today.isoformat()
            
            # 統計各品項本次預計入庫量
            received_summary = {}
            for item in self._po_items:
                received_summary[item["po_item_id"]] = 0
                
            total_items_to_insert = []

            for r in range(self.table.rowCount()):
                # 從第一格取出綁定的 item 資料
                it = self.table.item(r, 0)
                item = it.data(Qt.ItemDataRole.UserRole)
                po_item_id = item["po_item_id"]
                reagent_id = item["reagent_id"]
                reagent_name = item["reagent_name"]

                e_qty = self.table.cellWidget(r, 3)
                if e_qty.isReadOnly(): # 跳過唯讀的歷史紀錄
                    continue
                    
                try:
                    qty = int(float(e_qty.text() or 0))
                except ValueError:
                    qty = 0
                
                if qty == 0:
                    continue

                e_lot = self.table.cellWidget(r, 4)
                lot_number = e_lot.text().strip()
                if not lot_number:
                    self.warn("驗證", f"請填寫「{reagent_name}」的批號")
                    return

                de = self.table.cellWidget(r, 5)
                expiry = de.date().toPyDate()
                expiry_str = expiry.isoformat()

                if InventoryModel.check_lot_duplicate(reagent_id, lot_number):
                    if not self.confirm("批號警示", f"試劑「{reagent_name}」的批號「{lot_number}」曾使用過，確定要繼續嗎？"):
                        continue
                if InventoryModel.check_expiry_earlier(reagent_id, expiry):
                    if not self.confirm("效期警示", f"試劑「{reagent_name}」的新效期比現有庫存更早，確定要繼續嗎？"):
                        continue

                received_summary[po_item_id] += qty
                total_items_to_insert.append({
                    "qty": qty, "reagent_id": reagent_id, "reagent_name": reagent_name,
                    "lot": lot_number, "exp": expiry, "exp_str": expiry_str
                })
            
            if not total_items_to_insert:
                self.warn("提示", "未輸入任何入庫數量")
                return

            # 短交判斷：檢查是否所有品項都達到總訂購量
            is_short = False
            for item in self._po_items:
                total_acc = (item.get("received_qty") or 0) + received_summary[item["po_item_id"]]
                if total_acc < item["ordered_qty"]:
                    is_short = True
                    break
                    
            final_status = 2 # 預設結案
            if is_short:
                # 彈窗詢問
                reply = QMessageBox.question(
                    self, "短交確認", 
                    "⚠️ 系統偵測到本次入庫後，總數量仍小於訂單需求量。\n\n請問剩餘的試劑後續還會到貨嗎？\n\n(選擇 Yes 表示還會到貨，選擇 No 則強制結案不再收貨)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    final_status = 1 # 部分入庫，留待下次
                else:
                    final_status = 2 # 強制結案

            # 開始執行寫入
            qr_print_queue = []
            total_bottles = 0
            for row_data in total_items_to_insert:
                for _ in range(row_data["qty"]):
                    rid = generate_rid()
                    InventoryModel.insert(
                        rid=rid, reagent_id=row_data["reagent_id"], lot_number=row_data["lot"],
                        expiry_date=row_data["exp"], received_date=today,
                        received_by=self.user["user_id"], receive_mode=mode,
                        po_id=self._po["po_id"],
                    )
                    
                    if self.chk_large.isChecked():
                        try:
                            print_receive_label_large(rid, row_data["reagent_name"], row_data["lot"], row_data["exp_str"], today_str)
                        except Exception as e:
                            self.warn("列印錯誤", f"一般標籤列印失敗：{str(e)}")

                    if self.chk_qr.isChecked():
                        qr_print_queue.append({
                            "rid": rid, "name": row_data["reagent_name"], "lot": row_data["lot"],
                            "exp": row_data["exp_str"], "recv": today_str, "is_new": False
                        })
                total_bottles += row_data["qty"]

            # 更新各品項已入庫量
            for item in self._po_items:
                new_total = (item.get("received_qty") or 0) + received_summary[item["po_item_id"]]
                PurchaseOrderModel.update_received_qty(item["po_item_id"], new_total)

            if qr_print_queue:
                try:
                    print_receive_batch_qr(qr_print_queue)
                except Exception as e:
                    self.warn("列印錯誤", f"QR Code 批次列印失敗：{str(e)}")

            PurchaseOrderModel.set_status(self._po["po_id"], final_status)
            status_text = "部分入庫完成" if final_status == 1 else "整批入庫完成 (已結案)"
            self.alert(status_text, f"共入庫 {total_bottles} 瓶")
            
            self.table.setRowCount(0)
            self._po = None
            self.f_po_code.clear()
            self.lbl_po_info.setText("")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.warn("系統錯誤", f"入庫過程中發生錯誤，請截圖給開發者：\n{str(e)}\n\n{error_details}")
