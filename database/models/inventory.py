# database/models/inventory.py — 庫存資料存取層

from datetime import date, timedelta
from database.connection import DBContext


class InventoryModel:

    @staticmethod
    def insert(rid, reagent_id, lot_number, expiry_date, received_date,
               received_by, receive_mode=1, po_id=None) -> int:
        with DBContext() as (_, c):
            c.execute(
                "INSERT INTO inventory "
                "(rid, reagent_id, lot_number, expiry_date, received_date, "
                " received_by, receive_mode, po_id) "
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (rid, reagent_id, lot_number, expiry_date, received_date,
                 received_by, receive_mode, po_id),
            )
            return c.lastrowid

    @staticmethod
    def get_receipt_history(po_id: int, reagent_id: int) -> list[dict]:
        """查詢特定訂購單內，某項試劑的歷史分批入庫紀錄。"""
        with DBContext() as (_, c):
            c.execute(
                "SELECT lot_number, expiry_date, COUNT(*) as received_qty "
                "FROM inventory "
                "WHERE po_id=%s AND reagent_id=%s "
                "GROUP BY lot_number, expiry_date "
                "ORDER BY MIN(received_date), lot_number",
                (po_id, reagent_id),
            )
            return c.fetchall()

    @staticmethod
    def get_by_rid(rid: str) -> dict | None:
        sql = """
            SELECT i.*, r.reagent_name, r.open_days, r.storage_temp,
                   r.default_label_type, v.vendor_name
            FROM inventory i
            JOIN reagents r ON i.reagent_id = r.reagent_id
            JOIN vendors v ON r.vendor_id = v.vendor_id
            WHERE i.rid=%s
        """
        with DBContext() as (_, c):
            c.execute(sql, (rid,))
            return c.fetchone()

    @staticmethod
    def is_first_bottle_of_lot(rid: str) -> bool:
        """判斷該瓶試劑是否為同批號中最早入庫的第一瓶（用於還原 NEW 標記）"""
        with DBContext() as (_, c):
            c.execute("SELECT reagent_id, lot_number, inventory_id FROM inventory WHERE rid = %s", (rid,))
            row = c.fetchone()
            if not row:
                return False
            
            c.execute(
                "SELECT MIN(inventory_id) as min_id FROM inventory WHERE reagent_id = %s AND lot_number = %s",
                (row["reagent_id"], row["lot_number"])
            )
            res = c.fetchone()
            return res and res["min_id"] == row["inventory_id"]

    @staticmethod
    def issue(inventory_id: int, issued_by: int, issue_mode: int,
              open_expiry_date: date, printed_expiry_date: date) -> None:
        with DBContext() as (_, c):
            c.execute(
                "UPDATE inventory SET status=1, issued_at=NOW(), issued_by=%s, "
                "issue_mode=%s, open_expiry_date=%s, printed_expiry_date=%s "
                "WHERE inventory_id=%s",
                (issued_by, issue_mode, open_expiry_date, printed_expiry_date, inventory_id),
            )

    @staticmethod
    def mark_adjusted(inventory_id: int) -> None:
        with DBContext() as (_, c):
            c.execute(
                "UPDATE inventory SET status=2 WHERE inventory_id=%s",
                (inventory_id,),
            )

    @staticmethod
    def get_in_stock(reagent_id: int) -> list[dict]:
        """查詢指定試劑所有在庫庫存，依效期排序（FEFO）。"""
        with DBContext() as (_, c):
            c.execute(
                "SELECT * FROM inventory WHERE reagent_id=%s AND status=0 "
                "ORDER BY expiry_date ASC, received_date ASC",
                (reagent_id,),
            )
            return c.fetchall()

    @staticmethod
    def check_fefo(rid: str) -> list[dict]:
        """
        FEFO 檢查：查詢同試劑是否有效期更早（更緊迫）的在庫庫存。
        回傳效期比指定 RID 更早的清單。
        """
        item = InventoryModel.get_by_rid(rid)
        if not item:
            return []
        with DBContext() as (_, c):
            c.execute(
                "SELECT * FROM inventory "
                "WHERE reagent_id=%s AND status=0 AND inventory_id!=%s "
                "AND expiry_date < %s "
                "ORDER BY expiry_date ASC",
                (item["reagent_id"], item["inventory_id"], item["expiry_date"]),
            )
            return c.fetchall()

    @staticmethod
    def check_lot_duplicate(reagent_id: int, lot_number: str) -> bool:
        """批號重複檢查：回傳 True 表示曾用過此批號。"""
        with DBContext() as (_, c):
            c.execute(
                "SELECT COUNT(*) as cnt FROM inventory "
                "WHERE reagent_id=%s AND lot_number=%s",
                (reagent_id, lot_number),
            )
            row = c.fetchone()
            return row["cnt"] > 0

    @staticmethod
    def check_expiry_earlier(reagent_id: int, expiry_date: date) -> bool:
        """
        效期比現存批號更早的檢查：
        回傳 True 表示有在庫項目的效期比新入庫的效期更晚（即新批號效期更短）。
        """
        with DBContext() as (_, c):
            c.execute(
                "SELECT MAX(expiry_date) as max_exp FROM inventory "
                "WHERE reagent_id=%s AND status=0",
                (reagent_id,),
            )
            row = c.fetchone()
            if row["max_exp"] is None:
                return False
            return expiry_date < row["max_exp"]

    @staticmethod
    def get_current_stock_count(reagent_id: int) -> int:
        """回傳指定試劑的在庫數量（瓶數）。"""
        with DBContext() as (_, c):
            c.execute(
                "SELECT COUNT(*) as cnt FROM inventory "
                "WHERE reagent_id=%s AND status=0",
                (reagent_id,),
            )
            return c.fetchone()["cnt"]

    @staticmethod
    def filter_inventory(vendor_id=None, dept_id=None,
                          reagent_id=None, status=0) -> list[dict]:
        """調整庫存用的篩選查詢。"""
        sql = """
            SELECT i.*, r.reagent_name, r.item_number, v.vendor_name, d.dept_name
            FROM inventory i
            JOIN reagents r ON i.reagent_id = r.reagent_id
            JOIN vendors v ON r.vendor_id = v.vendor_id
            JOIN departments d ON r.dept_id = d.dept_id
            WHERE i.status=%s
        """
        params = [status]
        if vendor_id:
            sql += " AND r.vendor_id=%s"
            params.append(vendor_id)
        if dept_id:
            sql += " AND r.dept_id=%s"
            params.append(dept_id)
        if reagent_id:
            sql += " AND i.reagent_id=%s"
            params.append(reagent_id)
        sql += " ORDER BY r.reagent_name, i.expiry_date"
        with DBContext() as (_, c):
            c.execute(sql, params)
            return c.fetchall()

    @staticmethod
    def trace_query(vendor_id=None, dept_id=None, reagent_id=None,
                    date_from=None, date_to=None, rid=None, lot_number=None,
                    status=None, issue_from=None, issue_to=None) -> list[dict]:
        """庫存追溯查詢（含過往出入庫記錄）。"""
        sql = """
            SELECT i.*, r.reagent_name, v.vendor_name, d.dept_name,
                   u1.name AS received_by_name,
                   u2.name AS issued_by_name
            FROM inventory i
            JOIN reagents r ON i.reagent_id = r.reagent_id
            JOIN vendors v ON r.vendor_id = v.vendor_id
            JOIN departments d ON r.dept_id = d.dept_id
            LEFT JOIN users u1 ON i.received_by = u1.user_id
            LEFT JOIN users u2 ON i.issued_by = u2.user_id
            WHERE 1=1
        """
        params = []
        if vendor_id:
            sql += " AND r.vendor_id=%s"; params.append(vendor_id)
        if dept_id:
            sql += " AND r.dept_id=%s"; params.append(dept_id)
        if reagent_id:
            sql += " AND i.reagent_id=%s"; params.append(reagent_id)
        if date_from:
            sql += " AND i.received_date>=%s"; params.append(date_from)
        if date_to:
            sql += " AND i.received_date<=%s"; params.append(date_to)
        if rid:
            sql += " AND i.rid LIKE %s"; params.append(f"%{rid}%")
        if lot_number:
            sql += " AND i.lot_number LIKE %s"; params.append(f"%{lot_number}%")
        if status is not None:
            sql += " AND i.status=%s"; params.append(status)
        if issue_from:
            sql += " AND DATE(i.issued_at)>=%s"; params.append(issue_from)
        if issue_to:
            sql += " AND DATE(i.issued_at)<=%s"; params.append(issue_to)
            
        sql += " ORDER BY i.received_date DESC, i.rid"
        with DBContext() as (_, c):
            c.execute(sql, params)
            return c.fetchall()

    # ── 儀表板專用查詢 ──────────────────────────────────────

    @staticmethod
    def get_expired_in_stock() -> list[dict]:
        """取得所有已過期但仍在庫的試劑明細。"""
        sql = """
            SELECT i.inventory_id, i.rid, i.lot_number, i.expiry_date,
                   r.reagent_name, r.item_number, d.dept_name,
                   DATEDIFF(CURDATE(), i.expiry_date) AS days_overdue
            FROM inventory i
            JOIN reagents r ON i.reagent_id = r.reagent_id
            JOIN departments d ON r.dept_id = d.dept_id
            WHERE i.status = 0 AND i.expiry_date < CURDATE()
            ORDER BY i.expiry_date ASC, r.reagent_name
        """
        with DBContext() as (_, c):
            c.execute(sql)
            return c.fetchall()

    @staticmethod
    def get_expiring_soon_in_stock(days: int = 30) -> list[dict]:
        """取得即將在指定天數內到期的在庫試劑明細。"""
        sql = """
            SELECT i.inventory_id, i.rid, i.lot_number, i.expiry_date,
                   r.reagent_name, r.item_number, d.dept_name,
                   DATEDIFF(i.expiry_date, CURDATE()) AS days_remaining
            FROM inventory i
            JOIN reagents r ON i.reagent_id = r.reagent_id
            JOIN departments d ON r.dept_id = d.dept_id
            WHERE i.status = 0
              AND i.expiry_date >= CURDATE()
              AND i.expiry_date <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
            ORDER BY i.expiry_date ASC, r.reagent_name
        """
        with DBContext() as (_, c):
            c.execute(sql, (days,))
            return c.fetchall()

    @staticmethod
    def get_low_stock_reagents() -> list[dict]:
        """取得所有目前庫存低於安全庫存量的試劑清單。優先採用單位換算設定的安全庫存。"""
        sql = """
            SELECT r.reagent_id, r.reagent_name, r.item_number,
                   r.safety_stock, 
                   u.count_unit, u.stock_to_count, d.dept_name,
                   COUNT(i.inventory_id) AS current_stock_bottles,
                   COUNT(i.inventory_id) * COALESCE(u.stock_to_count, 1) AS current_stock_count
            FROM reagents r
            LEFT JOIN unit_conversions u ON r.unit_id = u.unit_id
            LEFT JOIN inventory i ON r.reagent_id = i.reagent_id AND i.status = 0
            JOIN departments d ON r.dept_id = d.dept_id
            GROUP BY r.reagent_id, r.reagent_name, r.item_number,
                     r.safety_stock, u.count_unit, u.stock_to_count, d.dept_name
            HAVING current_stock_count <= r.safety_stock
            ORDER BY (r.safety_stock - current_stock_count) DESC, r.reagent_name
        """
        with DBContext() as (_, c):
            c.execute(sql)
            return c.fetchall()
