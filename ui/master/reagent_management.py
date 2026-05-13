# ui/master/reagent_management.py — 試劑管理頁面

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QDialog, QFormLayout, QComboBox, QSpinBox,
    QDoubleSpinBox, QMessageBox, QTableWidgetItem, QFileDialog
)
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
        filter_row.addStretch()

        btn_import = QPushButton("📥 匯入 Excel")
        btn_import.clicked.connect(self._import_excel)
        filter_row.addWidget(btn_import)

        btn_add = QPushButton("＋ 新增試劑")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._add_reagent)
        filter_row.addWidget(btn_add)
        self.content_layout.addLayout(filter_row)

        headers = ["試劑名稱", "料號", "組別", "廠商", "廠牌",
                   "保存溫度", "開封天數", "操作"]
        self.table = self.make_table(headers)
        # 此欄固定寬度，容納兩個按鈕，給予更多空間避免重疊
        self.table.horizontalHeader().setSectionResizeMode(
            7, self.table.horizontalHeader().ResizeMode.Fixed
        )
        self.table.setColumnWidth(7, 180)
        self.content_layout.addWidget(self.table)

        self._load_data()

    def _import_excel(self):
        """匯入試劑主檔 Excel。"""
        # 詢問是要下載範本還是匯入
        msg = QMessageBox(None)
        msg.setWindowTitle("Excel 匯入")
        msg.setText("請選擇操作：")
        btn_download = msg.addButton("下載範本", QMessageBox.ButtonRole.ActionRole)
        btn_import = msg.addButton("選取檔案匯入", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_download:
            path, _ = QFileDialog.getSaveFileName(None, "儲存範本", "試劑匯入範本.xlsx", "Excel Files (*.xlsx)")
            if path:
                if ExcelService.generate_reagent_template(path):
                    self.alert("完成", "範本已儲存，請填寫後再行匯入。")
                else:
                    self.warn("失敗", "無法儲存範本，請檢查檔案是否已被開啟或資料夾權限。")
        
        elif msg.clickedButton() == btn_import:
            path, _ = QFileDialog.getOpenFileName(None, "選取 Excel 檔案", "", "Excel Files (*.xlsx *.xls)")
            if path:
                s, f, err = ExcelService.import_reagents(path)
                result_msg = f"匯入完成！\n成功：{s} 筆\n失敗：{f} 筆"
                if err:
                    result_msg += f"\n\n錯誤詳情：\n{err}"
                
                if f > 0:
                    QMessageBox.warning(None, "匯入結果", result_msg)
                else:
                    self.alert("匯入成功", result_msg)
                self._load_data()

    def _load_data(self):
        # 防止在匯入後 UI 物件已失效（Mac 偶發 Bug）
        try:
            vendor_id = self.cb_vendor.currentData()
            dept_id = self.cb_dept.currentData()
        except RuntimeError:
            return
            
        reagents = ReagentModel.get_all()
        if vendor_id:
            reagents = [r for r in reagents if r["vendor_id"] == vendor_id]
        if dept_id:
            reagents = [r for r in reagents if r["dept_id"] == dept_id]

        self.table.setRowCount(0)
        for r, rg in enumerate(reagents):
            self.table.insertRow(r)
            for c_idx, val in enumerate([
                rg["reagent_name"], rg["item_number"] or "", rg["dept_name"],
                rg["vendor_name"], rg["brand"] or "", rg["storage_temp"] or "",
                rg["open_days"] or "",
            ]):
                self.table.setItem(r, c_idx, QTableWidgetItem(str(val)))
            # 操作按鈕容器
            from PyQt6.QtWidgets import QWidget, QHBoxLayout
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(10, 0, 10, 0) # 增加左右邊距
            action_layout.setSpacing(12) # 增加按鈕間距

            btn_edit = self.make_table_btn("修改", "primary")
            btn_edit.clicked.connect(lambda _, rid=rg["reagent_id"]: self._edit_reagent(rid))
            
            btn_del = self.make_table_btn("刪除", "danger")
            btn_del.clicked.connect(lambda _, rid=rg["reagent_id"], rname=rg["reagent_name"]: self._delete_reagent(rid, rname))

            action_layout.addStretch()
            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_del)
            action_layout.addStretch()

            self.table.setCellWidget(r, 7, action_widget)

    def _add_reagent(self):
        dlg = ReagentDialog(self)
        if dlg.exec():
            try:
                d = dlg.get_data()
                ReagentModel.create(**d)
                self._load_data()
            except Exception as e:
                self.warn(self, "儲存失敗", f"無法新增試劑，請檢查資料是否正確：\n{str(e)}")

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
        self.setFixedWidth(440)
        self.setStyleSheet(parent.styleSheet())
        form = QFormLayout(self)
        form.setSpacing(10)
        form.setContentsMargins(20, 20, 20, 20)

        self.f_name = QLineEdit(reagent["reagent_name"] if reagent else "")
        self.f_item = QLineEdit(reagent["item_number"] or "" if reagent else "")

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
        self.f_open_days.setValue(reagent["open_days"] or 0 if reagent else 0)
        
        # 單位換算選單
        self.cb_unit = QComboBox()
        self.cb_unit.addItem("-- 不設定 (手動輸入) --", None)
        for u in UnitConversionModel.get_all():
            self.cb_unit.addItem(u["unit_name"], u["unit_id"])
        if reagent:
            idx = self.cb_unit.findData(reagent["unit_id"])
            if idx >= 0: self.cb_unit.setCurrentIndex(idx)

        for w in [self.f_open_days]:
            w.setStyleSheet(
                "background:#1a2535; border:1px solid #2d4060; "
                "border-radius:6px; color:#d0e8ff; padding:7px 10px;"
            )

        form.addRow("試劑名稱 *", self.f_name)
        form.addRow("料號", self.f_item)
        form.addRow("組別 *", self.cb_dept)
        form.addRow("廠商 *", self.cb_vendor)
        form.addRow("廠牌", self.f_brand)
        form.addRow("保存溫度", self.f_temp)
        form.addRow("開封天數（天）", self.f_open_days)
        form.addRow("單位換算設定", self.cb_unit)

        btn_row = QHBoxLayout()
        btn_ok = QPushButton("儲存")
        btn_ok.setObjectName("btn_primary")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self._validate)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        form.addRow(btn_row)

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
            "item_number":  self.f_item.text().strip() or None,
            "dept_id":      self.cb_dept.currentData(),
            "storage_temp": self.f_temp.currentText(),
            "open_days":    self.f_open_days.value() or None,
            "vendor_id":    self.cb_vendor.currentData(),
            "brand":        self.f_brand.text().strip() or None,
            "unit_id":      self.cb_unit.currentData(),
        }
