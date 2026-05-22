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
        self.cb_dept.addItem("不分組", None)
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
        headers = ["試劑名稱", "料號", "安全庫存", "目前庫存", "訂購數量 (入庫單位)"]
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
            "alternate-background-color:#FDFBF7; background:#FFFFFF; "
            "border:1px solid #DEE2E6; border-radius:6px; "
            "color:#2D3436; gridline-color:#DEE2E6; font-size: 13px;"
        )
        self.table.horizontalHeader().setStyleSheet(
            "QHeaderView::section{background:#F1F3F5; color:#2D3436; "
            "border:none; border-right:1px solid #DEE2E6; "
            "border-bottom:1px solid #DEE2E6; padding:10px 5px;}"
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
        if not vendor_id:
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

            # 訂購數量（無框幽靈輸入樣式）
            edit = QLineEdit("0")
            edit.setValidator(QIntValidator(0, 9999))
            edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            edit.setFixedSize(60, 42) # 寬度60，高度42完美對齊列高
            edit.setStyleSheet("""
                QLineEdit {
                    background: transparent;
                    border: none;
                    outline: none;
                    color: #2D3436;
                    font-size: 14px;
                    padding: 0px;
                    margin: 0px;
                }
                QLineEdit:hover { background: rgba(0, 0, 0, 0.03); }
                QLineEdit:focus {
                    background: rgba(255, 255, 255, 0.8);
                    border-bottom: 2px solid #0066CC;
                }
            """)
            
            # 建立容器並將輸入框與單位並排置中
            container = QWidget()
            container.setStyleSheet("background: transparent; border: none;")
            layout = QHBoxLayout(container)
            
            # 使用 Stretch 把元件擠在正中央
            layout.addStretch()
            layout.addWidget(edit)
            
            lbl_unit = QLabel(stock_unit)
            lbl_unit.setFixedHeight(42)
            lbl_unit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            lbl_unit.setStyleSheet("color: #636E72; font-size: 14px; border: none; background: transparent; padding-bottom: 6px; margin: 0px;")
            layout.addWidget(lbl_unit)
            layout.addStretch()
            
            layout.setContentsMargins(0, 0, 0, 0) 
            layout.setSpacing(2) # 輸入框與單位的微小間距
            self.table.setCellWidget(r, 4, container)

    def _save_and_print(self):
        if not self._reagents:
            self.warn("提示", "請先載入試劑清單")
            return

        dept_id = self.cb_dept.currentData()
        if not dept_id:
            self.warn("提示", "每張訂購單必須綁定所屬組別，請於上方下拉選單選擇特定「組別」後，重新載入並訂購。")
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

        # 列印訂購單（呼叫 A4 PDF 報表引擎）
        self._print_po(po_code)

        self.alert("訂單已建立",
                   f"訂購單條碼：{po_code}\n共 {len(order_items)} 項試劑")
        self.table.setRowCount(0)
        self._reagents = []

    def _print_po(self, po_code):
        """產生 A4 訂購單 PDF 並詢問儲存路徑，存檔後自動開啟。"""
        import os
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        from services.report_generator import ReportGenerator

        po_data = PurchaseOrderModel.get_by_code(po_code)
        if not po_data:
            self.warn("錯誤", "找不到訂購單資料")
            return

        po_data["creator_name"] = self.user.get("name", "未知")

        # 預設儲存路徑
        default_name = f"訂購單_{po_code}.pdf"
        default_dir = os.path.expanduser("~/Documents")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "儲存訂購單 PDF",
            os.path.join(default_dir, default_name),
            "PDF Files (*.pdf)"
        )
        if not path:
            return  # 使用者取消儲存

        try:
            ReportGenerator.generate_po_pdf(po_data, path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.warn("產生 PDF 失敗", str(e))
