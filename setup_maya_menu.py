"""
Menubuilder - Deployment Script

這是一個輕量級的部署腳本，用於在 Maya 啟動時自動生成菜單。

它的設計目的是讓沒有編輯需求的終端使用者（例如美術師）能夠輕鬆地
載入由TA或開發者配置好的菜單，而無需開啟 Menubuilder 的編輯器UI。
這個腳本通常透過 userSetup.py 來呼叫。
"""
import maya.cmds as cmds

def build_menus_on_startup():
    """
    一個獨立的啟動函式，用於在Maya啟動時自動生成菜單。
    這個函式不依賴任何UI，只在幕後執行。
    """
    # 為了讓使用者知道發生了什麼，在Script Editor中印出日誌
    print("--- [Menubuilder] Starting automatic menu generation on Maya startup ---")
    
    try:
        # 從 menubuilder 的核心模組中導入必要的元件
        # 使用相對導入路徑，確保它在作為 menubuilder 套件一部分時能正常工作
        from .core.setting_reader import current_setting
        from .core.data_handler import DataHandler
        from .core.menu_generator import MenuGenerator

        # 1. 讀取設定，找出預設要載入的菜單設定檔
        default_config = current_setting.get("menuitems")
        if not default_config:
            cmds.warning("[Menubuilder] No default menuitem specified in setting.json. Aborting menu generation.")
            return

        # 2. 實例化需要的類別
        data_handler = DataHandler()
        menu_generator = MenuGenerator()

        # 3. 載入菜單資料
        menu_data = data_handler.load_menu_config(default_config)

        if menu_data:
            # 4. 清除可能存在的舊菜單並生成新菜單
            menu_generator.clear_existing_menus()
            menu_generator.build_from_config(menu_data)
            print(f"--- [Menubuilder] Successfully built menus from '{default_config}.json' ---")
        else:
            cmds.warning(f"[Menubuilder] No data found in '{default_config}.json'. No menus were built.")

    except ImportError as ie:
        cmds.error(f"[Menubuilder] Failed to import modules. Please ensure the menubuilder project is in Maya's PYTHONPATH. Error: {ie}")
    except Exception as e:
        # 使用 cmds.error 可以在Maya中顯示更顯眼的紅色錯誤訊息
        cmds.error(f"[Menubuilder] An unexpected error occurred while building menus on startup. Error: {e}")