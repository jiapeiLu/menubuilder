# core/data_handler.py
import json
from pathlib import Path
from typing import List, Dict, Any
from .dto import MenuItemData
from .logger import log

# 動態獲取 menuitems 資料夾的路徑
MENUITEMS_DIR = Path(__file__).parent.parent / "menuitems"

class DataHandler:
    """負責讀取和寫入菜單設定檔。"""

    def load_menu_config(self, config_name: str) -> List[MenuItemData]:
        """
        從 menuitems 資料夾載入指定的設定檔。
        config_name: 不含 .json 副檔名的檔案名，例如 "TempBar"。
        """
        config_path = MENUITEMS_DIR / f"{config_name}.json"
        
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
        """將菜單項資料儲存為JSON檔案 (此階段先留空)。"""
        # 這個功能將在 Phase 2 實現
        log.info("save_menu_config() 已被呼叫，但功能將在Phase 2實現。")
        pass