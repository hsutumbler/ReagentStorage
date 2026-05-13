# database/models/reagent.py — 試劑主檔資料存取層

from database.connection import DBContext


class ReagentModel:

    @staticmethod
    def get_all(active_only=True) -> list[dict]:
        sql = """
            SELECT DISTINCT r.*, v.vendor_name, d.dept_name, u.unit_name,
                   u.stock_unit, u.count_unit, u.issue_unit,
                   u.stock_to_count, u.count_to_issue,
                   u.safety_stock
            FROM reagents r
            LEFT JOIN vendors v ON r.vendor_id = v.vendor_id
            LEFT JOIN departments d ON r.dept_id = d.dept_id
            LEFT JOIN unit_conversions u ON r.unit_id = u.unit_id
        """
        if active_only:
            sql += " WHERE r.is_active=TRUE"
        sql += " ORDER BY r.reagent_name"
        with DBContext() as (_, c):
            c.execute(sql)
            return c.fetchall()

    @staticmethod
    def get_by_id(reagent_id: int) -> dict | None:
        sql = """
            SELECT r.*, v.vendor_name, d.dept_name, u.unit_name,
                   u.stock_unit, u.count_unit, u.issue_unit,
                   u.stock_to_count, u.count_to_issue,
                   u.safety_stock
            FROM reagents r
            LEFT JOIN vendors v ON r.vendor_id = v.vendor_id
            LEFT JOIN departments d ON r.dept_id = d.dept_id
            LEFT JOIN unit_conversions u ON r.unit_id = u.unit_id
            WHERE r.reagent_id=%s
        """
        with DBContext() as (_, c):
            c.execute(sql, (reagent_id,))
            return c.fetchone()

    @staticmethod
    def get_by_vendor_dept(vendor_id: int, dept_id: int) -> list[dict]:
        """供訂單頁面使用：查詢特定廠商+組別的試劑。"""
        sql = """
            SELECT r.*, u.count_unit, u.stock_to_count,
                   u.safety_stock
            FROM reagents r
            LEFT JOIN unit_conversions u ON r.unit_id = u.unit_id
            WHERE r.vendor_id=%s AND r.dept_id=%s AND r.is_active=TRUE
            ORDER BY r.reagent_name
        """
        with DBContext() as (_, c):
            c.execute(sql, (vendor_id, dept_id))
            return c.fetchall()

    @staticmethod
    def create(reagent_name, item_number, dept_id, storage_temp,
               open_days, vendor_id, brand, unit_id=None) -> int:
        with DBContext() as (_, c):
            c.execute(
                "INSERT INTO reagents "
                "(reagent_name, item_number, dept_id, storage_temp, "
                " open_days, vendor_id, brand, unit_id) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (reagent_name, item_number, dept_id, storage_temp,
                 open_days, vendor_id, brand, unit_id),
            )
            return c.lastrowid

    @staticmethod
    def update(reagent_id, reagent_name, item_number, dept_id, storage_temp,
               open_days, vendor_id, brand, unit_id=None) -> None:
        with DBContext() as (_, c):
            sql = """
                UPDATE reagents SET 
                    reagent_name=%s, item_number=%s, dept_id=%s, 
                    storage_temp=%s, open_days=%s, vendor_id=%s, 
                    brand=%s, unit_id=%s
                WHERE reagent_id=%s
            """
            c.execute(sql, (
                reagent_name, item_number, dept_id, storage_temp,
                open_days, vendor_id, brand, unit_id, reagent_id
            ))

    @staticmethod
    def deactivate(reagent_id: int) -> None:
        with DBContext() as (_, c):
            c.execute("UPDATE reagents SET is_active=FALSE WHERE reagent_id=%s", (reagent_id,))

    @staticmethod
    def delete(reagent_id: int) -> None:
        with DBContext() as (_, c):
            c.execute("DELETE FROM reagents WHERE reagent_id=%s", (reagent_id,))

    # ── 組別 ──
    @staticmethod
    def get_all_departments() -> list[dict]:
        with DBContext() as (_, c):
            c.execute("SELECT * FROM departments WHERE is_active=TRUE ORDER BY dept_name")
            return c.fetchall()

    @staticmethod
    def create_department(dept_name: str) -> int:
        with DBContext() as (_, c):
            c.execute("INSERT INTO departments (dept_name) VALUES (%s)", (dept_name,))
            return c.lastrowid
