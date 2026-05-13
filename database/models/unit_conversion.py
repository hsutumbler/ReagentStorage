# database/models/unit_conversion.py — 單位換算主檔資料存取層

from database.connection import DBContext

class UnitConversionModel:

    @staticmethod
    def get_all() -> list[dict]:
        with DBContext() as (_, c):
            c.execute("SELECT * FROM unit_conversions ORDER BY unit_name")
            return c.fetchall()

    @staticmethod
    def get_by_name(name: str) -> dict | None:
        with DBContext() as (_, c):
            c.execute("SELECT * FROM unit_conversions WHERE unit_name=%s", (name,))
            return c.fetchone()

    @staticmethod
    def create(unit_name: str, stock_unit: str, count_unit: str, issue_unit: str,
               stock_to_count: float, count_to_issue: float, safety_stock: float) -> int:
        with DBContext() as (_, c):
            c.execute(
                "INSERT INTO unit_conversions "
                "(unit_name, stock_unit, count_unit, issue_unit, stock_to_count, count_to_issue, safety_stock) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (unit_name, stock_unit, count_unit, issue_unit, stock_to_count, count_to_issue, safety_stock)
            )
            return c.lastrowid

    @staticmethod
    def update(unit_id: int, unit_name: str, stock_unit: str, count_unit: str, issue_unit: str,
               stock_to_count: float, count_to_issue: float, safety_stock: float) -> None:
        with DBContext() as (_, c):
            c.execute(
                "UPDATE unit_conversions SET "
                "unit_name=%s, stock_unit=%s, count_unit=%s, issue_unit=%s, "
                "stock_to_count=%s, count_to_issue=%s, safety_stock=%s "
                "WHERE unit_id=%s",
                (unit_name, stock_unit, count_unit, issue_unit, stock_to_count, count_to_issue, safety_stock, unit_id)
            )

    @staticmethod
    def delete(unit_id: int) -> None:
        with DBContext() as (_, c):
            c.execute("DELETE FROM unit_conversions WHERE unit_id=%s", (unit_id,))
