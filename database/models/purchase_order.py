# database/models/purchase_order.py — 訂購單資料存取層

from database.connection import DBContext


class PurchaseOrderModel:

    @staticmethod
    def create(po_code, vendor_id, dept_id, created_by) -> int:
        with DBContext() as (_, c):
            c.execute(
                "INSERT INTO purchase_orders (po_code, vendor_id, dept_id, created_by) "
                "VALUES (%s,%s,%s,%s)",
                (po_code, vendor_id, dept_id, created_by),
            )
            return c.lastrowid

    @staticmethod
    def add_item(po_id, reagent_id, ordered_qty) -> int:
        with DBContext() as (_, c):
            c.execute(
                "INSERT INTO purchase_order_items (po_id, reagent_id, ordered_qty) "
                "VALUES (%s,%s,%s)",
                (po_id, reagent_id, ordered_qty),
            )
            return c.lastrowid

    @staticmethod
    def get_by_code(po_code: str) -> dict | None:
        with DBContext() as (_, c):
            c.execute(
                "SELECT po.*, v.vendor_name, d.dept_name, "
                "       (SELECT MIN(received_date) FROM inventory WHERE po_id = po.po_id) as received_date "
                "FROM purchase_orders po "
                "JOIN vendors v ON po.vendor_id = v.vendor_id "
                "JOIN departments d ON po.dept_id = d.dept_id "
                "WHERE po.po_code=%s",
                (po_code,),
            )
            return c.fetchone()

    @staticmethod
    def get_items(po_id: int) -> list[dict]:
        with DBContext() as (_, c):
            c.execute(
                "SELECT poi.*, r.reagent_name, r.item_number, u.stock_unit "
                "FROM purchase_order_items poi "
                "JOIN reagents r ON poi.reagent_id = r.reagent_id "
                "LEFT JOIN unit_conversions u ON r.unit_id = u.unit_id "
                "WHERE poi.po_id=%s",
                (po_id,),
            )
            return c.fetchall()

    @staticmethod
    def update_received_qty(po_item_id: int, received_qty: float) -> None:
        with DBContext() as (_, c):
            c.execute(
                "UPDATE purchase_order_items SET received_qty=%s WHERE po_item_id=%s",
                (received_qty, po_item_id),
            )

    @staticmethod
    def set_status(po_id: int, status: int) -> None:
        with DBContext() as (_, c):
            c.execute(
                "UPDATE purchase_orders SET status=%s WHERE po_id=%s",
                (status, po_id),
            )

    @staticmethod
    def query_orders(vendor_id=None, dept_id=None,
                     date_from=None, date_to=None) -> list[dict]:
        sql = """
            SELECT po.*, v.vendor_name, d.dept_name, u.name as creator_name
            FROM purchase_orders po
            JOIN vendors v ON po.vendor_id = v.vendor_id
            JOIN departments d ON po.dept_id = d.dept_id
            JOIN users u ON po.created_by = u.user_id
            WHERE 1=1
        """
        params = []
        if vendor_id:
            sql += " AND po.vendor_id=%s"; params.append(vendor_id)
        if dept_id:
            sql += " AND po.dept_id=%s"; params.append(dept_id)
        if date_from:
            sql += " AND DATE(po.created_at)>=%s"; params.append(date_from)
        if date_to:
            sql += " AND DATE(po.created_at)<=%s"; params.append(date_to)
        sql += " ORDER BY po.created_at DESC"
        with DBContext() as (_, c):
            c.execute(sql, params)
            return c.fetchall()
