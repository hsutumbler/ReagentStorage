# services/rid_generator.py — RID 與 PO 碼產生（thread-safe，資料庫鎖定確保多用戶唯一）

from datetime import date
from database.connection import DBContext


def generate_rid() -> str:
    """
    產生唯一 RID：R + yyMMDD + NNN（3碼流水號，每日重置自 001）。
    使用 MySQL 的 SELECT ... FOR UPDATE 確保多用戶端同時操作不重複。
    """
    today = date.today()
    yy = today.strftime("%y")
    mmdd = today.strftime("%m%d")
    seq_key = today.isoformat()  # YYYY-MM-DD

    with DBContext() as (_, cursor):
        # 取得或建立當日序列，並鎖定該列
        cursor.execute(
            "INSERT INTO rid_sequence (seq_date, last_seq) "
            "VALUES (%s, 1) "
            "ON DUPLICATE KEY UPDATE last_seq = last_seq + 1",
            (seq_key,),
        )
        cursor.execute(
            "SELECT last_seq FROM rid_sequence WHERE seq_date=%s",
            (seq_key,),
        )
        row = cursor.fetchone()
        seq = row["last_seq"]

    if seq > 999:
        raise OverflowError(f"今日 RID 流水號已超過 999，請聯絡系統管理員")

    return f"R{yy}{mmdd}{seq:03d}"


def generate_po_code() -> str:
    """
    產生唯一訂購單條碼：PO + yyyyMMDD + XX（2碼流水號，每日重置自 01）。
    """
    today = date.today()
    yyyymmdd = today.strftime("%Y%m%d")
    seq_key = today.isoformat()

    with DBContext() as (_, cursor):
        cursor.execute(
            "INSERT INTO po_sequence (seq_date, last_seq) "
            "VALUES (%s, 1) "
            "ON DUPLICATE KEY UPDATE last_seq = last_seq + 1",
            (seq_key,),
        )
        cursor.execute(
            "SELECT last_seq FROM po_sequence WHERE seq_date=%s",
            (seq_key,),
        )
        row = cursor.fetchone()
        seq = row["last_seq"]

    if seq > 99:
        raise OverflowError(f"今日 PO 流水號已超過 99，請聯絡系統管理員")

    return f"PO{yyyymmdd}{seq:02d}"
