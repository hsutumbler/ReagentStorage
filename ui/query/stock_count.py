from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QComboBox, QPushButton, QTableWidgetItem, QFileDialog
)
from PyQt6.QtGui import QColor, QTextDocument, QPageLayout, QPageSize
from PyQt6.QtPrintSupport import QPrinter
from ui.base_page import BasePage
from database.models.vendor import VendorModel
from database.models.reagent import ReagentModel
from database.models.inventory import InventoryModel


class StockCountPage(BasePage):
    def __init__(self, user: dict):
        super().__init__("庫存盤點", "查詢各試劑目前庫存（以盤點單位顯示）", user)
        self._data = []  # 儲存查詢結果以便列印與排序
        self._build()

    def _build(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("廠商："))
        self.cb_vendor = QComboBox()
        self.cb_vendor.addItem("全部", None)
        for v in VendorModel.get_all():
            self.cb_vendor.addItem(v["vendor_name"], v["vendor_id"])
        row.addWidget(self.cb_vendor)

        row.addWidget(QLabel("組別："))
        self.cb_dept = QComboBox()
        self.cb_dept.addItem("全部", None)
        for d in ReagentModel.get_all_departments():
            self.cb_dept.addItem(d["dept_name"], d["dept_id"])
        row.addWidget(self.cb_dept)

        row.addWidget(QLabel("排序："))
        self.cb_sort = QComboBox()
        self.cb_sort.addItem("依料號 (小→大)", "item_number")
        self.cb_sort.addItem("依名稱 (A→Z)", "reagent_name")
        self.cb_sort.currentIndexChanged.connect(self._search)
        row.addWidget(self.cb_sort)

        btn_search = QPushButton("🔍 查詢")
        btn_search.setObjectName("btn_primary")
        btn_search.clicked.connect(self._search)
        row.addWidget(btn_search)

        btn_print = QPushButton("🖨️ 列印盤點表")
        btn_print.clicked.connect(self._print_report)
        row.addWidget(btn_print)

        row.addStretch()
        self.content_layout.addLayout(row)

        headers = ["試劑名稱", "料號", "組別", "廠商", "目前庫存", "安全庫存", "盤點單位"]
        self.table = self.make_table(headers)
        self.content_layout.addWidget(self.table)
        self._search()

    def _search(self):
        vendor_id = self.cb_vendor.currentData()
        dept_id = self.cb_dept.currentData()
        sort_key = self.cb_sort.currentData()

        reagents = ReagentModel.get_all()
        if vendor_id:
            reagents = [r for r in reagents if r["vendor_id"] == vendor_id]
        if dept_id:
            reagents = [r for r in reagents if r["dept_id"] == dept_id]

        # 執行排序
        if sort_key == "item_number":
            reagents.sort(key=lambda x: (x["item_number"] or "").lower())
        else:
            reagents.sort(key=lambda x: (x["reagent_name"] or "").lower())

        self.table.setRowCount(0)
        self._data = []

        for rg in reagents:
            stock = InventoryModel.get_current_stock_count(rg["reagent_id"])
            s2c = float(rg.get("stock_to_count") or 1)
            stock_count = stock * s2c
            unit = rg.get("count_unit") or "未設"
            safety_count = float(rg.get("safety_stock") or 0) * s2c
            low = stock_count < safety_count and safety_count > 0

            row_data = [
                rg["reagent_name"], rg["item_number"] or "",
                rg["dept_name"], rg["vendor_name"],
                f"{stock_count:.1f}", f"{safety_count:.1f}", unit
            ]
            self._data.append(row_data)

            r_idx = self.table.rowCount()
            self.table.insertRow(r_idx)
            for c_idx, val in enumerate(row_data):
                item = QTableWidgetItem(str(val))
                if low:
                    item.setForeground(QColor("#e07820"))
                self.table.setItem(r_idx, c_idx, item)

    def _print_report(self):
        if not self._data:
            self.warn("提示", "目前沒有資料可供列印。")
            return

        path, _ = QFileDialog.getSaveFileName(self, "儲存盤點報表", "庫存盤點表.pdf", "PDF Files (*.pdf)")
        if not path:
            return

        # 產生 HTML 表格內容
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        html = f"""
        <html>
        <head>
            <style>
                h1 {{ text-align: center; font-family: sans-serif; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #333; padding: 8px; text-align: left; font-size: 12px; }}
                th {{ background-color: #f2f2f2; }}
                .footer {{ margin-top: 20px; font-size: 10px; color: #666; text-align: right; }}
            </style>
        </head>
        <body>
            <h1>庫存盤點報表</h1>
            <p>列印時間：{now} &nbsp;&nbsp; 盤點人員：{self.user.get('name', 'N/A')}</p>
            <table>
                <tr>
                    <th>試劑名稱</th><th>料號</th><th>組別</th><th>廠商</th>
                    <th>目前庫存</th><th>安全庫存</th><th>單位</th>
                </tr>
        """
        for row in self._data:
            html += "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>"
        
        html += """
            </table>
            <div class="footer">系統產生之自動稽核報表</div>
        </body>
        </html>
        """

        doc = QTextDocument()
        doc.setHtml(html)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QPageLayout.Margins(15, 15, 15, 15), QPageLayout.Unit.Millimeter)

        doc.print(printer)
        self.alert("列印成功", f"盤點報表已儲存至：\n{path}")
