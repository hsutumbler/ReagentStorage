# ui/issuing/issue_dialog.py — 出庫頁面

from datetime import date, timedelta
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QCheckBox,
    QTableWidgetItem, QButtonGroup
)
from ui.base_page import BasePage
from database.models.inventory import InventoryModel
from services.label_printer import (
    print_issue_label_large, print_issue_label_qr,
    print_issue_batch_qr
)
from ui.receiving.label_preview import LabelPreviewDialog

ISSUE_MODES = {1: "一般出庫", 2: "廠商借貨", 3: "體系轉出"}


class IssuePage(BasePage):
    def __init__(self, user: dict):
        super().__init__("出庫", "掃描 RID 或 QR Code 進行出庫", user)
        self._current_item = None
        self._pending_qr = None  # 暫存待列印的 QR 資料
        self.content_layout.setSpacing(10) # 縮小垂直間距
        self._build()

    def on_page_show(self):
        """當導航切換至此頁面時執行。"""
        self.f_rid.setFocus()
        self.f_rid.selectAll()

    def _build(self):
        # ── 掃描區 ──
        scan_card = QFrame()
        scan_card.setObjectName("section_card")
        scan_layout = QHBoxLayout(scan_card)

        scan_layout.addWidget(QLabel("掃描 RID / QR Code："))
        self.f_rid = QLineEdit()
        self.f_rid.setPlaceholderText("請掃描或輸入 RID（如 R2506080001）")
        self.f_rid.setMinimumWidth(280)
        self.f_rid.returnPressed.connect(self._load_item)
        scan_layout.addWidget(self.f_rid)

        btn_search = QPushButton("查詢")
        btn_search.setObjectName("btn_primary")
        btn_search.clicked.connect(self._load_item)
        scan_layout.addWidget(btn_search)
        scan_layout.addStretch()
        self.content_layout.addWidget(scan_card)

        # ── 試劑資訊卡 ──
        info_card = QFrame()
        info_card.setObjectName("section_card")
        # 使用 QHBoxLayout 作為容器，內含兩個垂直佈局（左欄與右欄）
        info_main_layout = QHBoxLayout(info_card)
        info_main_layout.setContentsMargins(15, 10, 15, 10)
        
        col_left = QVBoxLayout()
        col_right = QVBoxLayout()
        col_left.setSpacing(8)
        col_right.setSpacing(8)

        self.lbl_name    = QLabel("試劑：—")
        self.lbl_rid     = QLabel("RID：—")
        self.lbl_lot     = QLabel("批號：—")
        self.lbl_expiry  = QLabel("穩定效期：—")
        self.lbl_open_exp = QLabel("開封效期：—")
        self.lbl_print_exp = QLabel("出庫日期：—")
        
        # 設定樣式並加入對應欄位
        label_style = "color:#2D3436; font-size:14px; font-weight:700;"
        for lbl in [self.lbl_name, self.lbl_rid, self.lbl_lot]:
            lbl.setStyleSheet(label_style)
            col_left.addWidget(lbl)
            
        for lbl in [self.lbl_expiry, self.lbl_open_exp, self.lbl_print_exp]:
            lbl.setStyleSheet(label_style)
            col_right.addWidget(lbl)

        info_main_layout.addLayout(col_left, 1)
        info_main_layout.addLayout(col_right, 1)
        
        self.lbl_warn = QLabel("")
        self.lbl_warn.setStyleSheet("color:#FF8C00; font-weight:bold; font-size:12px;")
        
        # 整個內容區塊包裝
        info_wrapper = QVBoxLayout()
        info_wrapper.setSpacing(2)
        info_wrapper.addWidget(info_card)
        info_wrapper.addWidget(self.lbl_warn)
        self.content_layout.addLayout(info_wrapper)

        # ── 出庫設定 & 確認 ──
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 5, 0, 10)
        bottom.addWidget(QLabel("出庫模式："))
        self.cb_mode = QComboBox()
        for k, v in ISSUE_MODES.items():
            self.cb_mode.addItem(v, k)
        bottom.addWidget(self.cb_mode)

        self.chk_large = QCheckBox("列印一般標籤")
        self.chk_large.setChecked(True)
        self.chk_large.setStyleSheet("color:#636E72;")
        self.chk_qr = QCheckBox("列印 QR Code 標籤")
        self.chk_qr.setStyleSheet("color:#636E72;")

        # 使標籤選項互斥
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.chk_large)
        self.btn_group.addButton(self.chk_qr)
        self.btn_group.setExclusive(True)

        bottom.addWidget(self.chk_large)
        bottom.addWidget(self.chk_qr)
        bottom.addStretch()

        btn_issue = QPushButton("✔  確認出庫")
        btn_issue.setObjectName("btn_primary")
        btn_issue.clicked.connect(self._do_issue)
        bottom.addWidget(btn_issue)

        self.content_layout.addLayout(bottom)

        # ── 本次出庫記錄 ──
        lbl = QLabel("本次出庫記錄")
        lbl.setStyleSheet("color:#2D3436; font-weight:bold; font-size:14px;")
        self.content_layout.addWidget(lbl)

        headers = ["RID", "試劑名稱", "批號", "穩定效期", "開封效期", "出庫日期", "出庫模式"]
        self.table = self.make_table(headers)
        self.content_layout.addWidget(self.table)

    def _load_item(self):
        raw = self.f_rid.text().strip()
        if not raw:
            return

        # QR Code 掃描內容可能是 "RID|名稱|批號|效期|日期"（或「出|...」）
        rid = self._parse_rid(raw)
        if not rid:
            self.warn( "格式錯誤", "無法解析條碼內容")
            return

        item = InventoryModel.get_by_rid(rid)
        if not item:
            self.warn( "查無資料", f"找不到 RID：{rid}")
            return
        if item["status"] != 0:
            status_map = {1: "已出庫", 2: "已調整刪除"}
            self.warn( "狀態錯誤",
                      f"此試劑已{status_map.get(item['status'], '異常')}，無法出庫")
            return

        self._current_item = item

        # 計算開封效期
        today = date.today()
        open_days = item["open_days"] or 0
        open_exp = today + timedelta(days=open_days)

        # 取較早效期用於標籤
        expiry = item["expiry_date"]
        print_exp = min(expiry, open_exp)

        # 更新顯示
        self.lbl_name.setText(f"試劑：{item['reagent_name']}")
        self.lbl_rid.setText(f"RID：{rid}")
        self.lbl_lot.setText(f"批號：{item['lot_number']}")
        self.lbl_expiry.setText(f"穩定效期：{expiry}")
        self.lbl_open_exp.setText(f"開封效期：{open_exp}")
        self.lbl_print_exp.setText(f"出庫日期：{print_exp}")

        # 效期警示
        warnings = []
        if expiry < open_exp:
            warnings.append("⚠ 穩定效期早於開封效期，標籤將列印穩定效期")

        # FEFO 檢查
        earlier = InventoryModel.check_fefo(rid)
        if earlier:
            warnings.append(
                f"⚠ 庫存中有 {len(earlier)} 瓶同試劑的效期更早，建議優先使用"
            )

        self.lbl_warn.setText("\n".join(warnings))

        # ── 主動詢問出庫 ──
        if earlier:
            # FEFO 警示：預設為「否」，防止誤出
            msg = (f"【FEFO 警示】庫存中有 {len(earlier)} 瓶同試劑效期更早：\n"
                   + "\n".join(f"  RID: {e['rid']}  效期: {e['expiry_date']}" for e in earlier[:3])
                   + "\n\n仍要強行出庫此瓶嗎？")
            reply = self.confirm("FEFO 提醒", msg, default_yes=False)
            if reply:
                self._do_issue()
            else:
                self.f_rid.setFocus()
                self.f_rid.selectAll()
        else:
            # 一般出庫：預設為「是」，按 Enter 即可完成
            reply = self.confirm("確認出庫", f"確定要出庫試劑：{item['reagent_name']} (RID: {rid}) 嗎？", default_yes=True)
            if reply:
                self._do_issue()
            else:
                self.f_rid.setFocus()
                self.f_rid.selectAll()

    def _parse_rid(self, raw: str) -> str | None:
        """從原始掃描字串解析出 RID。"""
        if raw.startswith("R") and len(raw) >= 9:
            return raw.split("|")[0]   # 可能是 QR code 多欄位，取第一段
        # 處理「出|RID|...」格式
        parts = raw.split("|")
        if parts[0] == "出" and len(parts) >= 2:
            return parts[1]
        if len(parts) >= 2 and parts[1].startswith("R"):
            return parts[1]
        return None

    def _do_issue(self):
        if not self._current_item:
            self.warn( "提示", "請先掃描試劑條碼")
            return

        item = self._current_item
        mode = self.cb_mode.currentData()
        today = date.today()
        today_str = today.isoformat()

        open_days = item["open_days"] or 0
        open_exp = today + timedelta(days=open_days)
        expiry = item["expiry_date"]
        print_exp = min(expiry, open_exp)

        InventoryModel.issue(
            inventory_id=item["inventory_id"],
            issued_by=self.user["user_id"],
            issue_mode=mode,
            open_expiry_date=open_exp,
            printed_expiry_date=print_exp,
        )

        rid = item["rid"]
        name = item["reagent_name"]
        lot = item["lot_number"]
        print_exp_str = print_exp.isoformat()

        # 一般標籤立即列印
        if self.chk_large.isChecked():
            try:
                print_issue_label_large(rid, name, lot, print_exp_str, today_str, self.user["name"])
            except Exception as e:
                self.warn( "列印錯誤", f"一般標籤列印失敗：{str(e)}")

        # QR Code 緩衝列印邏輯
        if self.chk_qr.isChecked():
            current_qr = {
                "rid": rid, "name": name, "lot": lot,
                "exp": print_exp_str, "recv": today_str,
                "by": self.user["name"]
            }
            
            if self._pending_qr:
                # 已有待列印項，直接湊成一對印出
                try:
                    print_issue_batch_qr([self._pending_qr, current_qr])
                    self._pending_qr = None
                except Exception as e:
                    self.warn( "列印錯誤", str(e))
            else:
                # 第一瓶，詢問是否等下一瓶
                reply = self.confirm("列印詢問", "是否有下一瓶 QR 要出庫？\n(點擊「是」將等待下一瓶併案列印，點擊「否」則立即印出單張)")
                if reply:
                    self._pending_qr = current_qr
                    self.alert("等待中", "已暫存標籤資訊，請掃描下一瓶試劑...")
                else:
                    try:
                        print_issue_label_qr(rid, name, lot, print_exp_str, today_str, self.user["name"])
                    except Exception as e:
                        self.warn( "列印錯誤", str(e))

        # 加入記錄表格
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c_idx, val in enumerate([
            rid, name, lot, str(expiry), str(open_exp), today_str,
            ISSUE_MODES.get(mode, ""),
        ]):
            self.table.setItem(r, c_idx, QTableWidgetItem(val))

        self._current_item = None
        self.f_rid.clear()
        self.lbl_name.setText("試劑：—")
        self.lbl_rid.setText("RID：—")
        self.lbl_lot.setText("批號：—")
        self.lbl_expiry.setText("穩定效期：—")
        self.lbl_open_exp.setText("開封效期：—")
        self.lbl_print_exp.setText("出庫日期：—")
        self.lbl_warn.setText("")
        self.alert("出庫完成", f"RID {rid} 出庫成功")
        
        # 游標回到輸入框並全選，方便下一筆掃描
        self.f_rid.setFocus()
        self.f_rid.selectAll()

    def _show_preview(self):
        if not self._current_item:
            self.warn( "提示", "請先掃描試劑條碼以進行預覽")
            return
        
        item = self._current_item
        today = date.today()
        open_days = item["open_days"] or 0
        open_exp = today + timedelta(days=open_days)
        expiry = item["expiry_date"]
        print_exp = min(expiry, open_exp)
        
        dlg = LabelPreviewDialog(
            self, item["reagent_name"], item["lot_number"], 
            print_exp.isoformat(), is_issue=True
        )
        dlg.exec()
