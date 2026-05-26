# database/connection.py — MySQL 連線與斷線模擬器

import mysql.connector
from mysql.connector import pooling, Error
from config import DB_CONFIG, POOL_CONFIG

# 連線狀態旗標，預設未連線
IS_CONNECTED = False


class DummyCursor:
    """模擬游標，用於未連線狀態，所有執行皆回傳空值，防止介面崩潰。"""
    def execute(self, sql, params=None):
        return self

    @property
    def lastrowid(self):
        return 1

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def close(self):
        pass


class DummyConnection:
    """模擬連線，用於未連線狀態。"""
    def cursor(self, dictionary=True):
        return DummyCursor()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class DatabasePool:
    """單例連線池，確保整個應用程式共用同一個 pool。"""
    _pool: pooling.MySQLConnectionPool | None = None

    @classmethod
    def get_pool(cls) -> pooling.MySQLConnectionPool:
        if cls._pool is None:
            try:
                cls._pool = pooling.MySQLConnectionPool(
                    use_pure=True,
                    **POOL_CONFIG,
                    **DB_CONFIG,
                )
            except Error as e:
                raise ConnectionError(f"無法建立資料庫連線池：{e}") from e
        return cls._pool

    @classmethod
    def get_connection(cls):
        """取得一個連線（記得呼叫 .close() 歸還至 pool）。"""
        return cls.get_pool().get_connection()

    @classmethod
    def close_pool(cls):
        """應用程式結束時呼叫，釋放連線池。"""
        if cls._pool:
            cls._pool = None


class DBContext:
    """
    Context manager：自動取得/歸還連線，並處理 commit/rollback。
    """
    def __init__(self, dictionary=True):
        self._dictionary = dictionary
        self._conn = None
        self._cursor = None

    def __enter__(self):
        global IS_CONNECTED
        if not IS_CONNECTED:
            self._conn = DummyConnection()
            self._cursor = DummyCursor()
            return self._conn, self._cursor
            
        try:
            self._conn = DatabasePool.get_connection()
            self._cursor = self._conn.cursor(dictionary=self._dictionary)
            return self._conn, self._cursor
        except Exception:
            # 如果連線中斷，自動切換至未連線模式並返回模擬物件
            IS_CONNECTED = False
            self._conn = DummyConnection()
            self._cursor = DummyCursor()
            return self._conn, self._cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn is None:
            return False
            
        if isinstance(self._conn, DummyConnection):
            return False
            
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
            self._cursor.close()
            self._conn.close()
        except Exception:
            pass
        return False


def test_connection() -> bool:
    """測試資料庫連線是否正常，回傳 True/False。"""
    global IS_CONNECTED
    try:
        conn = DatabasePool.get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT 1 AS ok")
        cursor.fetchone()
        cursor.close()
        conn.close()
        IS_CONNECTED = True
        return True
    except Exception as e:
        import sys
        try:
            encoding = sys.stdout.encoding or "utf-8"
            err_msg = str(e).encode(encoding, errors="replace").decode(encoding)
        except Exception:
            err_msg = str(e)
        print(f"\n[ERROR 連線失敗詳細錯誤] {err_msg}\n", flush=True)
        IS_CONNECTED = False
        return False
