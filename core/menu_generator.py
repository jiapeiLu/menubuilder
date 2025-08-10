# core/menu_generator.py
from maya import cmds, mel
from typing import List
from .dto import MenuItemData
from .logger import log
import re # 導入正則表達式模組

OPTIONVAR_KEY = "menubuilder_created_menus"

class MenuGenerator:
    # ... clear_existing_menus() 方法不變 ...
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
                if cmds.menu(menu_name, query=True, exists=True):
                    log.info(f"找到並刪除舊菜單: {menu_name}")
                    cmds.deleteUI(menu_name)
        
        cmds.optionVar(remove=OPTIONVAR_KEY)

    def _generate_command_string(self, item: MenuItemData) -> str:
        original_command = item.function_str.strip()
        '''disable dockable
        if item.is_dockable:
            log.debug(f"為 '{item.menu_label}' 解析 Dockable 啟動資料。")
            ui_name = f"{item.menu_label.replace(' ','_')}_{item.order}_wsControl"
            ui_label = item.menu_label

            # 解析模組名和函式名 (現在是固定的格式)
            callable_line = original_command.strip().split('\n')[-1].strip()
            parts = callable_line.split('.')
            module_name = parts[0]
            func_name = parts[1].replace('()', '')

            # 生成簡單、乾淨的函式呼叫指令
            wrapped_command = (
                f"from menubuilder.core.ui_dockable import launch_dockable_from_data; "
                f"launch_dockable_from_data(ui_name='{ui_name}', ui_label='{ui_label}', module_name='{module_name}', func_name='{func_name}')"
            )
            return wrapped_command'''

        # --- 處理 MEL 或普通 Python 指令 (邏輯不變) ---
        if original_command.lower().startswith("mel:"):
            mel_command = original_command.replace("mel:", "", 1).strip()
            return f'mel.eval("{mel_command}")'
        else:
            return original_command
        
    def build_from_config(self, data: List[MenuItemData]):
        if not data:
            log.warning("沒有可建立的菜單資料。")
            return
        
        sorted_data = sorted(data, key=lambda x: (x.order))
        gMainWindow = mel.eval('$tmpVar=$gMainWindow')
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
                        new_menu_parent = None
                        if i == 0:
                            new_menu_parent = cmds.menu(part, parent=parent, tearOff=True)
                            cmds.optionVar(stringValueAppend=(OPTIONVAR_KEY, new_menu_parent))
                        else:
                            new_menu_parent = cmds.menuItem(label=part, subMenu=True, parent=parent, tearOff=True)
                        parent_menu_cache[full_path_key] = new_menu_parent
                        parent = new_menu_parent
            
            if item.menu_label.strip() in ["-", "---", "separator"]:
                cmds.menuItem(divider=True, parent=parent)
                continue

            command_str = self._generate_command_string(item)
            log.debug(f"生成指令: {command_str}。")
            cmds.menuItem(
                item.menu_label,
                parent=parent,
                command=command_str,
                image=item.icon_path if item.icon_path else "",
            )
        
        log.info(f"成功建立 {len(sorted_data)} 個菜單項。")