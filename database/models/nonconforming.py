# database/models/nonconforming.py — 不合格試劑記錄

from database.connection import DBContext


class NonConformingModel:

    @staticmethod
    def create(vendor_id, reagent_id, lot_number, expiry_date,
               nc_reason, recorded_by) -> int:
        with DBContext() as (_, c):
            c.execute(
                "INSERT INTO nonconforming_reagents "
                "(vendor_id, reagent_id, lot_number, expiry_date, nc_reason, recorded_by) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (vendor_id, reagent_id, lot_number, expiry_date, nc_reason, recorded_by),
            )
            return c.lastrowid

    @staticmethod
    def query(vendor_id=None, reagent_id=None,
              date_from=None, date_to=None) -> list[dict]:
        sql = """
            SELECT nc.*, v.vendor_name, r.reagent_name, u.name as recorder_name
            FROM nonconforming_reagents nc
            JOIN vendors v ON nc.vendor_id = v.vendor_id
            JOIN reagents r ON nc.reagent_id = r.reagent_id
            JOIN users u ON nc.recorded_by = u.user_id
            WHERE 1=1
        """
        params = []
        if vendor_id:
            sql += " AND nc.vendor_id=%s"; params.append(vendor_id)
        if reagent_id:
            sql += " AND nc.reagent_id=%s"; params.append(reagent_id)
        if date_from:
            sql += " AND DATE(nc.recorded_at)>=%s"; params.append(date_from)
        if date_to:
            sql += " AND DATE(nc.recorded_at)<=%s"; params.append(date_to)
        sql += " ORDER BY nc.recorded_at DESC"
        with DBContext() as (_, c):
            c.execute(sql, params)
            return c.fetchall()
