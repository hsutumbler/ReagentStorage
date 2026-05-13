# ui/receiving/label_preview.py — 標籤樣式預覽對話框

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QStackedWidget, QCheckBox
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap, QPen

class LabelPreviewDialog(QDialog):
    def __init__(self, parent, reagent_name, lot, expiry, is_issue=False):
        super().__init__(parent)
        self.setWindowTitle("Zebra 標籤排版預覽")
        self.setFixedSize(600, 500)
        self.reagent_name = reagent_name
        self.lot = lot
        self.expiry = expiry
        self.is_issue = is_issue
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Zebra 標籤排版模擬")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #60c0ff;")
        layout.addWidget(title)

        # 先建立 UI 元件，再建立預覽頁面，避免 _create_... 找不到元件
        self.chk_new_lot = QCheckBox("模擬新批號樣式 (加厚邊框)")
        self.chk_new_lot.stateChanged.connect(self._refresh_previews)
        
        self.btn_large = QPushButton("一般標籤 (5x3.5cm)")
        self.btn_qr = QPushButton("QR Code 標籤 (2x3cm)") # 修正文字為 2x3
        self.btn_large.setCheckable(True)
        self.btn_qr.setCheckable(True)
        self.btn_large.setChecked(True)
        self.btn_large.clicked.connect(lambda: self._switch(0))
        self.btn_qr.clicked.connect(lambda: self._switch(1))

        # 頁籤切換：一般標籤 vs QR Code 標籤
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_large_preview())
        self.stack.addWidget(self._create_qr_preview())

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_large)
        btn_row.addWidget(self.btn_qr)
        layout.addLayout(btn_row)
        layout.addWidget(self.chk_new_lot)
        layout.addWidget(self.stack)

        close_btn = QPushButton("關閉預覽")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedHeight(40)
        layout.addWidget(close_btn)

    def _refresh_previews(self):
        # 重新建立預覽頁面以反映新批號狀態
        old_large = self.stack.widget(0)
        old_qr = self.stack.widget(1)
        self.stack.removeWidget(old_large)
        self.stack.removeWidget(old_qr)
        self.stack.insertWidget(0, self._create_large_preview())
        self.stack.insertWidget(1, self._create_qr_preview())
        self.stack.setCurrentIndex(0 if self.btn_large.isChecked() else 1)

    def _switch(self, index):
        self.stack.setCurrentIndex(index)
        self.btn_large.setChecked(index == 0)
        self.btn_qr.setChecked(index == 1)

    def _create_large_preview(self):
        # 模擬 50mm x 35mm 的標籤 (比例縮放)
        container = QFrame()
        layout = QVBoxLayout(container)
        
        canvas = QLabel()
        pixmap = QPixmap(400, 280)
        pixmap.fill(QColor("white"))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 繪製邊框
        is_new = self.chk_new_lot.isChecked()
        border_w = 8 if is_new else 2
        painter.setPen(QPen(QColor("black"), border_w))
        painter.drawRect(5, 5, 390, 270)
        
        if is_new:
            painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            painter.drawText(300, 40, "[新批號]")
        
        # 標題 (試劑名稱)
        painter.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        painter.drawText(QRectF(20, 20, 360, 40), Qt.AlignmentFlag.AlignLeft, self.reagent_name)
        
        # 分隔線
        painter.setPen(QPen(QColor("black"), 1))
        painter.drawLine(20, 65, 380, 65)
        
        # 詳細資訊
        painter.setFont(QFont("Arial", 12))
        painter.drawText(20, 80, f"RID：R240508001")  # 將 RID 移到資訊區首行
        painter.drawText(20, 105, f"批號：{self.lot}")
        
        if self.is_issue:
            painter.drawText(20, 130, f"開封：{self.expiry}")
            painter.drawText(20, 155, f"出庫：2024-05-08")
        else:
            painter.drawText(20, 130, f"穩定：{self.expiry}")
            painter.drawText(20, 155, f"入庫：2024-05-08")
        
        # 模擬條碼區 (入庫才顯示條碼)
        if not self.is_issue:
            painter.setBrush(QColor("#f0f0f0"))
            painter.drawRect(20, 180, 360, 60)
            painter.setPen(QPen(QColor("black"), 1))
            # 畫一些黑條代表條碼
            import random
            x = 30
            while x < 370:
                w = random.choice([2, 3, 5])
                painter.fillRect(x, 190, w, 40, QColor("black"))
                x += w + random.choice([2, 3])
        else:
            # 出庫標籤不印條碼也不印大字 RID，保持畫面清爽
            pass
            
        painter.setFont(QFont("Courier New", 10))
        painter.drawText(QRectF(20, 240, 360, 20), Qt.AlignmentFlag.AlignCenter, f"RID: R240508001")
        
        painter.end()
        canvas.setPixmap(pixmap)
        canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(canvas)
        return container

    def _create_qr_preview(self):
        # 模擬 20mm x 30mm 的標籤 (比例縮放)
        container = QFrame()
        layout = QVBoxLayout(container)
        
        canvas = QLabel()
        pixmap = QPixmap(200, 300) # 2:3 比例
        pixmap.fill(QColor("white"))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 繪製邊框
        is_new = self.chk_new_lot.isChecked()
        border_w = 6 if is_new else 2
        painter.setPen(QPen(QColor("black"), border_w))
        painter.drawRect(5, 5, 190, 290)
        
        if is_new:
            painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            painter.drawText(140, 30, "新")
        
        # 模擬 QR Code (1.6cm x 1.6cm 比例)
        qr_size = 160
        qr_x = (200 - qr_size) // 2
        qr_y = 20
        
        painter.setBrush(QColor("black"))
        # 繪製 QR 碼模擬
        for i in range(12):
            for j in range(12):
                if (i+j) % 3 == 0 or (i*j) % 5 == 0:
                    painter.drawRect(qr_x + 10 + i*12, qr_y + 10 + j*12, 10, 10)
        
        # QR 中央白色底與文字
        box_size = 40
        box_x = qr_x + (qr_size - box_size) // 2
        box_y = qr_y + (qr_size - box_size) // 2
        painter.fillRect(box_x, box_y, box_size, box_size, QColor("white"))
        
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        center_text = "出" if self.is_issue else "入"
        painter.drawText(QRectF(box_x, box_y, box_size, box_size), Qt.AlignmentFlag.AlignCenter, center_text)
        
        # 底部文字 (只顯示品名、效期，無提示詞)
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        painter.drawText(QRectF(10, 200, 180, 30), Qt.AlignmentFlag.AlignCenter, self.reagent_name)
        
        # 效期 yyyy/mm/dd exp
        exp_display = f"{self.expiry.replace('-', '/')} exp"
        painter.setFont(QFont("Arial", 12))
        painter.drawText(QRectF(10, 230, 180, 30), Qt.AlignmentFlag.AlignCenter, exp_display)
        
        painter.end()
        canvas.setPixmap(pixmap)
        canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(canvas)
        return container
