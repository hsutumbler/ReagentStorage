# ui/master/user_management.py — 使用者管理頁面

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QFormLayout, QComboBox,
    QCheckBox, QMessageBox, QTableWidgetItem, QMenu,
)
from PyQt6.QtCore import Qt
from ui.base_page import BasePage
from services.auth_service import AuthService, ROLE_LABELS


class UserManagementPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("使用者管理", "新增、修改使用者帳號與權限", user)
        self._build()

    def _build(self):
        toolbar = QHBoxLayout()
        btn_add = QPushButton("＋ 新增使用者")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._add_user)
        
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

        headers = ["工號", "姓名", "角色", "狀態"]
        self.table = self.make_table(headers)
        
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        self.content_layout.addWidget(self.table)

        self._load_data()

    def _load_data(self):
        users = AuthService.get_all_users()
        self.table.setRowCount(0)
        for r, u in enumerate(users):
            self.table.insertRow(r)
            vals = [
                u["employee_id"], u["name"],
                ROLE_LABELS.get(u["role"], "?"),
                "啟用" if u["is_active"] else "停用",
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if c == 0:
                    item.setData(Qt.ItemDataRole.UserRole, u)
                self.table.setItem(r, c, item)
        
        self._on_selection_changed()

    def _on_selection_changed(self):
        has_selection = len(self.table.selectedItems()) > 0
        self.btn_edit.setEnabled(has_selection)
        
        can_delete = False
        if has_selection:
            data = self._get_selected_user()
            if data and data.get("employee_id") != "admin":
                can_delete = True
        self.btn_delete.setEnabled(can_delete)

    def _get_selected_user(self):
        row = self.table.currentRow()
        if row >= 0:
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _on_edit_clicked(self):
        data = self._get_selected_user()
        if data:
            self._edit_user(data["user_id"], data)

    def _on_delete_clicked(self):
        data = self._get_selected_user()
        if data:
            self._delete_user(data["user_id"], data["employee_id"])

    def _on_double_clicked(self, row, col):
        data = self._get_selected_user()
        if data:
            self._edit_user(data["user_id"], data)

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        
        data = self._get_selected_user()
        menu = QMenu(self)
        action_edit = menu.addAction("修改")
        action_delete = menu.addAction("刪除")
        if data and data.get("employee_id") == "admin":
            action_delete.setEnabled(False)
        
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == action_edit:
            self._on_edit_clicked()
        elif action == action_delete:
            self._on_delete_clicked()

    def _add_user(self):
        dlg = UserDialog(self)
        if dlg.exec():
            d = dlg.get_data()
            AuthService.create_user(d["employee_id"], d["name"], d["password"], d["role"])
            self._load_data()

    def _edit_user(self, user_id: int, u: dict):
        dlg = UserDialog(self, u)
        if dlg.exec():
            d = dlg.get_data()
            AuthService.update_user(user_id, d["name"], d["role"], d["is_active"])
            if d.get("password"):
                AuthService.change_password(user_id, d["password"])
            self._load_data()

    def _delete_user(self, user_id: int, employee_id: str):
        if not self.confirm("確認刪除", f"確定要刪除員工「{employee_id}」嗎？\n此操作無法復原！"):
            return
        
        try:
            AuthService.delete_user(user_id)
            self._load_data()
        except Exception as e:
            self.warn( "刪除失敗", f"無法刪除該員工（可能已有相關的操作記錄）：\n{str(e)}")


class UserDialog(QDialog):
    def __init__(self, parent, user: dict = None):
        super().__init__(parent)
        self.is_edit = user is not None
        self.setWindowTitle("使用者資料")
        self.setFixedWidth(380)
        self.setStyleSheet(parent.styleSheet())
        form = QFormLayout(self)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        self.f_emp_id = QLineEdit(user["employee_id"] if user else "")
        self.f_emp_id.setEnabled(not self.is_edit)
        self.f_name = QLineEdit(user["name"] if user else "")
        self.f_pw = QLineEdit()
        self.f_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.f_pw.setPlaceholderText("留空則不修改" if self.is_edit else "必填")

        self.f_role = QComboBox()
        for k, v in ROLE_LABELS.items():
            self.f_role.addItem(v, k)
        if user:
            idx = self.f_role.findData(user["role"])
            if idx >= 0:
                self.f_role.setCurrentIndex(idx)

        self.f_active = QCheckBox("帳號啟用")
        self.f_active.setChecked(user["is_active"] if user else True)
        self.f_active.setStyleSheet("color: #a0c0dc;")

        form.addRow("工號 *", self.f_emp_id)
        form.addRow("姓名 *", self.f_name)
        form.addRow("密碼", self.f_pw)
        form.addRow("角色 *", self.f_role)
        form.addRow("", self.f_active)

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
        if not self.f_emp_id.text().strip() or not self.f_name.text().strip():
            QMessageBox.warning(self, "驗證", "工號與姓名為必填")
            return
        if not self.is_edit and not self.f_pw.text():
            QMessageBox.warning(self, "驗證", "新增使用者時密碼為必填")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "employee_id": self.f_emp_id.text().strip(),
            "name":        self.f_name.text().strip(),
            "password":    self.f_pw.text(),
            "role":        self.f_role.currentData(),
            "is_active":   self.f_active.isChecked(),
        }
