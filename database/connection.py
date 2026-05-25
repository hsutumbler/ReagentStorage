# database/connection.py — MySQL 連線池管理

import mysql.connector
from mysql.connector import pooling, Error
from config import DB_CONFIG, POOL_CONFIG


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
            # mysql-connector-python 的 pool 在 GC 時自動關閉
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
        with DBContext() as (conn, cursor):
            cursor.execute("SELECT 1 AS ok")
            cursor.fetchone()   # 必須讀取，否則 commit 時報 Unread result
        return True
    except Exception as e:
        import sys
        try:
            encoding = sys.stdout.encoding or "utf-8"
            err_msg = str(e).encode(encoding, errors="replace").decode(encoding)
        except Exception:
            err_msg = str(e)
        print(f"\n[ERROR 連線失敗詳細錯誤] {err_msg}\n", flush=True)
        return False
