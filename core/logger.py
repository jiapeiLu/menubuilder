# core/logger.py
import logging
import os
from .setting_reader import current_setting # 載入setting
from maya import cmds

# 定義日誌的格式
LOG_FORMAT = '%(asctime)s - %(name)s - [%(levelname)s] - %(message)s'

# 定義日誌Framework名稱
LOG_FRAMEWORK = 'menubuilder'

# 定義日誌檔案的路徑，通常放在Maya的使用者設定資料夾中
LOG_FILE_PATH = os.path.join(cmds.internalVar(userPrefDir=True), f'{LOG_FRAMEWORK}.log')

def setup_logger(setting):
    """設定並返回一個配置好的logger實例"""
    
    # 獲取一個名為 'menubuilder' 的 logger
    # 使用特定名稱可以避免與Maya或其他工具的logger衝突
    logger = logging.getLogger(LOG_FRAMEWORK)
    

    # 從設定檔取得日誌等級，預設為 'INFO'
    log_level_str = setting.get("log_level", "INFO").upper()
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    # 設定等級
    level = level_map.get(log_level_str, logging.INFO)
    logger.setLevel(level)

    # [修正] 停止將訊息傳播到根 logger，避免重複輸出
    logger.propagate = False

    # 防止因重覆執行腳本而添加多個handler，導致日誌重覆輸出
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- 1. 建立輸出到Maya Script Editor的Handler ---
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(stream_handler)

    # --- 2. 建立輸出到檔案的Handler ---
    # 'a' 表示 append，日誌會不斷附加到檔案末尾
    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
    
    return logger



# 創建一個全域的logger實例，讓其他模組導入
log = setup_logger(current_setting)