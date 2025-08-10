# core/dto.py
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class MenuItemData:
    """一個標準的資料容器，用來表示單一菜單項的資料。"""
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