# core/setting_reader.py
import json
from pathlib import Path
setting_FILE = Path(__file__).parent.parent / "setting.json"

def load_setting(settingdir = setting_FILE):
    """
    載入設定檔 setting.json，並提供安全的預設值。
    """
    # 預設設定
    default_setting = {
          "menuitems": "TempBar",
          "log_modes": ["DEBUG", "INFO", "WARNING", "ERROR","CRITICAL"],
          "log_level": "DEBUG" ,
          "languages_modes":["zh_tw","en_us"],
          "language": "en_us"
        }

    try:
        
        if not setting_path.exists():
            logger.info("setting.json not found. Using default settings.")
            return default_setting

        with open(setting_path, 'r', encoding='utf-8') as f:
            user_setting = json.load(f)
            # 將使用者的設定覆蓋到預設設定上，這樣即使使用者只設定了一項，其他項也有預設值
            default_setting.update(user_setting)
            return default_setting

    except json.JSONDecodeError:
        print(f"ERROR: Failed to decode setting.json. File might be corrupted. Using default settings.")
        #logger.error("Failed to decode setting.json. File might be corrupted. Using default settings.")
        return default_setting
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading setting: {e}. Using default settings.")
        #logger.error(f"An unexpected error occurred while loading setting: {e}. Using default settings.")
        return default_setting
    
current_setting = load_setting()