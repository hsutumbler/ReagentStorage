# ui/master/reagent_management.py — 試劑管理頁面

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QDialog, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QMessageBox, QTableWidgetItem, QFileDialog, QMenu
)
from PyQt6.QtCore import Qt
from ui.base_page import BasePage
from database.models.reagent import ReagentModel
from database.models.vendor import VendorModel
from database.connection import DBContext
from services.excel_service import ExcelService


class ReagentManagementPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("試劑管理", "新增、修改試劑主檔", user)
        self._build()

    def _build(self):
        # 篩選列
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("廠商："))
        self.cb_vendor = QComboBox()
        self.cb_vendor.addItem("全部", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        self.cb_vendor.currentIndexChanged.connect(self._load_data)

        filter_row.addWidget(self.cb_vendor)
        filter_row.addWidget(QLabel("組別："))
        self.cb_dept = QComboBox()
        self.cb_dept.addItem("全部", None)
        for d in ReagentModel.get_all_departments():
            self.cb_dept.addItem(d["dept_name"], d["dept_id"])
        self.cb_dept.currentIndexChanged.connect(self._load_data)
        filter_row.addWidget(self.cb_dept)
        
        filter_row.addWidget(QLabel("類別："))
        self.cb_category = QComboBox()
        self.cb_category.addItem("全部", None)
        for cat in ["試劑", "品管液", "校正液", "緩衝液", "其他"]:
            self.cb_category.addItem(cat, cat)
        self.cb_category.currentIndexChanged.connect(self._load_data)
        filter_row.addWidget(self.cb_category)
        
        filter_row.addStretch()

        self.btn_edit = QPushButton("修改")
        self.btn_edit.setObjectName("btn_success")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_clicked)
        
        self.btn_delete = QPushButton("刪除")
        self.btn_delete.setObjectName("btn_danger")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        
        filter_row.addWidget(self.btn_edit)
        filter_row.addWidget(self.btn_delete)

        btn_import = QPushButton("📥 匯入 Excel")
        btn_import.clicked.connect(self._import_excel)
        filter_row.addWidget(btn_import)

        btn_add = QPushButton("＋ 新增試劑")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._add_reagent)
        filter_row.addWidget(btn_add)
        self.content_layout.addLayout(filter_row)
        
        # 提示文字
        lbl_hint = QLabel("💡 提示：雙擊資料可修改，右鍵可刪除")
        lbl_hint.setStyleSheet("color: #888888; font-size: 12px;")
        hint_row = QHBoxLayout()
        hint_row.addStretch()
        hint_row.addWidget(lbl_hint)
        self.content_layout.addLayout(hint_row)

        headers = ["試劑名稱", "類別", "料號", "組別", "廠商", "廠牌",
                   "保存溫度", "開封天數", "安全庫存"]
        self.table = self.make_table(headers)
        
        # 欄位寬度最佳化，善用整頁寬度
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(header.ResizeMode.Interactive)
        
        # 固定基本寬度的欄位
        self.table.setColumnWidth(1, 80)   # 類別
        self.table.setColumnWidth(2, 100)  # 料號
        self.table.setColumnWidth(3, 100)  # 組別
        self.table.setColumnWidth(5, 100)  # 廠牌
        self.table.setColumnWidth(6, 120)  # 保存溫度
        self.table.setColumnWidth(7, 80)   # 開封天數
        self.table.setColumnWidth(8, 100)  # 安全庫存
        
        # 試劑名稱與廠商因為字數可能較長，設為 Stretch 自動平分並填滿剩餘的頁面寬度
        header.setSectionResizeMode(0, header.ResizeMode.Stretch)
        header.setSectionResizeMode(4, header.ResizeMode.Stretch)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        self.content_layout.addWidget(self.table)

        self._load_data()

    def on_page_show(self):
        """當頁面顯示時，刷新下拉選單，確保剛新增的廠商/組別能出現"""
        self._refresh_filters()
        self._load_data()

    def _refresh_filters(self):
        self.cb_vendor.blockSignals(True)
        self.cb_dept.blockSignals(True)
        self.cb_category.blockSignals(True)
        
        curr_vendor = self.cb_vendor.currentData()
        curr_dept = self.cb_dept.currentData()
        curr_category = self.cb_category.currentData()
        
        self.cb_vendor.clear()
        self.cb_vendor.addItem("全部", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
            
        self.cb_dept.clear()
        self.cb_dept.addItem("全部", None)
        for d in ReagentModel.get_all_departments():
            self.cb_dept.addItem(d["dept_name"], d["dept_id"])
            
        idx_v = self.cb_vendor.findData(curr_vendor)
        if idx_v >= 0: self.cb_vendor.setCurrentIndex(idx_v)
        
        idx_d = self.cb_dept.findData(curr_dept)
        if idx_d >= 0: self.cb_dept.setCurrentIndex(idx_d)
        
        idx_c = self.cb_category.findData(curr_category)
        if idx_c >= 0: self.cb_category.setCurrentIndex(idx_c)
        
        self.cb_vendor.blockSignals(False)
        self.cb_dept.blockSignals(False)
        self.cb_category.blockSignals(False)

    def _import_excel(self):
        """匯入試劑主檔 Excel。"""
        # 詢問是要下載範本還是匯入
        parent_win = self.window() if self.window() else self
        msg = QMessageBox(parent_win)
        msg.setWindowTitle("Excel 匯入")
        msg.setText("請選擇操作：")
        btn_download = msg.addButton("下載範本", QMessageBox.ButtonRole.ActionRole)
        btn_import = msg.addButton("選取檔案匯入", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_download:
            path, _ = QFileDialog.getSaveFileName(parent_win, "儲存範本", "試劑匯入範本.xlsx", "Excel Files (*.xlsx)")
            if path:
                if ExcelService.generate_reagent_template(path):
                    self.alert("完成", "範本已儲存，請填寫後再行匯入。")
                else:
                    self.warn("失敗", "無法儲存範本，請檢查檔案是否已被開啟或資料夾權限。")
        
        elif msg.clickedButton() == btn_import:
            path, _ = QFileDialog.getOpenFileName(parent_win, "選取 Excel 檔案", "", "Excel Files (*.xlsx *.xls)")
            if path:
                s, f, err = ExcelService.import_reagents(path)
                result_msg = f"匯入完成！\n成功：{s} 筆\n失敗：{f} 筆"
                if err:
                    result_msg += f"\n\n錯誤詳情：\n{err}"
                
                if f > 0:
                    QMessageBox.warning(parent_win, "匯入結果", result_msg)
                else:
                    self.alert("匯入成功", result_msg)
                self._load_data()

    def _load_data(self):
        # 防止在匯入後 UI 物件已失效（Mac 偶發 Bug）
        try:
            vendor_id = self.cb_vendor.currentData()
            dept_id = self.cb_dept.currentData()
            category = self.cb_category.currentData()
        except RuntimeError:
            return
            
        reagents = ReagentModel.get_all(vendor_id=vendor_id, category=category)
        if dept_id:
            reagents = [r for r in reagents if r["dept_id"] == dept_id]
        if dept_id:
            reagents = [r for r in reagents if r["dept_id"] == dept_id]

        self.table.setRowCount(0)
        for r, rg in enumerate(reagents):
            self.table.insertRow(r)
            stock_unit = rg.get("stock_unit") or ""
            safety_display = f"{float(rg.get('safety_stock') or 0):.1f} {stock_unit}"
            
            for c_idx, val in enumerate([
                rg["reagent_name"], rg.get("category", "試劑"), rg["item_number"] or "", rg["dept_name"],
                rg["vendor_name"], rg["brand"] or "", rg["storage_temp"] or "",
                rg["open_days"] or "", safety_display
            ]):
                item = QTableWidgetItem(str(val))
                if c_idx == 0:
                    item.setData(Qt.ItemDataRole.UserRole, rg)
                self.table.setItem(r, c_idx, item)

        self._on_selection_changed()

    def _on_selection_changed(self):
        has_selection = len(self.table.selectedItems()) > 0
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _get_selected_reagent(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_edit_clicked(self):
        data = self._get_selected_reagent()
        if data:
            self._edit_reagent(data["reagent_id"])

    def _on_delete_clicked(self):
        data = self._get_selected_reagent()
        if data:
            self._delete_reagent(data["reagent_id"], data["reagent_name"])

    def _on_double_clicked(self, row, col):
        data = self._get_selected_reagent()
        if data:
            self._edit_reagent(data["reagent_id"])

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        
        menu = QMenu(self)
        action_edit = menu.addAction("修改")
        action_delete = menu.addAction("刪除")
        
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == action_edit:
            self._on_edit_clicked()
        elif action == action_delete:
            self._on_delete_clicked()

    def _add_reagent(self):
        dlg = ReagentDialog(self)
        if dlg.exec():
            try:
                d = dlg.get_data()
                ReagentModel.create(**d)
                self._load_data()
            except Exception as e:
                self.warn( "儲存失敗", f"無法新增試劑，請檢查資料是否正確：\n{str(e)}")

    def _edit_reagent(self, reagent_id: int):
        r = ReagentModel.get_by_id(reagent_id)
        dlg = ReagentDialog(self, r)
        if dlg.exec():
            try:
                d = dlg.get_data()
                ReagentModel.update(reagent_id, **d)
                self._load_data()
            except Exception as e:
                self.warn("儲存失敗", f"無法更新試劑資料：\n{str(e)}")

    def _delete_reagent(self, reagent_id: int, reagent_name: str):
        if not self.confirm("確認刪除", f"確定要刪除試劑「{reagent_name}」嗎？\n此操作無法復原！"):
            return
        
        try:
            ReagentModel.delete(reagent_id)
            self._load_data()
        except Exception as e:
            self.warn("刪除失敗", f"無法刪除該試劑（可能已有相關的庫存或訂單資料）：\n{str(e)}")



from database.models.unit_conversion import UnitConversionModel

class ReagentDialog(QDialog):
    def __init__(self, parent, reagent: dict = None):
        super().__init__(parent)
        self.setWindowTitle("試劑資料")
        self.setFixedWidth(680)
        self.setStyleSheet(parent.styleSheet())
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        self.f_name = QLineEdit(reagent["reagent_name"] if reagent else "")
        self.f_item = QLineEdit(reagent["item_number"] or "" if reagent else "")

        self.cb_category = QComboBox()
        self.cb_category.addItems(["試劑", "品管液", "校正液", "緩衝液", "其他"])
        if reagent and reagent.get("category"):
            idx = self.cb_category.findText(reagent["category"])
            if idx >= 0: self.cb_category.setCurrentIndex(idx)

        self.cb_dept = QComboBox()
        depts = ReagentModel.get_all_departments()
        for d in depts:
            self.cb_dept.addItem(d["dept_name"], d["dept_id"])
        if reagent:
            idx = self.cb_dept.findData(reagent["dept_id"])
            if idx >= 0: self.cb_dept.setCurrentIndex(idx)

        self.cb_vendor = QComboBox()
        vendors = VendorModel.get_all()
        for v in vendors:
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        if reagent:
            idx = self.cb_vendor.findData(reagent["vendor_id"])
            if idx >= 0: self.cb_vendor.setCurrentIndex(idx)

        self.f_brand = QLineEdit(reagent["brand"] or "" if reagent else "")
        
        self.f_temp = QComboBox()
        temp_options = ["室溫(18-25度)", "冷藏(2-8度)", "冷凍(< -20度)"]
        self.f_temp.addItems(temp_options)
        if reagent and reagent["storage_temp"]:
            idx = self.f_temp.findText(reagent["storage_temp"])
            if idx >= 0: self.f_temp.setCurrentIndex(idx)

        self.f_open_days = QSpinBox()
        self.f_open_days.setRange(0, 3650)
        self.f_open_days.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.f_open_days.setValue(reagent["open_days"] or 0 if reagent else 0)
        
        # 單位換算選單 — 切換時更新安全庫存單位標籤
        self.cb_unit = QComboBox()
        self.cb_unit.addItem("-- 不設定 (手動輸入) --", None)
        self._unit_map = {}  # unit_id -> unit data
        for u in UnitConversionModel.get_all():
            self.cb_unit.addItem(u["unit_name"], u["unit_id"])
            self._unit_map[u["unit_id"]] = u
        if reagent:
            idx = self.cb_unit.findData(reagent["unit_id"])
            if idx >= 0: self.cb_unit.setCurrentIndex(idx)

        # 安全庫存 (以入庫單位儲存)
        self.f_safety = QDoubleSpinBox()
        self.f_safety.setRange(0, 99999)
        self.f_safety.setDecimals(1)
        self.f_safety.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.f_safety.setValue(float(reagent["safety_stock"] or 0) if reagent else 0)
        self.lbl_safety_unit = QLabel("")
        safety_row = QHBoxLayout()
        safety_row.setContentsMargins(0, 0, 0, 0)
        safety_row.addWidget(self.f_safety)
        safety_row.addWidget(self.lbl_safety_unit)

        # 預設標籤類型設定
        self.cb_label_type = QComboBox()
        self.cb_label_type.addItem("一般標籤", 1)
        self.cb_label_type.addItem("QR Code 標籤", 2)
        if reagent:
            idx = self.cb_label_type.findData(reagent.get("default_label_type", 1))
            if idx >= 0: self.cb_label_type.setCurrentIndex(idx)

        # 切換換算設定時動態更新安全庫存的單位標籤
        self.cb_unit.currentIndexChanged.connect(self._update_safety_unit_label)
        self._update_safety_unit_label()

        # ── 兩排版面配置 ──
        # Row 0
        grid.addWidget(QLabel("試劑名稱 *"), 0, 0)
        grid.addWidget(self.f_name, 0, 1)
        grid.addWidget(QLabel("類別 *"), 0, 2)
        grid.addWidget(self.cb_category, 0, 3)
        # Row 1
        grid.addWidget(QLabel("料號"), 1, 0)
        grid.addWidget(self.f_item, 1, 1)
        grid.addWidget(QLabel("組別 *"), 1, 2)
        grid.addWidget(self.cb_dept, 1, 3)
        # Row 2
        grid.addWidget(QLabel("廠商 *"), 2, 0)
        grid.addWidget(self.cb_vendor, 2, 1)
        grid.addWidget(QLabel("廠牌"), 2, 2)
        grid.addWidget(self.f_brand, 2, 3)
        # Row 3
        grid.addWidget(QLabel("保存溫度"), 3, 0)
        grid.addWidget(self.f_temp, 3, 1)
        grid.addWidget(QLabel("開封天數（天）"), 3, 2)
        grid.addWidget(self.f_open_days, 3, 3)
        # Row 4
        grid.addWidget(QLabel("單位換算設定"), 4, 0)
        grid.addWidget(self.cb_unit, 4, 1)
        grid.addWidget(QLabel("安全庫存 (入庫)"), 4, 2)
        grid.addLayout(safety_row, 4, 3)
        # Row 5
        grid.addWidget(QLabel("預設列印標籤"), 5, 0)
        grid.addWidget(self.cb_label_type, 5, 1)
        
        main_layout.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("儲存")
        btn_ok.setObjectName("btn_primary")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self._validate)
        btn_cancel.clicked.connect(self.reject)
        
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        
        main_layout.addLayout(btn_row)

    def _update_safety_unit_label(self):
        """切換換算設定時，動態更新安全庫存旁邊的單位名稱。"""
        unit_id = self.cb_unit.currentData()
        u = self._unit_map.get(unit_id)
        if u:
            self.lbl_safety_unit.setText(u["stock_unit"])
            self.lbl_safety_unit.setStyleSheet("color:#7ea8c9; font-size:13px;")
        else:
            self.lbl_safety_unit.setText("（未設定換算）")
            self.lbl_safety_unit.setStyleSheet("color:#506070; font-size:12px;")

    def _validate(self):
        if not self.f_name.text().strip():
            QMessageBox.warning(self, "驗證", "試劑名稱為必填")
            return
        if self.cb_dept.currentData() is None:
            QMessageBox.warning(self, "驗證", "請選擇組別")
            return
        if self.cb_vendor.currentData() is None:
            QMessageBox.warning(self, "驗證", "請選擇廠商")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "reagent_name": self.f_name.text().strip(),
            "category":     self.cb_category.currentText(),
            "item_number":  self.f_item.text().strip() or None,
            "dept_id":      self.cb_dept.currentData(),
            "storage_temp": self.f_temp.currentText(),
            "open_days":    self.f_open_days.value() or None,
            "vendor_id":    self.cb_vendor.currentData(),
            "brand":        self.f_brand.text().strip() or None,
            "unit_id":      self.cb_unit.currentData(),
            "safety_stock": self.f_safety.value(),
            "default_label_type": self.cb_label_type.currentData(),
        }
