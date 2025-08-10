"""
Menubuilder - Data Transfer Object (DTO) Module

這個模組定義了專案中最核心的資料結構 `MenuItemData`。

`MenuItemData` 作為一個 dataclass，被用來在不同模組之間標準化地傳遞
菜單項目的屬性資料，例如標籤、指令、路徑等。它扮演著資料容器的角色，
確保了資料在整個應用程式中的一致性和可預測性。
"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class MenuItemData:
    """
    一個標準的資料容器 (Data Transfer Object)，用來表示單一菜單項目的所有屬性。
    
    作為應用程式的模型(Model)核心，它確保了菜單資料在UI、資料處理器和
    菜單生成器之間傳遞時的結構一致性。使用 @dataclass 裝飾器可以簡化
    其屬性的定義和初始化。
    """
    sub_menu_path: str = ""
    order: int = 10
    function_str: str = ""
    menu_label: str = ""
    module_path: str = ""
    icon_path: str = ""
    #is_dockable: bool = False
    is_option_box: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MenuItemData':
        """從字典創建一個 MenuItemData 實例。"""
        # 這會自動匹配字典的鍵到類別的屬性
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """將 MenuItemData 實例轉換回字典，方便儲存為JSON。"""
        return self.__dict__