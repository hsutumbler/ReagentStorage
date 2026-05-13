# database/models/stock_adjustment.py

from database.connection import DBContext


class StockAdjustmentModel:

    @staticmethod
    def record(inventory_id, rid, reagent_name, lot_number,
               expiry_date, received_date, adjusted_by, reason="") -> int:
        with DBContext() as (_, c):
            c.execute(
                "INSERT INTO stock_adjustments "
                "(inventory_id, rid, reagent_name, lot_number, "
                " expiry_date, received_date, adjusted_by, reason) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (inventory_id, rid, reagent_name, lot_number,
                 expiry_date, received_date, adjusted_by, reason),
            )
            return c.lastrowid

    @staticmethod
    def query_all() -> list[dict]:
        sql = """
            SELECT sa.*, u.name as adjuster_name
            FROM stock_adjustments sa
            JOIN users u ON sa.adjusted_by = u.user_id
            ORDER BY sa.adjusted_at DESC
        """
        with DBContext() as (_, c):
            c.execute(sql)
            return c.fetchall()
