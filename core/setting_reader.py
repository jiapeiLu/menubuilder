"""
Menubuilder - Settings Reader Module

這個模組專門負責讀取專案根目錄下的 `settings.json` 檔案。

它的核心功能是 `load_setting` 函式，該函式會安全地載入使用者設定，
並在檔案不存在或內容損毀時，提供一套穩健的預設值，確保工具
總能以一個可用的狀態啟動。
"""
import json
from pathlib import Path
from PySide2 import QtCore

setting_FILE = Path(__file__).parent.parent / "setting.json"

class SettingsManager:
    """
    [重構版] 一個單例的設定管理器。
    負責讀取、寫入 setting.json，並在記憶體中維護一份唯一的設定資料。
    所有模組都應透過這個管理器來存取設定，以避免資料快照問題。
    """
    def __init__(self):
        self.current_setting = self._load_setting()

    def _get_default_settings(self):
        """返回一份預設設定，確保每次都拿到新的字典物件。"""
        return {
            "menuitems": "TempBar",
            "log_modes": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "log_level": "ERROR",
            "languages_modes": ["zh_tw", "en_us", "ja_jp"],
            "language": "en_us"
        }

    def _load_setting(self, setting_path=setting_FILE):
        """載入設定檔 setting.json，並提供安全的預設值。"""
        default_settings = self._get_default_settings()
        try:
            if not setting_path.exists():
                print(f"INFO: {setting_path} not found. Using default settings.")
                return default_settings

            with open(setting_path, 'r', encoding='utf-8') as f:
                user_setting = json.load(f)
                default_settings.update(user_setting)
                return default_settings
        except json.JSONDecodeError:
            print(f"ERROR: Failed to decode setting.json. Using default settings.")
            return self._get_default_settings()
        except Exception as e:
            print(f"ERROR: Error loading settings: {e}. Using default settings.")
            return self._get_default_settings()

    def save_setting(self):
        """將記憶體中的 current_setting 字典寫入到 setting.json 檔案中。"""
        try:
            with open(setting_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.current_setting, f, ensure_ascii=False, indent=4)
            print(f"INFO: Settings successfully saved to {setting_FILE}")
            return True
        except Exception as e:
            print(f"ERROR: An error occurred while saving settings: {e}")
            return False

    def reload(self):
        """[核心] 提供一個外部接口，用於從硬碟強制重新載入設定。"""
        print(f"INFO: Reloading settings from disk...")
        self.current_setting = self._load_setting()

def get_settings_manager_instance():
    """
    穩健的單例工廠函式，確保 SettingsManager 的實例在 Maya Session 中唯一。
    """
    app = QtCore.QCoreApplication.instance()
    if not hasattr(app, '_menubuilder_settings_manager_instance'):
        instance = SettingsManager()
        setattr(app, '_menubuilder_settings_manager_instance', instance)
    return getattr(app, '_menubuilder_settings_manager_instance')

# 建立一個全域的、唯一的設定管理器實例的引用
settings_manager = get_settings_manager_instance()