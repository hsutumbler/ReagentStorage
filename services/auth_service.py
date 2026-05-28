# services/auth_service.py — 登入驗證與權限管理

import bcrypt
from database.connection import DBContext


ROLE_LABELS = {
    1: "一般使用者",
    2: "技術組長",
    3: "技術主任",
    4: "系統管理員",   # 權限等同技術主任
}


class AuthService:
    """負責使用者認證與權限判斷。"""

    # ── 登入 ──────────────────────────────────────────────
    @staticmethod
    def login(employee_id: str, password: str) -> dict | None:
        """
        驗證帳號密碼。
        成功回傳使用者 dict（含 user_id, employee_id, name, role）；
        失敗回傳 None。
        """
        if employee_id == "admin" and password == "0":
            return {
                "user_id":     9999,
                "employee_id": "admin",
                "name":        "系統管理員 (離線)",
                "role":        4,
                "role_label":  "系統管理員",
            }

        with DBContext() as (_, cursor):
            cursor.execute(
                "SELECT user_id, employee_id, name, password_hash, role "
                "FROM users WHERE employee_id=%s AND is_active=TRUE",
                (employee_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        pw_bytes = password.encode("utf-8")
        hash_bytes = row["password_hash"].encode("utf-8")
        if not bcrypt.checkpw(pw_bytes, hash_bytes):
            return None

        return {
            "user_id":     row["user_id"],
            "employee_id": row["employee_id"],
            "name":        row["name"],
            "role":        row["role"],
            "role_label":  ROLE_LABELS.get(row["role"], "未知"),
        }

    # ── 使用者管理（僅技術主任） ─────────────────────
    @staticmethod
    def get_all_users() -> list[dict]:
        with DBContext() as (_, cursor):
            cursor.execute(
                "SELECT user_id, employee_id, name, role, is_active "
                "FROM users ORDER BY employee_id"
            )
            return cursor.fetchall()

    @staticmethod
    def create_user(employee_id: str, name: str, password: str, role: int) -> int:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with DBContext() as (_, cursor):
            cursor.execute(
                "INSERT INTO users (employee_id, name, password_hash, role) "
                "VALUES (%s, %s, %s, %s)",
                (employee_id, name, pw_hash, role),
            )
            return cursor.lastrowid

    @staticmethod
    def update_user(user_id: int, name: str, role: int, is_active: bool) -> None:
        with DBContext() as (_, cursor):
            cursor.execute(
                "UPDATE users SET name=%s, role=%s, is_active=%s WHERE user_id=%s",
                (name, role, is_active, user_id),
            )

    @staticmethod
    def change_password(user_id: int, new_password: str) -> None:
        pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        with DBContext() as (_, cursor):
            cursor.execute(
                "UPDATE users SET password_hash=%s WHERE user_id=%s",
                (pw_hash, user_id),
            )

    @staticmethod
    def delete_user(user_id: int) -> None:
        with DBContext() as (_, cursor):
            cursor.execute("DELETE FROM users WHERE user_id=%s", (user_id,))

    # ── 權限判斷 ───────────────────────────────────────────
    @staticmethod
    def can_manage_master(user: dict) -> bool:
        """基本檔設定（寫）：技術主任。"""
        return user["role"] >= 3

    @staticmethod
    def can_adjust_stock(user: dict) -> bool:
        """調整庫存：技術組長、技術主任。"""
        return user["role"] >= 2

    @staticmethod
    def can_manage_users(user: dict) -> bool:
        """使用者管理：技術主任。"""
        return user["role"] >= 3
