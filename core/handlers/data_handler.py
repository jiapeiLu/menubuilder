#menubuilder/core/handlers/data_handler.py
"""
Menubuilder - Data Handler Module (Model)

這個模組是 MVC 架構中的「模型(Model)」層的一部分。

它的核心職責是處理所有與菜單設定檔 (`menuitems/*.json`) 相關的
檔案 I/O 操作。這包括從 .json 檔案中讀取資料並將其轉換為
`MenuItemData` 物件列表，以及將 `MenuItemData` 物件列表寫回
.json 檔案中。
"""
import json
from pathlib import Path
from typing import List
import os
from ..dto import MenuItemData
from ..logger import log

class DataHandler:
    """
    負責讀取和寫入菜單設定檔，是MVC架構中模型(Model)的檔案I/O部分。
    
    這個類別封裝了所有與 `menuitems/*.json` 檔案互動的邏輯。它將
    JSON的字典格式與程式內部的 `MenuItemData` 物件格式進行互相轉換。
    """
    
    # 動態獲取 menuitems 資料夾的路徑
    MENUITEMS_DIR = Path(__file__).parent.parent.parent / "menuitems"

    def __init__(self):
        """
        初始化 DataHandler，動態決定菜單設定檔的路徑。
        """
        # 1. 嘗試從環境變數讀取路徑
        env_path = os.environ.get('MENUBUILDER_CONFIG_PATH')

        if env_path and os.path.exists(env_path):
            self.MENUITEMS_DIR = Path(env_path)
            log.info(f"使用環境變數指定的路徑: {self.MENUITEMS_DIR}")
        else:
            # 2. 如果環境變數不存在，則使用預設的相對路徑
            self.MENUITEMS_DIR = Path(__file__).parent.parent.parent / "menuitems"
            log.info(f"使用工具預設路徑: {self.MENUITEMS_DIR}")

    def load_menu_config(self, config_name: str) -> List[MenuItemData]:
        """
        從 menuitems 資料夾載入指定的設定檔，並將其內容轉換為 MenuItemData 物件列表。

        Args:
            config_name (str): 菜單設定檔的名稱，不包含 .json 副檔名。
                               例如: "personal_menubar"。

        Returns:
            List[MenuItemData]: 一個包含所有已載入菜單項資料的列表。
                                如果檔案不存在或解析失敗，則返回一個空列表。
        """
        config_path = self.MENUITEMS_DIR / f"{config_name}.json"
        
        if not config_path.exists():
            log.error(f"設定檔不存在: {config_path}")
            return []

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # 將從JSON讀取的字典列表，轉換為MenuItemData物件列表
            menu_items = [MenuItemData.from_dict(item) for item in json_data]
            log.info(f"成功從 {config_path} 載入 {len(menu_items)} 個菜單項。")
            return menu_items
            
        except json.JSONDecodeError:
            log.error(f"解碼JSON時發生錯誤: {config_path}，檔案可能已損毀。", exc_info=True)
            return []
        except Exception as e:
            log.error(f"載入設定檔時發生未知錯誤: {e}", exc_info=True)
            return []

    def save_menu_config(self, config_name: str, data: List[MenuItemData]):
        """
        將 MenuItemData 物件列表轉換為 JSON 格式，並寫入到指定的設定檔中。

        Args:
            config_name (str): 要儲存的菜單設定檔的名稱，不包含 .json 副檔名。
            data (List[MenuItemData]): 包含了當前所有菜單項資料的物件列表。
        """
        config_path = self.MENUITEMS_DIR / f"{config_name}.json"
        
        try:
            # 將 MenuItemData 物件列表轉換回字典列表
            data_to_save = [item.to_dict() for item in data]
            
            with open(config_path, 'w', encoding='utf-8') as f:
                # indent=4 讓JSON檔案格式化，更易讀
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            log.info(f"成功將 {len(data)} 個菜單項儲存至 {config_path}")
            
        except Exception as e:
            log.error(f"儲存設定檔時發生錯誤: {e}", exc_info=True)