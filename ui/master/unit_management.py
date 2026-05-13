from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QFormLayout, QDoubleSpinBox,
    QMessageBox, QTableWidgetItem, QCompleter, QFileDialog
)
from ui.base_page import BasePage
from database.models.reagent import ReagentModel
from database.connection import DBContext
from services.excel_service import ExcelService
from database.models.unit_conversion import UnitConversionModel

class UnitManagementPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("單位換算管理", "設定入庫、盤點、出庫單位及換算比例", user)
        self._build()

    def _build(self):
        toolbar = QHBoxLayout()
        btn_import = QPushButton("📥 匯入 Excel")
        btn_import.clicked.connect(self._import_excel)
        toolbar.addWidget(btn_import)

        btn_add = QPushButton("＋ 新增單位換算")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._add_unit)
        btn_refresh = QPushButton("重新整理")
        btn_refresh.clicked.connect(self._load_data)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_refresh)
        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

        # 說明
        hint = QLabel("範例：1 箱（入庫）= 12 盒（盤點）= 60 管（出庫），"
                       "則入庫→盤點=12，入庫→出庫=60")
        hint.setStyleSheet("color:#4a7aaa; font-size:12px;")
        self.content_layout.addWidget(hint)

        headers = ["換算名稱", "入庫單位", "盤點單位", "出庫單位",
                   "入庫→盤點", "入庫→出庫", "安全庫存", "操作"]
        self.table = self.make_table(headers)
        # 此欄固定寬度，容納兩個按鈕
        self.table.horizontalHeader().setSectionResizeMode(
            7, self.table.horizontalHeader().ResizeMode.Fixed
        )
        self.table.setColumnWidth(7, 160)
        self.content_layout.addWidget(self.table)

        self._load_data()

    def _import_excel(self):
        """匯入單位換算 Excel。"""
        msg = QMessageBox(None)
        msg.setWindowTitle("Excel 匯入")
        msg.setText("請選擇操作：")
        btn_download = msg.addButton("下載範本", QMessageBox.ButtonRole.ActionRole)
        btn_import = msg.addButton("選取檔案匯入", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        msg.exec()

        if msg.clickedButton() == btn_download:
            path, _ = QFileDialog.getSaveFileName(None, "儲存範本", "單位換算匯入範本.xlsx", "Excel Files (*.xlsx)")
            if path:
                if ExcelService.generate_unit_template(path):
                    self.alert("完成", "範本已儲存，請填寫後再行匯入。")
                else:
                    self.warn("失敗", "無法儲存範本，請檢查檔案是否已被開啟或資料夾權限。")
        
        elif msg.clickedButton() == btn_import:
            path, _ = QFileDialog.getOpenFileName(None, "選取 Excel 檔案", "", "Excel Files (*.xlsx *.xls)")
            if path:
                s, f, err = ExcelService.import_units(path)
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
            with DBContext() as (_, c):
                c.execute("SELECT * FROM unit_conversions ORDER BY unit_name")
                rows = c.fetchall()
        except RuntimeError:
            return
        self.table.setRowCount(0)
        for r, u in enumerate(rows):
            self.table.insertRow(r)
            # 計算 入庫 -> 出庫 的總比值
            total_ratio = u["stock_to_count"] * u["count_to_issue"]
            for c_idx, val in enumerate([
                u["unit_name"], u["stock_unit"], u["count_unit"], u["issue_unit"],
                u["stock_to_count"], total_ratio, u["safety_stock"],
            ]):
                self.table.setItem(r, c_idx, QTableWidgetItem(str(val)))
            # 操作按鈕容器
            from PyQt6.QtWidgets import QWidget, QHBoxLayout
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(10)

            btn_edit = self.make_table_btn("修改", "primary")
            btn_edit.clicked.connect(lambda _, uid=u["unit_id"]: self._edit_unit(uid))
            
            btn_del = self.make_table_btn("刪除", "danger")
            btn_del.clicked.connect(lambda _, uid=u["unit_id"], uname=u["unit_name"]: self._delete_unit(uid, uname))

            action_layout.addStretch()
            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_del)
            action_layout.addStretch()

            self.table.setCellWidget(r, 7, action_widget)

    def _add_unit(self):
        dlg = UnitDialog(self)
        if dlg.exec():
            d = dlg.get_data()
            with DBContext() as (_, c):
                # 1. 插入單位換算
                c.execute(
                    "INSERT INTO unit_conversions "
                    "(unit_name,stock_unit,count_unit,issue_unit,stock_to_count,count_to_issue,safety_stock) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (d["unit_name"], d["stock_unit"], d["count_unit"],
                     d["issue_unit"], d["stock_to_count"], d["count_to_issue"], d["safety_stock"]),
                )
                unit_id = c.lastrowid
                
                # 2. 自動關聯：找尋名稱相同的試劑並更新其 unit_id
                c.execute("UPDATE reagents SET unit_id=%s WHERE reagent_name=%s", (unit_id, d["unit_name"]))
                
            self._load_data()

    def _edit_unit(self, unit_id: int):
        with DBContext() as (_, c):
            c.execute("SELECT * FROM unit_conversions WHERE unit_id=%s", (unit_id,))
            u = c.fetchone()
        dlg = UnitDialog(self, u)
        if dlg.exec():
            d = dlg.get_data()
            with DBContext() as (_, c):
                c.execute(
                    "UPDATE unit_conversions SET unit_name=%s, stock_unit=%s, "
                    "count_unit=%s, issue_unit=%s, stock_to_count=%s, count_to_issue=%s, safety_stock=%s "
                    "WHERE unit_id=%s",
                    (d["unit_name"], d["stock_unit"], d["count_unit"],
                     d["issue_unit"], d["stock_to_count"], d["count_to_issue"], d["safety_stock"], unit_id),
                )
                # 再次同步：防止名稱修改後關聯跑掉
                c.execute("UPDATE reagents SET unit_id=%s WHERE reagent_name=%s", (unit_id, d["unit_name"]))
                
            self._load_data()

    def _delete_unit(self, unit_id: int, unit_name: str):
        if not self.confirm("確認刪除", f"確定要刪除「{unit_name}」的換算設定嗎？\n此操作無法復原！"):
            return
        
        try:
            with DBContext() as (_, c):
                c.execute("DELETE FROM unit_conversions WHERE unit_id=%s", (unit_id,))
            self._load_data()
        except Exception as e:
            self.warn(self, "刪除失敗", f"無法刪除該單位換算（可能已有試劑正在使用此單位）：\n{str(e)}")


