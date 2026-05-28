# ui/main_window.py — 主視窗（現代側邊導航）

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QSpacerItem, QSizePolicy, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QCursor
from config import APP_NAME, DEFAULT_FONT
from services.auth_service import AuthService

from ui.dashboard                import DashboardPage
from ui.master.user_management    import UserManagementPage
from ui.master.vendor_management  import VendorManagementPage
from ui.master.reagent_management import ReagentManagementPage
from ui.master.unit_management    import UnitManagementPage
from ui.receiving.manual_receive  import ManualReceivePage
from ui.receiving.batch_receive   import BatchReceivePage
from ui.issuing.issue_dialog      import IssuePage
from ui.order.purchase_order      import PurchaseOrderPage
from ui.adjustment.stock_adjustment import StockAdjustmentPage
from ui.nonconforming.nc_reagent  import NonConformingPage
from ui.query.traceability        import TraceabilityPage
from ui.query.stock_count         import StockCountPage
from ui.query.adjustment_log      import AdjustmentLogPage
from ui.query.order_query         import OrderQueryPage
from ui.query.nc_query            import NcQueryPage


# ── 導航結構（含圖示） ─────────────────────────────────────
NAV_GROUPS = [
    {
        "group": "_dashboard",  # 特殊群組，不顯示群組標籤
        "items": [
            {"icon": "🏠", "label": "儀表板", "key": "dashboard", "role_min": 1},
        ],
    },
    {
        "group": "庫存作業",
        "items": [
            {"icon": "📥", "label": "手工入庫",  "key": "receive_manual", "role_min": 1},
            {"icon": "📦", "label": "整批入庫",  "key": "receive_batch",  "role_min": 1},
            {"icon": "📤", "label": "出庫",      "key": "issue",          "role_min": 1},
        ],
    },
    {
        "group": "訂單管理",
        "items": [
            {"icon": "🛒", "label": "試劑訂單",    "key": "po",         "role_min": 1},
            {"icon": "✏️", "label": "調整庫存",    "key": "adjustment", "role_min": 2},
            {"icon": "⚠️", "label": "不合格試劑記錄",  "key": "nc",         "role_min": 1},
        ],
    },
    {
        "group": "資料查詢",
        "items": [
            {"icon": "🔍", "label": "庫存追溯",   "key": "q_trace", "role_min": 1},
            {"icon": "📊", "label": "庫存盤點",   "key": "q_stock", "role_min": 1},
            {"icon": "📋", "label": "調整庫存查詢",   "key": "q_adj",   "role_min": 1},
            {"icon": "📄", "label": "試劑訂單查詢", "key": "q_order", "role_min": 1},
            {"icon": "🚫", "label": "不合格試劑查詢", "key": "q_nc",    "role_min": 1},
        ],
    },
    {
        "group": "基本設定",
        "items": [
            {"icon": "👤", "label": "使用者管理", "key": "users",    "role_min": 3},
            {"icon": "🏢", "label": "廠商管理",   "key": "vendors",  "role_min": 3},
            {"icon": "🧬", "label": "試劑管理",   "key": "reagents", "role_min": 3},
            {"icon": "⚖️", "label": "單位換算",   "key": "units",    "role_min": 3},
        ],
    },
]


