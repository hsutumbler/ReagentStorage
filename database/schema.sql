-- ============================================================
-- 試劑庫存管理系統 — 資料庫建立腳本
-- 符合 ISO 15189 規範
-- ============================================================

CREATE DATABASE IF NOT EXISTS reagent_storage
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE reagent_storage;

-- ------------------------------------------------------------
-- 使用者資料表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    employee_id   VARCHAR(20)  NOT NULL UNIQUE COMMENT '工號（帳號）',
    name          VARCHAR(50)  NOT NULL COMMENT '姓名',
    password_hash VARCHAR(255) NOT NULL COMMENT 'bcrypt 雜湊密碼',
    role          TINYINT      NOT NULL DEFAULT 1
                  COMMENT '1=一般使用者, 2=試劑負責人, 3=組長/技術主任',
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                  ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_employee_id (employee_id)
) COMMENT='使用者';

-- ------------------------------------------------------------
-- 組別資料表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    dept_id   INT AUTO_INCREMENT PRIMARY KEY,
    dept_name VARCHAR(50) NOT NULL UNIQUE COMMENT '組別名稱',
    is_active BOOLEAN     NOT NULL DEFAULT TRUE
) COMMENT='組別';

-- ------------------------------------------------------------
-- 廠商資料表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vendors (
    vendor_id     INT AUTO_INCREMENT PRIMARY KEY,
    vendor_name   VARCHAR(100) NOT NULL COMMENT '廠商名稱',
    sales_rep     VARCHAR(50)  COMMENT '業務',
    order_contact VARCHAR(50)  COMMENT '訂藥窗口',
    phone         VARCHAR(30)  COMMENT '電話',
    email         VARCHAR(100) COMMENT 'Email',
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                  ON UPDATE CURRENT_TIMESTAMP
) COMMENT='廠商';

-- ------------------------------------------------------------
-- 單位換算資料表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS unit_conversions (
    unit_id         INT AUTO_INCREMENT PRIMARY KEY,
    unit_name       VARCHAR(50)    NOT NULL UNIQUE COMMENT '換算組合名稱',
    stock_unit      VARCHAR(20)    NOT NULL COMMENT '入庫單位',
    count_unit      VARCHAR(20)    NOT NULL COMMENT '盤點單位',
    issue_unit      VARCHAR(20)    NOT NULL COMMENT '出庫單位',
    stock_to_count  DECIMAL(10,4)  NOT NULL DEFAULT 1 COMMENT '入庫→盤點換算比',
    count_to_issue  DECIMAL(10,4)  NOT NULL DEFAULT 1 COMMENT '盤點→出庫換算比'
) COMMENT='單位換算';

-- ------------------------------------------------------------
-- 試劑主檔
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reagents (
    reagent_id    INT AUTO_INCREMENT PRIMARY KEY,
    reagent_name  VARCHAR(100)  NOT NULL COMMENT '試劑名稱',
    item_number   VARCHAR(50)   COMMENT '料號',
    dept_id       INT           NOT NULL,
    storage_temp  VARCHAR(20)   COMMENT '保存溫度（如 2-8°C）',
    open_days     INT           COMMENT '開封後有效天數',
    safety_stock  DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '安全庫存量',
    vendor_id     INT           NOT NULL,
    brand         VARCHAR(50)   COMMENT '廠牌',
    unit_id       INT           COMMENT '單位換算',
    default_label_type INT      NOT NULL DEFAULT 0 COMMENT '預設標籤類型：0=系統預設, 1=一般標籤, 2=QR Code標籤',
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                  ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (dept_id)   REFERENCES departments(dept_id),
    FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id),
    FOREIGN KEY (unit_id)   REFERENCES unit_conversions(unit_id),
    INDEX idx_vendor (vendor_id),
    INDEX idx_dept   (dept_id)
) COMMENT='試劑主檔';

-- ------------------------------------------------------------
-- 訂購單
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id        INT AUTO_INCREMENT PRIMARY KEY,
    po_code      VARCHAR(20)  NOT NULL UNIQUE COMMENT '訂購單條碼 PO+yyyyMMDD+XX',
    vendor_id    INT          NOT NULL,
    dept_id      INT          NOT NULL,
    created_by   INT          NOT NULL COMMENT '建立人員 user_id',
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status       TINYINT      NOT NULL DEFAULT 0
                 COMMENT '0=草稿, 1=已送出, 2=已入庫',
    FOREIGN KEY (vendor_id)  REFERENCES vendors(vendor_id),
    FOREIGN KEY (dept_id)    REFERENCES departments(dept_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id),
    INDEX idx_po_code (po_code),
    INDEX idx_vendor  (vendor_id)
) COMMENT='訂購單';

-- ------------------------------------------------------------
-- 訂購單明細
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS purchase_order_items (
    po_item_id   INT AUTO_INCREMENT PRIMARY KEY,
    po_id        INT           NOT NULL,
    reagent_id   INT           NOT NULL,
    ordered_qty  DECIMAL(10,2) NOT NULL COMMENT '訂購數量',
    received_qty DECIMAL(10,2) NOT NULL DEFAULT 0 COMMENT '實際入庫數量',
    FOREIGN KEY (po_id)      REFERENCES purchase_orders(po_id),
    FOREIGN KEY (reagent_id) REFERENCES reagents(reagent_id),
    INDEX idx_po (po_id)
) COMMENT='訂購單明細';

