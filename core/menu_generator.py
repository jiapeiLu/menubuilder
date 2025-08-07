# core/menu_generator.py
from maya import cmds, mel
from typing import List
from .dto import MenuItemData
from .logger import log

OPTIONVAR_KEY = "menubuilder_created_menus"

class MenuGenerator:
    """負責在Maya中實際生成和銷毀菜單。"""

    def clear_existing_menus(self):
        """讀取 optionVar，清除由本工具先前創建的所有頂層菜單。"""
        log.info("正在透過 optionVar 清除舊的 Menubuilder 菜單...")
        if not cmds.optionVar(exists=OPTIONVAR_KEY):
            return

        created_menus = cmds.optionVar(query=OPTIONVAR_KEY)
        if not isinstance(created_menus, list):
            created_menus = [created_menus]
            
        if created_menus:
            for menu_name in created_menus:
                # 必須檢查UI物件是否存在，因為使用者可能手動關閉了
                if cmds.menu(menu_name, query=True, exists=True):
                    log.info(f"找到並刪除舊菜單: {menu_name}")
                    cmds.deleteUI(menu_name)
        
        cmds.optionVar(remove=OPTIONVAR_KEY)
    
    def _generate_command_string(self, item: MenuItemData) -> str:
        """根據 MenuItemData 生成可執行的 command 字串。"""
        if ".mel" in item.module_path.lower() or item.function_str.lower().startswith("mel:"):
            mel_command = item.function_str.replace("mel:", "", 1).strip()
            return f'mel.eval("{mel_command}")'
        return item.function_str

    def build_from_config(self, data: List[MenuItemData]):
        """根據提供的資料列表，在Maya中建立完整的菜單結構。"""
        if not data:
            log.warning("沒有可建立的菜單資料。")
            return
        
        # 排序對於建立過程至關重要
        sorted_data = sorted(data, key=lambda x: (x.order))
        gMainWindow = mel.eval('$tmpVar=$gMainWindow')
        
        # 緩存將儲存每個路徑對應的父級菜單UI名稱
        parent_menu_cache = {}

        for item in sorted_data:
            parent = gMainWindow
            
            if item.sub_menu_path:
                path_parts = item.sub_menu_path.split('/')
                full_path_key = ""

                for i, part in enumerate(path_parts):
                    full_path_key = f"{full_path_key}/{part}" if full_path_key else part

                    if full_path_key in parent_menu_cache:
                        parent = parent_menu_cache[full_path_key]
                    else:
                        # [核心邏輯重構]
                        # 根據層級使用不同的指令來創建菜單
                        new_menu_parent = None
                        if i == 0:
                            # 頂層菜單: 使用 cmds.menu
                            new_menu_parent = cmds.menu(part, parent=parent, tearOff=True)
                            # 只有頂層菜單需要被記錄以便刪除
                            cmds.optionVar(stringValueAppend=(OPTIONVAR_KEY, new_menu_parent))
                            log.debug(f"建立頂層菜單: {part} -> {new_menu_parent}")
                        else:
                            # 子菜單: 使用 cmds.menuItem(subMenu=True)
                            new_menu_parent = cmds.menuItem(label=part, subMenu=True, parent=parent, tearOff=True)
                            log.debug(f"建立子菜單: {part} -> {new_menu_parent}")

                        parent_menu_cache[full_path_key] = new_menu_parent
                        parent = new_menu_parent
            
            # 處理分隔符
            if item.menu_label.strip() in ["-", "---", "separator"]:
                cmds.menuItem(divider=True, parent=parent)
                continue

            # 創建最終的功能菜單項
            command_str = self._generate_command_string(item)
            cmds.menuItem(
                item.menu_label,
                parent=parent,
                command=command_str,
                image=item.icon_path if item.icon_path else "",
            )
        
        log.info(f"成功建立 {len(sorted_data)} 個菜單項。")