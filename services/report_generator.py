# services/report_generator.py — A4 報表產生器 (QPainter 修復版)

import os
import tempfile
import traceback
import barcode
from barcode.writer import ImageWriter
from PyQt6.QtCore import QRect, Qt, QMarginsF
from PyQt6.QtGui import QPainter, QFont, QImage, QPageSize, QPageLayout, QColor, QPen
from PyQt6.QtPrintSupport import QPrinter
from database.models.purchase_order import PurchaseOrderModel

class ReportGenerator:
    @staticmethod
    def generate_po_pdf(po_data: dict, output_path: str) -> bool:
        """
        使用 QPainter 繪製精確的 A4 訂購單 PDF。
        """
        actual_barcode_path = None
        try:
            po_id = po_data["po_id"]
            items = PurchaseOrderModel.get_items(po_id)
            
            # 1. 產生一維條碼圖片 (Code 128)
            writer = ImageWriter()
            ean = barcode.get('code128', po_data["po_code"], writer=writer)
            tmp_dir = tempfile.gettempdir()
            barcode_filename = f"barcode_{po_data['po_code']}"
            full_tmp_path = os.path.join(tmp_dir, barcode_filename)
            actual_barcode_path = ean.save(full_tmp_path, options={"write_text": False})
            
            # 2. 設定 Printer 與 Painter
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(output_path)
            
            page_size = QPageSize(QPageSize.PageSizeId.A4)
            layout = QPageLayout(page_size, QPageLayout.Orientation.Portrait, QMarginsF(20, 20, 20, 20))
            printer.setPageLayout(layout)
            
            painter = QPainter(printer)
            rect = printer.pageRect(QPrinter.Unit.DevicePixel)
            w = rect.width()
            h = rect.height()
            
            scale = w / 210.0
            def _mm(mm): return int(mm * scale)
            
            def set_font(size_mm, bold=False):
                font = QFont("PingFang TC")
                if bold: font.setBold(True)
                font.setPixelSize(_mm(size_mm))
                painter.setFont(font)

            # 設定實體線畫筆 (寬度 0.3mm)
            solid_pen = QPen(QColor("#000000"), _mm(0.3), Qt.PenStyle.SolidLine)
            painter.setPen(solid_pen)

            # ── 開始繪製 ──
            # 將畫布整體向右平移 10mm (1.0公分) 以確保左側邊距
            margin_left = _mm(10)
            painter.translate(margin_left, 0)
            
            # 1. 繪製條碼與文字 (右上角，中央對齊)
            img = QImage(actual_barcode_path)
            bw = _mm(45) # 寬 4.5 公分
            bh = _mm(7)  # 高 0.7 公分
            # 條碼置於右上 (扣除 margin_left 確保不會超出右側邊界)
            bx = int(w - bw - margin_left)
            by = 0
            painter.drawImage(QRect(bx, by, int(bw), int(bh)), img)
            
            # 條碼下方的文字 (對齊條碼中央)
            set_font(3)
            painter.drawText(bx, int(bh + _mm(1)), int(bw), int(_mm(5)), Qt.AlignmentFlag.AlignCenter, po_data["po_code"])

            # 2. 標題 (因為已經 translate，w 需扣除平移量來置中)
            set_font(8, True)
            painter.drawText(0, _mm(20), int(w - margin_left), _mm(12), Qt.AlignmentFlag.AlignCenter, "試 劑 訂 購 單")
            
            # 3. 基本資訊
            set_font(4.5)
            y = _mm(40)
            lh = _mm(10)
            painter.drawText(0, int(y), f"廠商：{po_data['vendor_name']}"); y += lh
            painter.drawText(0, int(y), f"訂購單號：{po_data['po_code']}"); y += lh
            painter.drawText(0, int(y), f"訂購日期：{str(po_data['created_at'])[:10]}"); y += lh
            painter.drawText(0, int(y), f"訂購人員：{po_data['creator_name']}")
            
            # 4. 表格
            y += _mm(15)
            col_ws = [_mm(20), _mm(100), _mm(25), _mm(25)]
            headers = ["項目", "品名", "需要數量", "單位"]
            
            # 表頭
            painter.setBrush(QColor("#f2f2f2"))
            painter.drawRect(0, int(y), int(sum(col_ws)), _mm(12))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            set_font(4.5, True)
            cx = 0
            for i, txt in enumerate(headers):
                painter.drawRect(int(cx), int(y), int(col_ws[i]), _mm(12)) # 實體邊框
                painter.drawText(int(cx), int(y), int(col_ws[i]), _mm(12), Qt.AlignmentFlag.AlignCenter, txt)
                cx += col_ws[i]
            
            # 表身
            y += _mm(12)
            set_font(4.5)
            for idx, item in enumerate(items, 1):
                cx = 0
                qty = float(item['ordered_qty'])
                qty_str = f"{int(qty)}" if qty == int(qty) else f"{qty}"
                vals = [str(idx), item['reagent_name'], qty_str, item['stock_unit'] or "瓶"]
                
                for i, v in enumerate(vals):
                    # 繪製實體線框
                    painter.drawRect(int(cx), int(y), int(col_ws[i]), _mm(12))
                    align = Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignLeft if i==1 else Qt.AlignmentFlag.AlignCenter)
                    px = _mm(3) if i==1 else 0
                    painter.drawText(int(cx + px), int(y), int(col_ws[i] - 2*px), _mm(12), align, str(v))
                    cx += col_ws[i]
                y += _mm(12)
                if y > _mm(250): break

            # 5. 簽名區
            y += _mm(20)
            painter.drawText(0, int(y), f"備註：____________________________________________________________________")
            y += _mm(35)
            set_font(5.5, True)
            painter.drawText(0, int(y), int(w), _mm(12), Qt.AlignmentFlag.AlignRight, "單位主管簽章：____________________")
            
            painter.end()
            
            if actual_barcode_path and os.path.exists(actual_barcode_path):
                try: os.remove(actual_barcode_path)
                except: pass
            return True
        except Exception:
            traceback.print_exc()
            return False
