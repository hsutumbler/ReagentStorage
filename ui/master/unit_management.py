from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QFormLayout, QDoubleSpinBox,
    QMessageBox, QTableWidgetItem, QCompleter, QFileDialog, QMenu
)
from PyQt6.QtCore import Qt
from ui.base_page import BasePage
from database.models.reagent import ReagentModel
from database.connection import DBContext
from services.excel_service import ExcelService
from database.models.unit_conversion import UnitConversionModel

class UnitManagementPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("單位換算", "設定入庫、盤點、出庫單位及換算比例", user)
        self._build()

    def _build(self):
        toolbar = QHBoxLayout()
        btn_add = QPushButton("＋ 新增單位換算")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._add_unit)
        
        self.btn_edit = QPushButton("修改")
        self.btn_edit.setObjectName("btn_success")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._on_edit_clicked)
        
        self.btn_delete = QPushButton("刪除")
        self.btn_delete.setObjectName("btn_danger")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        
        btn_refresh = QPushButton("重新整理")
        btn_refresh.clicked.connect(self._load_data)
        
        toolbar.addWidget(btn_add)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(btn_refresh)
        
        lbl_hint = QLabel("💡 提示：雙擊資料可修改，右鍵可刪除")
        lbl_hint.setStyleSheet("color: #888888; font-size: 12px;")
        toolbar.addStretch()
        toolbar.addWidget(lbl_hint)
        
        self.content_layout.addLayout(toolbar)

        # 說明
        hint = QLabel("範例：1 箱（入庫）= 12 盒（盤點）= 60 管（出庫），"
                       "則入庫→盤點=12，入庫→出庫=60")
        hint.setStyleSheet("color:#4a7aaa; font-size:12px;")
        self.content_layout.addWidget(hint)

        headers = ["換算名稱", "入庫單位", "盤點單位", "出庫單位",
                   "入庫→盤點", "入庫→出庫"]
        self.table = self.make_table(headers)
        
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        self.content_layout.addWidget(self.table)

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
                f"{float(u['stock_to_count']):.1f}", f"{float(total_ratio):.1f}",
            ]):
                item = QTableWidgetItem(str(val))
                if c_idx == 0:
                    item.setData(Qt.ItemDataRole.UserRole, u)
                self.table.setItem(r, c_idx, item)
                
        self._on_selection_changed()

    def _on_selection_changed(self):
        has_selection = len(self.table.selectedItems()) > 0
        self.btn_edit.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _get_selected_unit(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_edit_clicked(self):
        data = self._get_selected_unit()
        if data:
            self._edit_unit(data["unit_id"])

    def _on_delete_clicked(self):
        data = self._get_selected_unit()
        if data:
            self._delete_unit(data["unit_id"], data["unit_name"])

    def _on_double_clicked(self, row, col):
        data = self._get_selected_unit()
        if data:
            self._edit_unit(data["unit_id"])

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

    def _add_unit(self):
        dlg = UnitDialog(self)
        if dlg.exec():
            d = dlg.get_data()
            with DBContext() as (_, c):
                # 1. 插入單位換算
                c.execute(
                    "INSERT INTO unit_conversions (unit_name,stock_unit,count_unit,issue_unit,stock_to_count,count_to_issue) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (d["unit_name"], d["stock_unit"], d["count_unit"],
                     d["issue_unit"], d["stock_to_count"], d["count_to_issue"]),
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
                sql = """
                    UPDATE unit_conversions SET 
                        unit_name=%s, stock_unit=%s, count_unit=%s, issue_unit=%s,
                        stock_to_count=%s, count_to_issue=%s
                    WHERE unit_id=%s
                """
                c.execute(sql, (
                    d["unit_name"], d["stock_unit"], d["count_unit"],
                    d["issue_unit"], d["stock_to_count"], d["count_to_issue"], unit_id
                ))
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
            self.warn( "刪除失敗", f"無法刪除該單位換算（可能已有試劑正在使用此單位）：\n{str(e)}")


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

        self.f_s2c = QDoubleSpinBox()
        self.f_s2c.setRange(0.1, 99999)
        self.f_s2c.setDecimals(1)
        self.f_s2c.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.f_s2c.setValue(float(unit["stock_to_count"]) if unit else 1.0)

        # 改為顯示/輸入 入庫 -> 出庫 的總比值
        self.f_s2i = QDoubleSpinBox()
        self.f_s2i.setRange(0.1, 999999)
        self.f_s2i.setDecimals(1)
        self.f_s2i.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
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

        form.addRow("換算名稱 *", self.f_name)
        form.addRow("入庫單位 *", self.f_stock)
        form.addRow("盤點單位 *", self.f_count)
        form.addRow("出庫單位 *", self.f_issue)
        form.addRow("入庫→盤點比 *", self.f_s2c)
        form.addRow("入庫→出庫比 *", self.f_s2i)

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
        }
