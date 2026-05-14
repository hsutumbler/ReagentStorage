# ui/order/purchase_order.py — 試劑訂單頁面

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QFrame, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QWidget,
    QLineEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.purchase_order import PurchaseOrderModel
from database.models.inventory import InventoryModel
from services.rid_generator import generate_po_code
from services.label_printer import _send_zpl  # 直接用 ZPL 列印訂購單條碼


class PurchaseOrderPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("試劑訂單", "建立試劑訂購單並列印", user)
        self._reagents = []
        self._build()

    def _build(self):
        # ── 選廠商 & 組別 ──
        top = QHBoxLayout()
        top.addWidget(QLabel("廠商："))
        self.cb_vendor = QComboBox()
        self.cb_vendor.setMinimumWidth(200)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        top.addWidget(self.cb_vendor)

        top.addWidget(QLabel("組別："))
        self.cb_dept = QComboBox()
        self.cb_dept.setMinimumWidth(150)
        for d in ReagentModel.get_all_departments():
            self.cb_dept.addItem(d["dept_name"], d["dept_id"])
        top.addWidget(self.cb_dept)

        btn_load = QPushButton("載入試劑清單")
        btn_load.setObjectName("btn_primary")
        btn_load.clicked.connect(self._load_reagents)
        top.addWidget(btn_load)
        top.addStretch()
        self.content_layout.addLayout(top)

        # ── 訂購明細表格 ──
        headers = ["試劑名稱", "料號", "安全庫存", "目前庫存", "訂購數量"]
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # 平均分配五欄欄寬
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        
        from ui.base_page import CenterDelegate
        self.table.setItemDelegate(CenterDelegate(self.table))
        
        self.table.verticalHeader().setDefaultSectionSize(42) 
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            "alternate-background-color:#131c2a; background:#111b28; "
            "border:1px solid #1e2d42; border-radius:6px; "
            "color:#c0d8f0; gridline-color:#1e2d42; font-size: 13px;"
        )
        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section{background:#1a2535; color:#7ea8c9; "
            "border:none; border-right:1px solid #2d4060; "
            "border-bottom:1px solid #2d4060; padding:10px 5px;}"
        )
        self.content_layout.addWidget(self.table)

        # ── 底部操作 ──
        bottom = QHBoxLayout()
        bottom.addStretch()
        btn_save = QPushButton("💾  儲存並列印訂購單")
        btn_save.setObjectName("btn_primary")
        btn_save.clicked.connect(self._save_and_print)
        bottom.addWidget(btn_save)
        self.content_layout.addLayout(bottom)

    def _load_reagents(self):
        vendor_id = self.cb_vendor.currentData()
        dept_id = self.cb_dept.currentData()
        if not vendor_id or not dept_id:
            return

        self._reagents = ReagentModel.get_by_vendor_dept(vendor_id, dept_id)
        self.table.setRowCount(0)

        for r, rg in enumerate(self._reagents):
            self.table.insertRow(r)
            self.table.setRowHeight(r, 45)
            stock_raw = float(InventoryModel.get_current_stock_count(rg["reagent_id"]) or 0)
            s2c = float(rg.get("stock_to_count") or 1)
            stock_unit = rg.get("stock_unit") or "未設單位"

            # 安全庫存以「入庫單位」儲存於 reagents.safety_stock
            safety_in_stock = float(rg.get("safety_stock") or 0)
            # 目前庫存折算回入庫單位比較
            stock_in_stock = stock_raw  # get_current_stock_count 已是入庫單位數量
            low = stock_in_stock < safety_in_stock and safety_in_stock > 0

            for c_idx, val in enumerate([
                rg["reagent_name"],
                rg["item_number"] or "",
                f"{safety_in_stock:.1f} {stock_unit}",
                f"{stock_raw:.1f} {stock_unit}",
            ]):
                item = QTableWidgetItem(str(val))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                # 目前庫存不足安全庫存，橘色提示
                if c_idx == 3 and low:
                    item.setForeground(__import__("PyQt6.QtGui", fromlist=["QColor"]).QColor("#e07820"))
                self.table.setItem(r, c_idx, item)

            # 訂購數量（透過容器封裝實現絕對垂直置中）
            edit = QLineEdit("0")
            edit.setValidator(QIntValidator(0, 9999))
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setFixedHeight(32) # 調高至 32px 確保文字不被遮擋
            edit.setStyleSheet(
                "background: transparent; border: none; "
                "color:#d0e8ff; selection-background-color: #3d5a80; "
                "font-size: 13px; padding: 0px;"
            )
            
            # 建立容器並將輸入框「拎起來」放到正中央
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(edit)
            layout.setContentsMargins(5, 0, 5, 0) # 左右留一點點邊距，上下交給 layout 自動對齊
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # 強制垂直與水平置中
            self.table.setCellWidget(r, 4, container)

    def _save_and_print(self):
        if not self._reagents:
            self.warn("提示", "請先載入試劑清單")
            return

        # 收集有訂購數量的項目
        order_items = []
        for r, rg in enumerate(self._reagents):
            container = self.table.cellWidget(r, 4)
            if container:
                edit = container.findChild(QLineEdit)
                if edit:
                    try:
                        qty = int(float(edit.text() or 0))
                        if qty > 0:
                            order_items.append({"reagent_id": rg["reagent_id"], "qty": qty,
                                                 "name": rg["reagent_name"]})
                    except ValueError:
                        continue

        if not order_items:
            self.warn( "提示", "請至少輸入一項訂購數量")
            return

        vendor_id = self.cb_vendor.currentData()
        dept_id = self.cb_dept.currentData()
        vendor_name = self.cb_vendor.currentText()
        dept_name = self.cb_dept.currentText()

        po_code = generate_po_code()
        po_id = PurchaseOrderModel.create(po_code, vendor_id, dept_id, self.user["user_id"])
        for oi in order_items:
            PurchaseOrderModel.add_item(po_id, oi["reagent_id"], oi["qty"])

        PurchaseOrderModel.set_status(po_id, 1)

        # 列印訂購單（ZPL A4 / 一般訂購條碼標籤）
        self._print_po(po_code, vendor_name, dept_name, order_items)

        self.alert(self, "訂單已建立",
                   f"訂購單條碼：{po_code}\n共 {len(order_items)} 項試劑")
        self.table.setRowCount(0)
        self._reagents = []

    def _print_po(self, po_code, vendor_name, dept_name, items):
        """列印訂購單（含訂購條碼），使用 ZPL 列印至 Zebra 印表機。"""
        # 訂購單標籤：10cm x 15cm @ 203dpi = 800 x 1200 dots
        lines = "\n".join(
            f"^FO20,{220 + i*28}^CF0,20^FD{oi['name']}  x{oi['qty']}^FS"
            for i, oi in enumerate(items[:20])
        )
        zpl = f"""^XA
^PW800
^LL1200
^CI28

^FO20,20
^CF0,40
^FD訂購單^FS

^FO20,70
^CF0,24
^FD廠商：{vendor_name}^FS
^FO20,100
^CF0,24
^FD組別：{dept_name}^FS

^FO20,140
^BCN,80,N,N,N
^FD{po_code}^FS
^FO260,148
^CF0,20
^FD{po_code}^FS

^FO20,200
^CF0,20
^FD訂購項目：^FS
{lines}

^XZ"""
        try:
            _send_zpl(zpl)
        except Exception as e:
            self.warn( "列印錯誤", str(e))
