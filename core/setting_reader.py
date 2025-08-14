"""
Menubuilder - Settings Reader Module

這個模組專門負責讀取專案根目錄下的 `settings.json` 檔案。

它的核心功能是 `load_setting` 函式，該函式會安全地載入使用者設定，
並在檔案不存在或內容損毀時，提供一套穩健的預設值，確保工具
總能以一個可用的狀態啟動。
"""
import json
from pathlib import Path

setting_FILE = Path(__file__).parent.parent / "setting.json"

def save_setting(data_to_save):
    """將設定字典寫入到 setting.json 檔案中。"""
    try:
        with open(setting_FILE, 'w', encoding='utf-8') as f:
            # indent=4 讓JSON檔案格式化，更易讀
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"INFO: Settings successfully saved to {setting_FILE}")
        return True
    except Exception as e:
        print(f"ERROR: An error occurred while saving settings: {e}")
        return False

def load_setting(setting_path = setting_FILE):
    """
    載入設定檔 setting.json，並提供安全的預設值。
    """
    # 預設設定
    default_setting = {
          "menuitems": "TempBar",
          "log_modes": ["DEBUG", "INFO", "WARNING", "ERROR","CRITICAL"],
          "log_level": "ERROR" ,
          "languages_modes":["zh_tw","en_us","ja_jp"],
          "language": "en_us"
        }

    try:
        
        if not setting_path.exists():
            print(f"INFO: {setting_path} not found. Using default settings.")
            return default_setting

        with open(setting_path, 'r', encoding='utf-8') as f:
            user_setting = json.load(f)
            # 將使用者的設定覆蓋到預設設定上，這樣即使使用者只設定了一項，其他項也有預設值
            default_setting.update(user_setting)
            return default_setting

    except json.JSONDecodeError:
        print(f"ERROR: Failed to decode setting.json. File might be corrupted. Using default settings.")
        return default_setting
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading setting: {e}. Using default settings.")
        return default_setting
    
current_setting = load_setting()