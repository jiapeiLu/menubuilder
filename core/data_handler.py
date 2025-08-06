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
        """將菜單項資料列表轉換為字典並儲存為JSON檔案。"""
        config_path = MENUITEMS_DIR / f"{config_name}.json"
        
        try:
            # 將 MenuItemData 物件列表轉換回字典列表
            data_to_save = [item.to_dict() for item in data]
            
            with open(config_path, 'w', encoding='utf-8') as f:
                # indent=4 讓JSON檔案格式化，更易讀
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            log.info(f"成功將 {len(data)} 個菜單項儲存至 {config_path}")
            
        except Exception as e:
            log.error(f"儲存設定檔時發生錯誤: {e}", exc_info=True)