-- ------------------------------------------------------------
-- 庫存（每瓶一筆）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id       INT AUTO_INCREMENT PRIMARY KEY,
    rid                VARCHAR(20)  NOT NULL UNIQUE COMMENT '試劑條碼 R+yyMMDD+NNN',
    reagent_id         INT          NOT NULL,
    lot_number         VARCHAR(50)  NOT NULL COMMENT '批號',
    expiry_date        DATE         NOT NULL COMMENT '穩定效期',
    received_date      DATE         NOT NULL COMMENT '入庫日期',
    received_by        INT          NOT NULL COMMENT '入庫人員',
    receive_mode       TINYINT      NOT NULL DEFAULT 1
                       COMMENT '1=一般入庫, 2=廠商還貨, 3=體系轉入',
    po_id              INT          COMMENT '關聯訂購單（整批入庫時填入）',
    status             TINYINT      NOT NULL DEFAULT 0
                       COMMENT '0=在庫, 1=已出庫, 2=已調整刪除',
    issued_at          DATETIME     COMMENT '出庫時間',
    issued_by          INT          COMMENT '出庫人員',
    issue_mode         TINYINT      COMMENT '1=一般出庫, 2=廠商借貨, 3=體系轉出',
    open_expiry_date   DATE         COMMENT '開封效期（出庫日期+開封天數）',
    printed_expiry_date DATE        COMMENT '標籤列印效期（穩定與開封取較早者）',
    created_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reagent_id)  REFERENCES reagents(reagent_id),
    FOREIGN KEY (received_by) REFERENCES users(user_id),
    FOREIGN KEY (po_id)       REFERENCES purchase_orders(po_id),
    INDEX idx_rid        (rid),
    INDEX idx_reagent    (reagent_id),
    INDEX idx_status     (status),
    INDEX idx_lot        (lot_number),
    INDEX idx_expiry     (expiry_date)
) COMMENT='庫存（每瓶一筆）';

-- ------------------------------------------------------------
-- 庫存調整記錄（稽核軌跡）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stock_adjustments (
    adj_id         INT AUTO_INCREMENT PRIMARY KEY,
    inventory_id   INT          NOT NULL COMMENT '被調整的 inventory_id',
    rid            VARCHAR(20)  NOT NULL COMMENT 'RID 快照',
    reagent_name   VARCHAR(100) NOT NULL COMMENT '試劑名稱快照',
    lot_number     VARCHAR(50)  NOT NULL COMMENT '批號快照',
    expiry_date    DATE         NOT NULL COMMENT '穩定效期快照',
    received_date  DATE         NOT NULL COMMENT '入庫日期快照',
    adjusted_by    INT          NOT NULL COMMENT '調整人員',
    adjusted_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason         VARCHAR(255) COMMENT '調整原因',
    FOREIGN KEY (adjusted_by) REFERENCES users(user_id),
    INDEX idx_adj_rid (rid)
) COMMENT='庫存調整稽核記錄';

-- ------------------------------------------------------------
-- 不合格試劑記錄
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nonconforming_reagents (
    nc_id        INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id    INT          NOT NULL,
    reagent_id   INT          NOT NULL,
    lot_number   VARCHAR(50)  NOT NULL COMMENT '批號',
    expiry_date  DATE         COMMENT '穩定效期',
    nc_reason    TEXT         NOT NULL COMMENT '不合格原因',
    recorded_by  INT          NOT NULL COMMENT '紀錄人員',
    recorded_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id)   REFERENCES vendors(vendor_id),
    FOREIGN KEY (reagent_id)  REFERENCES reagents(reagent_id),
    FOREIGN KEY (recorded_by) REFERENCES users(user_id),
    INDEX idx_nc_vendor  (vendor_id),
    INDEX idx_nc_reagent (reagent_id)
) COMMENT='不合格試劑記錄';

-- ------------------------------------------------------------
-- RID 流水號追蹤（確保多用戶端不重複）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rid_sequence (
    seq_date    DATE    NOT NULL PRIMARY KEY COMMENT '日期',
    last_seq    INT     NOT NULL DEFAULT 0   COMMENT '當日最後流水號'
) COMMENT='RID 流水號（每日重置）';

-- ------------------------------------------------------------
-- PO 流水號追蹤
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS po_sequence (
    seq_date    DATE    NOT NULL PRIMARY KEY COMMENT '日期',
    last_seq    INT     NOT NULL DEFAULT 0   COMMENT '當日最後流水號'
) COMMENT='PO 訂購單流水號（每日重置）';

-- ------------------------------------------------------------
-- 預設資料：初始管理員帳號
-- 預設帳號：admin，密碼：Admin1234（請第一次登入後立即修改）
-- bcrypt hash of 'Admin1234'
-- ------------------------------------------------------------
INSERT IGNORE INTO users (employee_id, name, password_hash, role)
VALUES (
    'admin',
    '系統管理員',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGwmGhvQLHx3hIBJIL7m8VCKJvK',
    3
);
