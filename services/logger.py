# services/logger.py — 全域日誌管理服務

import os
import sys
import logging
from datetime import datetime


class MonthlyFolderDailyFileHandler(logging.Handler):
    """
    自訂日誌 Handler：
    1. 每日自動分檔，檔名格式如 error_YYYY-MM-DD.log
    2. 自動跨月分資料夾儲存，目錄格式如 logs/YYYY-MM/
    3. 自動保留 30 天歷史紀錄，逾期自動清理檔案與空資料夾
    """
    def __init__(self, log_dir):
        super().__init__()
        self.log_dir = log_dir
        self._handler = None
        self._current_day = None

    def _get_handler(self):
        now = datetime.now()
        day_str = now.strftime("%Y-%m-%d")
        month_str = now.strftime("%Y-%m")
        
        # 若當天日期沒變，直接使用現有的 FileHandler
        if self._current_day == day_str and self._handler:
            return self._handler
            
        # 建立年月資料夾 (logs/YYYY-MM/)
        month_dir = os.path.join(self.log_dir, month_str)
        if not os.path.exists(month_dir):
            try:
                os.makedirs(month_dir, exist_ok=True)
            except Exception as e:
                print(f"無法建立月分日誌目錄: {e}", file=sys.stderr)
            
        log_file = os.path.join(month_dir, f"error_{day_str}.log")
        
        # 關閉舊的 handler
        if self._handler:
            self._handler.close()
            
        self._handler = logging.FileHandler(log_file, encoding="utf-8")
        if self.formatter:
            self._handler.setFormatter(self.formatter)
            
        self._current_day = day_str
        
        # 每天切檔時順便進行 30 天舊日誌清理
        self._cleanup_old_logs()
        
        return self._handler

    def _cleanup_old_logs(self):
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=30)
            
            if not os.path.exists(self.log_dir):
                return
                
            for month_folder in os.listdir(self.log_dir):
                month_path = os.path.join(self.log_dir, month_folder)
                if not os.path.isdir(month_path):
                    continue
                    
                for log_file in os.listdir(month_path):
                    if not log_file.startswith("error_") or not log_file.endswith(".log"):
                        continue
                    # 檔名解析 (error_YYYY-MM-DD.log)
                    try:
                        date_part = log_file[6:16]
                        file_date = datetime.strptime(date_part, "%Y-%m-%d")
                        if file_date < cutoff_date:
                            os.remove(os.path.join(month_path, log_file))
                    except Exception:
                        pass
                
                # 若年月資料夾已無日誌，則刪除該空資料夾
                try:
                    if not os.listdir(month_path):
                        os.rmdir(month_path)
                except Exception:
                    pass
        except Exception:
            pass

    def emit(self, record):
        try:
            handler = self._get_handler()
            handler.emit(record)
        except Exception:
            self.handleError(record)

    def close(self):
        if self._handler:
            self._handler.close()
        super().close()


def setup_global_logger():
    """配置全域日誌系統，攔截未處理的異常並記錄至日誌檔案。"""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            print(f"無法建立日誌目錄: {e}", file=sys.stderr)
            return logging.getLogger()

    logger = logging.getLogger("ReagentStorage")
    logger.setLevel(logging.INFO)

    # 使用我們自訂的跨月跨日分流日誌 Handler
    handler = MonthlyFolderDailyFileHandler(log_dir)
    
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # 同時將錯誤輸出至終端機 stdout 方便本地除錯
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 捕捉未被 try-except 攔截的全域例外
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # 讓 Ctrl+C 正常終止程式
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # 記錄完整的 Traceback 堆疊資訊
        logger.critical(
            "未攔截的全域例外異常 (Uncaught Exception):",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception

    # 攔截 unraisable 執行緒或背景異常（Python 3.8+ 支援）
    if hasattr(sys, "unraisablehook"):
        def handle_unraisable(unraisable):
            logger.critical(
                f"背景/執行緒未處理異常 (Unraisable Exception): {unraisable.err_msg or ''}",
                exc_info=(unraisable.exc_type, unraisable.exc_value, unraisable.exc_traceback)
            )
        sys.unraisablehook = handle_unraisable

    return logger
