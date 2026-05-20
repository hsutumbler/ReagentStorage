# ui/master/user_management.py — 使用者管理頁面

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QFormLayout, QComboBox,
    QCheckBox, QMessageBox, QTableWidgetItem,
)
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
        btn_refresh = QPushButton("重新整理")
        btn_refresh.clicked.connect(self._load_data)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_refresh)
        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

        headers = ["工號", "姓名", "角色", "狀態", "操作"]
        self.table = self.make_table(headers)
        # 此欄固定寬度，容納兩個按鈕
        self.table.horizontalHeader().setSectionResizeMode(
            4, self.table.horizontalHeader().ResizeMode.Fixed
        )
        self.table.setColumnWidth(4, 180)
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
                self.table.setItem(r, c, QTableWidgetItem(str(v)))

            # 操作按鈕容器
            from PyQt6.QtWidgets import QWidget, QHBoxLayout
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(10, 0, 10, 0)
            action_layout.setSpacing(12)

            btn_edit = self.make_table_btn("修改", "primary")
            btn_edit.clicked.connect(lambda _, uid=u["user_id"], uu=u: self._edit_user(uid, uu))
            
            action_layout.addStretch()
            action_layout.addWidget(btn_edit)
            
            # 系統管理員 admin 不能被刪除，直接不顯示按鈕
            if u["employee_id"] != "admin":
                btn_del = self.make_table_btn("刪除", "danger")
                btn_del.clicked.connect(lambda _, uid=u["user_id"], emp=u["employee_id"]: self._delete_user(uid, emp))
                action_layout.addWidget(btn_del)

            action_layout.addStretch()

            self.table.setCellWidget(r, 4, action_widget)

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
