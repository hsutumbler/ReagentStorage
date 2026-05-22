# config.py — 資料庫連線設定
# 請依實際環境修改以下設定

DB_CONFIG = {
    "host": "127.0.0.1",      # MySQL 伺服器 IP
    "port": 3306,
    "user": "reagent_user",
    "password": "reagent_pass",
    "database": "reagent_storage",
    "charset": "utf8mb4",
    "connection_timeout": 10,
}

# 連線池設定
POOL_CONFIG = {
    "pool_name": "reagent_pool",
    "pool_size": 5,
    "pool_reset_session": True,
}

# 應用程式設定
APP_NAME = "試劑庫存管理系統"
APP_VERSION = "1.0.0"

# 跨平台字型偵測
import platform
IS_MAC = platform.system() == "Darwin"
# Mac 優先使用蘋方，Windows 優先使用微軟正黑體
DEFAULT_FONT = "PingFang TC" if IS_MAC else "Microsoft JhengHei"

# ──────────────────────────────────────────────────────────
# Zebra 印表機設定
# ──────────────────────────────────────────────────────────
#
# 支援型號與常見 DPI：
#   GX420t → 203 dpi（此型號固定，請填 203）
#   ZT410  → 依購買版本：203 dpi 或 300 dpi
#   ZD421  → 依購買版本：203 dpi 或 300 dpi
#
# 如何確認 DPI：於印表機上列印設定頁（Configuration Label），
# 查看 "Print Resolution" 欄位。
# ──────────────────────────────────────────────────────────

# 印表機名稱
# Windows: 填入「裝置和印表機」中顯示的名稱，例如 "ZDesigner GX420t"
# macOS  : 填入 CUPS 中的印表機名稱，例如 "Zebra_ZT410"
# 留空   : 使用系統預設印表機
ZEBRA_PRINTER_NAME = "Zebra_Technologies_ZTC_ZD421_203dpi_ZPL"

# 印表機 DPI（請依實際型號與購買規格填入 203 或 300）
ZEBRA_DPI = 203


def cm_to_dots(cm: float) -> int:
    """
    將公分換算為 Zebra dots。
    公式：dots = cm / 2.54 * DPI
    例：5 cm @ 203 dpi = 399 dots ≈ 400
        5 cm @ 300 dpi = 591 dots ≈ 591
    """
    return round(cm / 2.54 * ZEBRA_DPI)


# ──────────────────────────────────────────────────────────
# 標籤實體尺寸（公分）— 請勿修改，除非標籤紙規格不同
# ──────────────────────────────────────────────────────────
LABEL_LARGE_W_CM = 5.0    # 一般標籤：寬
LABEL_LARGE_H_CM = 3.5    # 一般標籤：高

LABEL_SMALL_W_CM = 5.0    # QR Code 標籤：寬 (同步為 5.0 以支援並排排版)
LABEL_SMALL_H_CM = 3.5    # QR Code 標籤：高 (同步為 3.5)

LABEL_QR_BODY_CM = 1.6    # QR Code 本身邊長
