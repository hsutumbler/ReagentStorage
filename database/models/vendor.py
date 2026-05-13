# database/models/vendor.py — 廠商資料存取層

from database.connection import DBContext


class VendorModel:

    @staticmethod
    def get_all(active_only=True) -> list[dict]:
        sql = "SELECT * FROM vendors"
        if active_only:
            sql += " WHERE is_active=TRUE"
        sql += " ORDER BY vendor_name"
        with DBContext() as (_, c):
            c.execute(sql)
            return c.fetchall()

    @staticmethod
    def get_by_id(vendor_id: int) -> dict | None:
        with DBContext() as (_, c):
            c.execute("SELECT * FROM vendors WHERE vendor_id=%s", (vendor_id,))
            return c.fetchone()

    @staticmethod
    def create(vendor_name, sales_rep, order_contact, phone, email) -> int:
        with DBContext() as (_, c):
            c.execute(
                "INSERT INTO vendors (vendor_name, sales_rep, order_contact, phone, email) "
                "VALUES (%s,%s,%s,%s,%s)",
                (vendor_name, sales_rep, order_contact, phone, email),
            )
            return c.lastrowid

    @staticmethod
    def update(vendor_id, vendor_name, sales_rep, order_contact, phone, email) -> None:
        with DBContext() as (_, c):
            c.execute(
                "UPDATE vendors SET vendor_name=%s, sales_rep=%s, "
                "order_contact=%s, phone=%s, email=%s WHERE vendor_id=%s",
                (vendor_name, sales_rep, order_contact, phone, email, vendor_id),
            )

    @staticmethod
    def deactivate(vendor_id: int) -> None:
        with DBContext() as (_, c):
            c.execute("UPDATE vendors SET is_active=FALSE WHERE vendor_id=%s", (vendor_id,))

    @staticmethod
    def delete(vendor_id: int) -> None:
        with DBContext() as (_, c):
            c.execute("DELETE FROM vendors WHERE vendor_id=%s", (vendor_id,))