class MainWindow(QMainWindow):
    _active_windows = []

    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1280, 800)
        self._page_map: dict[str, QWidget] = {}
        self._nav_btns: dict[str, QPushButton] = {}
        self._current_key: str = ""
        self._build_ui()
        self._apply_global_style()
        self._navigate_first()

    # ── 主佈局 ─────────────────────────────────────────────
    def _build_ui(self):
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root = QHBoxLayout(root_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        # 右側：頁面堆疊
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_area")
        self._register_pages()
        root.addWidget(self.stack, 1)

    # ── 側邊欄 ─────────────────────────────────────────────
    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo 區
        layout.addWidget(self._build_logo())

        # 使用者資訊
        layout.addWidget(self._build_user_info())

        # 分隔線
        layout.addWidget(self._make_divider())

        # 導航清單
        nav_wrap = QWidget()
        nav_wrap.setObjectName("nav_wrap")
        nav_layout = QVBoxLayout(nav_wrap)
        nav_layout.setContentsMargins(12, 12, 12, 12)
        nav_layout.setSpacing(0)

        for group in NAV_GROUPS:
            visible_items = [i for i in group["items"] if i["role_min"] <= self.user["role"]]
            if not visible_items:
                continue

            # 儀表板群組不顯示群組標籤
            if not group["group"].startswith("_"):
                grp_lbl = QLabel(group["group"].upper())
                grp_lbl.setObjectName("nav_group_label")
                nav_layout.addWidget(grp_lbl)

            for item in visible_items:
                btn = QPushButton(f"  {item['icon']}  {item['label']}")
                btn.setObjectName("nav_btn")
                btn.setProperty("nav_key", item["key"])
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(40)
                btn.setCheckable(True)
                btn.clicked.connect(lambda _, k=item["key"]: self._navigate(k))
                self._nav_btns[item["key"]] = btn
                nav_layout.addWidget(btn)

            nav_layout.addSpacing(8)

        nav_layout.addStretch()
        layout.addWidget(nav_wrap, 1)

        # 底部登出
        layout.addWidget(self._make_divider())
        layout.addWidget(self._build_logout_btn())

        return sidebar

    def _build_logo(self) -> QWidget:
        w = QWidget()
        w.setObjectName("logo_bar")
        w.setFixedHeight(68)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(20, 0, 20, 0)

        icon = QLabel("🧪")
        icon.setObjectName("sidebar_logo_icon")
        name = QLabel("試劑庫存系統")
        name.setObjectName("sidebar_logo_text")

        layout.addWidget(icon)
        layout.addSpacing(8)
        layout.addWidget(name)
        layout.addStretch()
        return w

    def _build_user_info(self) -> QWidget:
        w = QWidget()
        w.setObjectName("user_info_bar")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # 頭像圓圈
        avatar = QLabel(self.user["name"][0])
        avatar.setObjectName("user_avatar")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right = QVBoxLayout()
        right.setSpacing(2)
        name_lbl = QLabel(self.user["name"])
        name_lbl.setObjectName("user_name_label")
        role_lbl = QLabel(self.user["role_label"])
        role_lbl.setObjectName("user_role_label")
        right.addWidget(name_lbl)
        right.addWidget(role_lbl)

        layout.addWidget(avatar)
        layout.addLayout(right)
        layout.addStretch()
        return w

    def _build_logout_btn(self) -> QPushButton:
        btn = QPushButton("  ⎋   登出")
        btn.setObjectName("logout_btn")
        btn.setFixedHeight(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._logout)
        return btn

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("sidebar_divider")
        line.setFixedHeight(1)
        return line

    # ── 頁面注冊 ───────────────────────────────────────────
    def _register_pages(self):
        page_classes = {
            "dashboard":      DashboardPage,
            "users":          UserManagementPage,
            "vendors":        VendorManagementPage,
            "reagents":       ReagentManagementPage,
            "units":          UnitManagementPage,
            "receive_manual": ManualReceivePage,
            "receive_batch":  BatchReceivePage,
            "issue":          IssuePage,
            "po":             PurchaseOrderPage,
            "adjustment":     StockAdjustmentPage,
            "nc":             NonConformingPage,
            "q_trace":        TraceabilityPage,
            "q_stock":        StockCountPage,
            "q_adj":          AdjustmentLogPage,
            "q_order":        OrderQueryPage,
            "q_nc":           NcQueryPage,
        }
        for key, cls in page_classes.items():
            try:
                page = cls(self.user)
            except TypeError:
                page = cls()
            self._page_map[key] = page
            self.stack.addWidget(page)

    # ── 導航 ───────────────────────────────────────────────
    def _navigate(self, key: str):
        if key not in self._page_map:
            return
        self._current_key = key
        page = self._page_map[key]
        self.stack.setCurrentWidget(page)
        for k, btn in self._nav_btns.items():
            btn.setChecked(k == key)
            
        # 如果頁面有定義顯示時的動作 (例如自動聚焦)，則執行
        if hasattr(page, "on_page_show"):
            page.on_page_show()

    def _navigate_first(self):
        """根據角色設定登入後的初始頁面。"""
        # 一般使用者 (role=1) 直接進「出庫」
        if self.user.get("role") == 1:
            self._navigate("issue")
        else:
            # 組長、主任、管理員進「儀表板」
            self._navigate("dashboard")

    # ── 登出 ───────────────────────────────────────────────
    def _logout(self):
        reply = QMessageBox.question(
            self, "確認登出", f"確定要登出嗎？\n目前使用者：{self.user['name']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from ui.login_window import LoginWindow
            # 建立新的登入視窗，不指定 parent 避免因主視窗關閉而被關閉
            login_win = LoginWindow()
            
            def on_relogin(user: dict):
                new_win = MainWindow(user)
                new_win.show()
                MainWindow._active_windows.append(new_win)
                if login_win in MainWindow._active_windows:
                    MainWindow._active_windows.remove(login_win)
                    
            login_win.login_success.connect(on_relogin)
            login_win.show()
            
            # 將登入視窗加入強引用列表中，避免被垃圾回收
            MainWindow._active_windows.append(login_win)
            
            # 從強引用列表中移除目前要關閉的視窗
            if self in MainWindow._active_windows:
                MainWindow._active_windows.remove(self)
                
            from PyQt6.QtWidgets import QApplication
            QApplication.setQuitOnLastWindowClosed(False)
            self.close()
            QApplication.setQuitOnLastWindowClosed(True)

    # ── 全域樣式 ───────────────────────────────────────────
    def _apply_global_style(self):
        self.setStyleSheet("""
            /* ── 全域字型 ── */
            * {
                font-family: {DEFAULT_FONT};
            }

            QMainWindow, #content_area {
                background: #FDFBF7;
            }

            /* ── 側邊欄 ── */
            #sidebar {
                background: #F1F4F9;
                border-right: 1px solid #DEE2E6;
            }

            #logo_bar {
                background: #EBF0F6;
            }
            #sidebar_logo_icon {
                font-size: 20px;
            }
            #sidebar_logo_text {
                color: #2D3436;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            #user_info_bar {
                background: #F1F4F9;
            }
            #user_avatar {
                background: #0066CC;
                color: #FFFFFF;
                border-radius: 18px;
                font-size: 14px;
                font-weight: 700;
            }
            #user_name_label {
                color: #2D3436;
                font-size: 13px;
                font-weight: 600;
            }
            #user_role_label {
                color: #636E72;
                font-size: 11px;
            }

            #sidebar_divider {
                background: #DEE2E6;
                border: none;
            }

            /* ── 導航 ── */
            #nav_wrap {
                background: #F1F4F9;
            }
            #nav_group_label {
                color: #B2BEC3;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 12px 4px 6px 4px;
            }
            #nav_btn {
                background: transparent;
                color: #636E72;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding: 0 10px;
                font-size: 13px;
                font-weight: 500;
            }
            #nav_btn:hover {
                background: #E2E8F0;
                color: #2D3436;
            }
            #nav_btn:checked {
                background: #E6F0FF;
                color: #0066CC;
                font-weight: 600;
            }

            /* ── 登出按鈕 ── */
            #logout_btn {
                background: transparent;
                color: #636E72;
                border: none;
                text-align: left;
                padding: 0 20px;
                font-size: 13px;
            }
            #logout_btn:hover {
                background: #FFF5F5;
                color: #DC3545;
            }
        """)
