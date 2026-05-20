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
    def query_all(query="", date_from=None, date_to=None) -> list[dict]:
        params = []
        where = []
        
        if query:
            where.append("(sa.reagent_name LIKE %s OR sa.rid LIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])
            
        if date_from:
            where.append("DATE(sa.adjusted_at) >= %s")
            params.append(date_from)
            
        if date_to:
            where.append("DATE(sa.adjusted_at) <= %s")
            params.append(date_to)

        where_sql = " WHERE " + " AND ".join(where) if where else ""
        
        sql = f"""
            SELECT sa.*, u.name as adjuster_name
            FROM stock_adjustments sa
            JOIN users u ON sa.adjusted_by = u.user_id
            {where_sql}
            ORDER BY sa.adjusted_at DESC
        """
        with DBContext() as (_, c):
            c.execute(sql, params)
            return c.fetchall()
