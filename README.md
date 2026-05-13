# 醫院檢驗科試劑庫存管理系統

符合 ISO 15189 規範的試劑庫存管理系統，使用 Python + PyQt6 + MySQL。

## 系統需求

- Python 3.11+
- MySQL 8.0+
- Zebra 印表機（支援 ZPL）
- HID 條碼掃描器

## 安裝與設定

### 1. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 2. 設定資料庫

1. 在 MySQL 伺服器上建立資料庫與資料表：

```bash
mysql -u root -p < database/schema.sql
```

2. 建立 MySQL 使用者（範例）：

```sql
CREATE USER 'reagent_user'@'%' IDENTIFIED BY 'reagent_pass';
GRANT ALL PRIVILEGES ON reagent_storage.* TO 'reagent_user'@'%';
FLUSH PRIVILEGES;
```

### 3. 修改連線設定

編輯 `config.py`，設定 MySQL 伺服器 IP、帳號、密碼：

```python
DB_CONFIG = {
    "host": "192.168.1.xxx",   # MySQL 伺服器 IP
    "user": "reagent_user",
    "password": "your_password",
    ...
}
```

### 4. 設定 Zebra 印表機

在 `config.py` 中設定印表機名稱：

```python
ZEBRA_PRINTER_NAME = "Zebra ZD421"   # Windows 印表機名稱
```

### 5. 啟動程式

```bash
python main.py
```

## 預設帳號

| 工號 | 密碼 | 角色 |
|------|------|------|
| admin | Admin1234 | 組長/技術主任 |

**請第一次登入後立即修改密碼！**

## 功能模組

| 模組 | 說明 |
|------|------|
| 使用者管理 | 帳號、角色管理 |
| 廠商管理 | 廠商基本資料 |
| 試劑管理 | 試劑主檔、組別設定 |
| 單位換算 | 入庫/盤點/出庫單位換算 |
| 手工入庫 | 逐筆入庫、批號警示、ZPL 標籤列印 |
| 整批入庫 | 掃描訂購單條碼批次入庫 |
| 出庫 | FEFO 提醒、效期比對、出庫標籤列印 |
| 試劑訂單 | 建立訂購單、列印訂購條碼 |
| 調整庫存 | 庫存刪除（含稽核記錄） |
| 不合格試劑 | ISO 15189 不合格品記錄 |
| 庫存追溯 | 出入庫歷程查詢 |
| 庫存盤點 | 以盤點單位顯示庫存 |
| 調整記錄 | 庫存修改稽核查詢 |
| 訂購單查詢 | 歷史訂購單查詢 |
| 不合格查詢 | 不合格記錄查詢 |

## 識別碼規則

- **RID**：`R` + `yyMMDD` + `NNN`（每日流水號從 001 重置）
- **訂購單**：`PO` + `yyyyMMDD` + `XX`（每日流水號從 01 重置）

## 標籤規格（Zebra @ 203dpi）

| 類型 | 尺寸 | 用途 |
|------|------|------|
| 一般入庫標籤 | 5cm × 3.5cm | Code128 + 試劑資訊 |
| QR Code 入庫 | 2cm × 2cm | QR Code + 試劑名稱 |
| 一般出庫標籤 | 5cm × 3.5cm | 出庫資訊 |
| QR Code 出庫 | 2cm × 2cm | 含「出」字識別 |

## 目錄結構

```
ReagentStorage/
├── main.py              # 程式進入點
├── config.py            # 連線與列印設定
├── requirements.txt
├── database/
│   ├── schema.sql       # 資料庫建立腳本
│   ├── connection.py    # 連線池
│   └── models/          # 資料存取層
├── services/            # 業務邏輯
│   ├── auth_service.py
│   ├── rid_generator.py
│   └── label_printer.py
└── ui/                  # PyQt6 介面
    ├── login_window.py
    ├── main_window.py
    ├── base_page.py
    ├── master/
    ├── receiving/
    ├── issuing/
    ├── order/
    ├── adjustment/
    ├── nonconforming/
    └── query/
```
