# database/connection.py — MySQL 連線池管理與離線 Mock 機制

import mysql.connector
from mysql.connector import pooling, Error
from config import DB_CONFIG, POOL_CONFIG


class MockRow(dict):
    """
    虛擬資料列類別，繼承自 dict。
    - 在 boolean 判斷中 (例如 `if row:`) 預設等價於空字典 (即 False)。
    - 但當呼叫任何鍵值 (例如 `row["cnt"]` 或 `row["max_exp"]`) 時，
      即使該鍵不存在，也會安全地回傳預設值（特定欄位回傳 None，其他回傳 0），防止拋出 KeyError / TypeError。
    """
    def __missing__(self, key):
        if key in ("max_exp", "exp_date", "manufacture_date", "unit_name", 
                   "vendor_name", "dept_name", "brand", "reagent_name", 
                   "item_number", "storage_temp", "po_code", "status_label", 
                   "role_label", "name", "password_hash", "employee_id"):
            return None
        return 0

    def get(self, key, default=None):
        if key in self:
            return super().get(key)
        return self.__missing__(key)


class MockCursor:
    """虛擬資料庫 Cursor。"""
    def __init__(self, dictionary=True):
        self.dictionary = dictionary
        self.lastrowid = 1
        self.rowcount = 0
        self._last_sql = ""

    def execute(self, sql, params=None):
        self._last_sql = sql.upper() if sql else ""

    def fetchone(self):
        # 如果是聚合查詢（COUNT, MAX, MIN, SUM, AVG），回傳 MockRow
        if any(x in self._last_sql for x in ("COUNT(", "MAX(", "MIN(", "SUM(", "AVG(")):
            return MockRow()
        # 其他一般的查詢，回傳 None（表示查無此資料，以符合 model 中的 if not row 判定）
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


class MockConnection:
    """虛擬資料庫 Connection。"""
    def cursor(self, dictionary=True):
        return MockCursor(dictionary=dictionary)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class DatabasePool:
    """單例連線池，確保整個應用程式共用同一個 pool。"""
    _pool: pooling.MySQLConnectionPool | None = None
    _offline_mode: bool = False

    @classmethod
    def set_offline_mode(cls, offline: bool):
        cls._offline_mode = offline
        if offline:
            cls._pool = None

    @classmethod
    def get_pool(cls) -> pooling.MySQLConnectionPool:
        if cls._offline_mode:
            raise ConnectionError("目前處於離線模式，無法建立資料庫連線池。")
        if cls._pool is None:
            try:
                cls._pool = pooling.MySQLConnectionPool(
                    **POOL_CONFIG,
                    **DB_CONFIG,
                )
            except Error as e:
                raise ConnectionError(f"無法建立資料庫連線池：{e}") from e
        return cls._pool

    @classmethod
    def get_connection(cls):
        """取得一個連線（記得呼叫 .close() 歸還至 pool）。"""
        if cls._offline_mode:
            return MockConnection()
        try:
            return cls.get_pool().get_connection()
        except Exception:
            cls._offline_mode = True
            return MockConnection()

    @classmethod
    def close_pool(cls):
        """應用程式結束時呼叫，釋放連線池。"""
        if cls._pool:
            cls._pool = None


class DBContext:
    """
    Context manager：自動取得/歸還連線，並處理 commit/rollback。

    使用方式：
        with DBContext() as (conn, cursor):
            cursor.execute(...)
    """
    def __init__(self, dictionary=True):
        self._dictionary = dictionary
        self._conn = None
        self._cursor = None

    def __enter__(self):
        self._conn = DatabasePool.get_connection()
        self._cursor = self._conn.cursor(dictionary=self._dictionary)
        return self._conn, self._cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn is not None and self._cursor is not None:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
            self._cursor.close()
            self._conn.close()   # 歸還至 pool
        return False         # 不吞掉例外


def test_connection() -> bool:
    """測試資料庫連線是否正常，回傳 True/False。"""
    try:
        # 測試真實連線時，直接嘗試建立獨立連線以繞過全域 _offline_mode
        pool = pooling.MySQLConnectionPool(
            **POOL_CONFIG,
            **DB_CONFIG,
        )
        conn = pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 AS ok")
        cursor.fetchone()
        cursor.close()
        conn.close()
        # 測試成功，還原為連線模式並共用此 pool
        DatabasePool._pool = pool
        DatabasePool._offline_mode = False
        return True
    except Exception as e:
        print(f"\n[❌ 連線失敗詳細錯誤] {e}\n")
        DatabasePool._offline_mode = True
        DatabasePool._pool = None
        return False