class UnitDialog(QDialog):
    def __init__(self, parent, unit: dict = None):
        super().__init__(parent)
        self.setWindowTitle("單位換算設定")
        self.setFixedWidth(360)
        self.setStyleSheet(parent.styleSheet())
        form = QFormLayout(self)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        self.f_name = QLineEdit(unit["unit_name"] if unit else "")
        self.f_stock = QLineEdit(unit["stock_unit"] if unit else "")
        self.f_count = QLineEdit(unit["count_unit"] if unit else "")
        self.f_issue = QLineEdit(unit["issue_unit"] if unit else "")
        self.f_issue.textChanged.connect(self._update_unit_label)

        self.f_c2i = QDoubleSpinBox()
        self.f_c2i.setRange(0.0001, 99999)
        self.f_c2i.setDecimals(4)
        self.f_c2i.setValue(float(unit["count_to_issue"]) if unit else 1.0)

        self.f_safety = QDoubleSpinBox()
        self.f_safety.setRange(0, 999999)
        self.f_safety.setValue(float(unit["safety_stock"]) if unit else 0.0)
        self.lbl_safety_unit = QLabel(unit["issue_unit"] if unit else "")
        self.lbl_safety_unit.setStyleSheet("color:#4a7aaa; font-weight:bold;")

        self.f_s2c = QDoubleSpinBox()
        self.f_s2c.setRange(0.0001, 99999)
        self.f_s2c.setDecimals(4)
        self.f_s2c.setValue(float(unit["stock_to_count"]) if unit else 1.0)

        # 改為顯示/輸入 入庫 -> 出庫 的總比值
        self.f_s2i = QDoubleSpinBox()
        self.f_s2i.setRange(0.0001, 999999)
        self.f_s2i.setDecimals(4)
        if unit:
            total = float(unit["stock_to_count"] * unit["count_to_issue"])
            self.f_s2i.setValue(total)
        else:
            self.f_s2i.setValue(1.0)

        # 試劑名稱自動完成
        reagents = ReagentModel.get_all()
        names = [r["reagent_name"] for r in reagents]
        completer = QCompleter(names)
        completer.setCaseSensitivity(__import__("PyQt6.QtCore").QtCore.Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(__import__("PyQt6.QtCore").QtCore.Qt.MatchFlag.MatchContains)
        self.f_name.setCompleter(completer)

        for w in [self.f_s2c, self.f_s2i, self.f_safety]:
            w.setStyleSheet(
                "background:#1a2535; border:1px solid #2d4060; "
                "border-radius:6px; color:#d0e8ff; padding:7px 10px;"
            )

        form.addRow("換算名稱 *", self.f_name)
        form.addRow("入庫單位 *", self.f_stock)
        form.addRow("盤點單位 *", self.f_count)
        form.addRow("出庫單位 *", self.f_issue)
        form.addRow("入庫→盤點比 *", self.f_s2c)
        form.addRow("入庫→出庫比 *", self.f_s2i)
        
        safety_row = QHBoxLayout()
        safety_row.addWidget(self.f_safety)
        safety_row.addWidget(self.lbl_safety_unit)
        form.addRow("安全庫存", safety_row)

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
        if not all([self.f_name.text().strip(), self.f_stock.text().strip(),
                    self.f_count.text().strip(), self.f_issue.text().strip()]):
            QMessageBox.warning(self, "驗證", "所有欄位為必填")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "unit_name":     self.f_name.text().strip(),
            "stock_unit":    self.f_stock.text().strip(),
            "count_unit":    self.f_count.text().strip(),
            "issue_unit":    self.f_issue.text().strip(),
            "stock_to_count": self.f_s2c.value(),
            # 存回 DB 前換算回 count_to_issue
            "count_to_issue": self.f_s2i.value() / self.f_s2c.value() if self.f_s2c.value() != 0 else 0,
            "safety_stock":   self.f_safety.value(),
        }

    def _update_unit_label(self, text):
        self.lbl_safety_unit.setText(text)
