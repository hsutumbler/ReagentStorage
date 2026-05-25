# services/excel_service.py — Excel 匯入與範例產生服務

import os
import traceback
from database.models.reagent import ReagentModel
from database.models.vendor import VendorModel
from database.models.unit_conversion import UnitConversionModel

class ExcelService:
    @staticmethod
    def import_reagents(file_path: str) -> tuple[int, int, str]:
        """
        匯入試劑主檔。
        回傳: (成功筆數, 失敗筆數, 錯誤訊息)
        """
        try:
            import pandas as pd
        except ImportError:
            return 0, 0, "系統尚未安裝 pandas 模組，請執行 pip install pandas openpyxl"

        success = 0
        fail = 0
        errors = []
        try:
            df = pd.read_excel(file_path)
            # 欄位映射
            # 預期欄位: 試劑名稱, 料號, 組別, 廠商, 廠牌, 保存溫度, 開封天數, 換算名稱
            for _, row in df.iterrows():
                try:
                    name = str(row.get("試劑名稱", "")).strip()
                    if not name or name == "nan": continue
                    
                    item_num = str(row.get("料號", "")) if pd.notna(row.get("料號")) else ""
                    dept_name = str(row.get("組別", "預設組別")).strip()
                    vendor_name = str(row.get("廠商", "預設廠商")).strip()
                    brand = str(row.get("廠牌", "")) if pd.notna(row.get("廠牌")) else ""
                    temp = str(row.get("保存溫度", "")) if pd.notna(row.get("保存溫度")) else ""
                    open_days = int(row.get("開封天數", 0)) if pd.notna(row.get("開封天數")) else 0
                    safety_stock = float(row.get("安全庫存", 0)) if pd.notna(row.get("安全庫存")) else 0.0
                    unit_name = str(row.get("換算名稱", "")).strip() if pd.notna(row.get("換算名稱")) else None
                    lbl_type_str = str(row.get("預設標籤類型", "一般標籤")).strip()
                    default_label_type = 2 if "QR" in lbl_type_str or "qr" in lbl_type_str else 1
                    
                    # 1. 處理組別
                    dept_id = ExcelService._get_or_create_dept(dept_name)
                    
                    # 2. 處理廠商
                    vendor_id = ExcelService._get_or_create_vendor(vendor_name)
                    
                    # 3. 處理單位換算 ID
                    unit_id = None
                    if unit_name:
                        u = UnitConversionModel.get_by_name(unit_name)
                        if u: unit_id = u["unit_id"]

                    # 4. 建立試劑
                    ReagentModel.create(
                        reagent_name=name,
                        item_number=item_num,
                        dept_id=dept_id,
                        storage_temp=temp,
                        open_days=open_days,
                        vendor_id=vendor_id,
                        brand=brand,
                        unit_id=unit_id,
                        safety_stock=safety_stock,
                        default_label_type=default_label_type
                    )
                    success += 1
                except Exception as e:
                    fail += 1
                    errors.append(f"行 {_+2}: {str(e)}")
            
            err_msg = "\n".join(errors[:5]) + ("\n..." if len(errors) > 5 else "")
            return success, fail, err_msg
            
        except Exception as e:
            return 0, 0, f"讀取檔案失敗: {str(e)}"

    @staticmethod
    def import_units(file_path: str) -> tuple[int, int, str]:
        """
        匯入單位換算。
        """
        try:
            import pandas as pd
        except ImportError:
            return 0, 0, "系統尚未安裝 pandas 模組，請執行 pip install pandas openpyxl"

        success = 0
        fail = 0
        errors = []
        try:
            df = pd.read_excel(file_path)
            for _, row in df.iterrows():
                try:
                    name = str(row.get("換算名稱", "")).strip()
                    if not name or name == "nan": continue
                    
                    stock_u = str(row.get("入庫單位", "瓶"))
                    count_u = str(row.get("盤點單位", "瓶"))
                    issue_u = str(row.get("出庫單位", "瓶"))
                    s2c = float(row.get("入庫轉盤點比例", 1))
                    s2i = float(row.get("入庫轉出庫比例", 1))
                    safety = float(row.get("安全庫存", 0))
                    
                    c2i = s2i / s2c if s2c != 0 else 0
                    
                    existing = UnitConversionModel.get_by_name(name)
                    if existing:
                        UnitConversionModel.update(
                            existing["unit_id"], name, stock_u, count_u, issue_u, s2c, c2i, safety
                        )
                    else:
                        UnitConversionModel.create(
                            name, stock_u, count_u, issue_u, s2c, c2i, safety
                        )
                    success += 1
                except Exception as e:
                    fail += 1
                    errors.append(f"行 {_+2}: {str(e)}")
            
            err_msg = "\n".join(errors[:5]) + ("\n..." if len(errors) > 5 else "")
            return success, fail, err_msg
        except Exception as e:
            return 0, 0, f"讀取檔案失敗: {str(e)}"

    @staticmethod
    def generate_reagent_template(output_path: str) -> bool:
        try:
            import pandas as pd
            df = pd.DataFrame(columns=[
                "試劑名稱", "料號", "組別", "廠商", "廠牌", "保存溫度", "開封天數", "安全庫存", "換算名稱", "預設標籤類型"
            ])
            df.loc[0] = ["範例試劑-AFP", "REF-001", "生化組", "醫全", "Abbott", "2-8°C", 30, 10.0, "AFP-100T", "一般標籤"]
            df.loc[1] = ["範例試劑-HIV", "REF-002", "血清組", "醫全", "Roche", "2-8°C", 45, 5.0, "HIV-100T", "QR Code 標籤"]
            df.to_excel(output_path, index=False)
            return True
        except Exception:
            return False

    @staticmethod
    def generate_unit_template(output_path: str) -> bool:
        try:
            import pandas as pd
            df = pd.DataFrame(columns=[
                "換算名稱", "入庫單位", "盤點單位", "出庫單位", "入庫轉盤點比例", "入庫轉出庫比例", "安全庫存"
            ])
            df.loc[0] = ["AFP-100T", "箱", "盒", "瓶", 1, 10, 2]
            df.to_excel(output_path, index=False)
            return True
        except Exception:
            return False

    @staticmethod
    def _get_or_create_dept(name: str) -> int:
        from database.connection import DBContext
        with DBContext() as (_, c):
            c.execute("SELECT dept_id FROM departments WHERE dept_name=%s", (name,))
            row = c.fetchone()
            if row: return row["dept_id"]
            
            c.execute("INSERT INTO departments (dept_name) VALUES (%s)", (name,))
            return c.lastrowid

    @staticmethod
    def _get_or_create_vendor(name: str) -> int:
        from database.models.vendor import VendorModel
        from database.connection import DBContext
        with DBContext() as (_, c):
            c.execute("SELECT vendor_id FROM vendors WHERE vendor_name=%s", (name,))
            row = c.fetchone()
            if row: return row["vendor_id"]
            
            return VendorModel.create(name, "", "", "", "")
