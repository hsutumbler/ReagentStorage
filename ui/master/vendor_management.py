# ui/master/vendor_management.py — 廠商管理頁面

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QFormLayout, QFrame,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from ui.base_page import BasePage
from database.models.vendor import VendorModel


class VendorManagementPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("廠商管理", "新增、修改廠商資料", user)
        self._build()

    def _build(self):
        # 工具列
        toolbar = QHBoxLayout()
        btn_add = QPushButton("＋ 新增廠商")
        btn_add.setObjectName("btn_primary")
        btn_add.clicked.connect(self._add_vendor)
        btn_refresh = QPushButton("重新整理")
        btn_refresh.clicked.connect(self._load_data)
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_refresh)
        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

        # 表格
        headers = ["廠商名稱", "業務", "訂藥窗口", "電話", "Email", "操作"]
        self.table = self.make_table(headers)
        # 此欄固定寬度，容納兩個按鈕
        self.table.horizontalHeader().setSectionResizeMode(
            5, self.table.horizontalHeader().ResizeMode.Fixed
        )
        self.table.setColumnWidth(5, 160)
        self.content_layout.addWidget(self.table)

        self._load_data()

    def _load_data(self):
        vendors = VendorModel.get_all()
        self.table.setRowCount(0)
        for r, v in enumerate(vendors):
            self.table.insertRow(r)
            for c, val in enumerate([
                v["vendor_name"], v["sales_rep"] or "",
                v["order_contact"] or "", v["phone"] or "", v["email"] or "",
            ]):
                from PyQt6.QtWidgets import QTableWidgetItem
                self.table.setItem(r, c, QTableWidgetItem(val))

            # 操作按鈕容器
            from PyQt6.QtWidgets import QWidget, QHBoxLayout
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(10)

            btn_edit = self.make_table_btn("修改", "primary")
            btn_edit.clicked.connect(lambda _, vid=v["vendor_id"]: self._edit_vendor(vid))
            
            btn_del = self.make_table_btn("刪除", "danger")
            btn_del.clicked.connect(lambda _, vid=v["vendor_id"], vname=v["vendor_name"]: self._delete_vendor(vid, vname))

            action_layout.addStretch()
            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_del)
            action_layout.addStretch()

            self.table.setCellWidget(r, 5, action_widget)

    def _add_vendor(self):
        dlg = VendorDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            VendorModel.create(**data)
            self._load_data()

    def _edit_vendor(self, vendor_id: int):
        v = VendorModel.get_by_id(vendor_id)
        dlg = VendorDialog(self, v)
        if dlg.exec():
            data = dlg.get_data()
            VendorModel.update(vendor_id, **data)
            self._load_data()

    def _delete_vendor(self, vendor_id: int, vendor_name: str):
        if not self.confirm(self, "確認刪除", f"確定要刪除廠商「{vendor_name}」嗎？\n此操作無法復原！"):
            return
        
        try:
            VendorModel.delete(vendor_id)
            self._load_data()
        except Exception as e:
            self.warn(self, "刪除失敗", f"無法刪除該廠商（可能已有相關的試劑或訂單資料）：\n{str(e)}")


class VendorDialog(QDialog):
    def __init__(self, parent, vendor: dict = None):
        super().__init__(parent)
        self.setWindowTitle("廠商資料")
        self.setFixedWidth(400)
        self.setStyleSheet(parent.styleSheet())
        form = QFormLayout(self)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        self.f_name = QLineEdit(vendor["vendor_name"] if vendor else "")
        self.f_sales = QLineEdit(vendor["sales_rep"] or "" if vendor else "")
        self.f_contact = QLineEdit(vendor["order_contact"] or "" if vendor else "")
        self.f_phone = QLineEdit(vendor["phone"] or "" if vendor else "")
        self.f_email = QLineEdit(vendor["email"] or "" if vendor else "")

        form.addRow("廠商名稱 *", self.f_name)
        form.addRow("業務", self.f_sales)
        form.addRow("訂藥窗口", self.f_contact)
        form.addRow("電話", self.f_phone)
        form.addRow("Email", self.f_email)

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
            QMessageBox.warning(self, "驗證", "廠商名稱為必填")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "vendor_name":   self.f_name.text().strip(),
            "sales_rep":     self.f_sales.text().strip() or None,
            "order_contact": self.f_contact.text().strip() or None,
            "phone":         self.f_phone.text().strip() or None,
            "email":         self.f_email.text().strip() or None,
        }
