"""
Menubuilder - Maya Menu Generator Module

這個模組是連接 menubuilder 資料與 Maya 實際UI之間的橋樑。

它的核心職責是接收一個 `MenuItemData` 物件列表，並根據其中的
資料，使用 maya.cmds 來動態地創建、銷毀和刷新 Maya 主視窗上
的菜單和菜單項。所有直接與 Maya 菜單UI互動的程式碼都應封裝在此處。
"""
from maya import cmds, mel
from typing import List
from .dto import MenuItemData
from .logger import log
import re # 導入正則表達式模組

OPTIONVAR_KEY = "menubuilder_created_menus"

class MenuGenerator:
    """
    負責在Maya中實際生成和銷毀菜單。

    這個類別是 Menubuilder 資料邏輯與 Maya UI 之間的最終橋樑。
    它接收一個 `MenuItemData` 物件的列表，並將其轉換為一系列
    `maya.cmds.menu` 和 `maya.cmds.menuItem` 的呼叫，以在Maya
    主菜單欄上建構出使用者定義的結構。
    """
    def clear_existing_menus(self):
        """
        清理所有由 Menubuilder 先前創建的頂層菜單。

        此函式透過讀取儲存在 Maya `optionVar` (`menubuilder_created_menus`) 中的
        菜單名稱列表，來安全地識別並刪除由本工具管理的菜單，從而避免在
        刷新時產生重複的菜單。
        """
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
        """
        一個私有輔助函式，根據 MenuItemData 物件的內容生成最終的可執行指令字串。

        它會處理不同的指令類型，例如將 'mel:' 前綴的指令包裝在 `mel.eval()` 中。
        這是將儲存的 `function_str` 轉換為 `cmds.menuItem` 所需 `command` 參數的
        最後一步。

        Args:
            item (MenuItemData): 包含指令資訊的菜單項資料物件。

        Returns:
            str: 一個準備好被 Maya menuItem 執行的單行指令字串。
        """
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
        """
        接收一個已排序的資料列表，並在Maya中建構出完整的菜單結構。

        這是本類別的核心方法。其主要執行流程如下：
        1. 根據 `order` 屬性對傳入的資料列表進行最終排序。
        2. 遍歷每一個 `MenuItemData` 物件。
        3. 對於每個項目，解析其 `sub_menu_path`，並使用快取 (`parent_menu_cache`)
           來遞迴地創建或查找對應的父級子菜單。
           - 頂層菜單使用 `cmds.menu()` 創建。
           - 子菜單使用 `cmds.menuItem(subMenu=True)` 創建。
        4. 處理特殊項目，如分隔符(`separator`)。
        5. 呼叫 `_generate_command_string` 來獲取最終指令。
        6. 創建最終的 `cmds.menuItem`，並根據資料設定其屬性（如 `optionBox`, `image` 等）。

        Args:
            data (List[MenuItemData]): 一個包含了所有菜單項資料的物件列表。
        """
        if not data:
            log.warning("沒有可建立的菜單資料。")
            return
        
        sorted_data = sorted(data, key=lambda x: (x.order))
        gMainWindow = mel.eval('$tmpVar=$gMainWindow')
        parent_menu_cache = {}

        for item in sorted_data:
            # [核心修改] 使用新的 is_divider 屬性
            if item.is_divider:
                cmds.menuItem(divider=True, parent=parent)
                continue # 處理完畢，跳到下一個項目

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
            # --- [核心修改] ---
            # 檢查是否為 Option Box
            is_opt_box = item.is_option_box
            
            # 為 Option Box 自動指定 Maya 內建圖示
            icon_path = ":/options.png" if is_opt_box else (item.icon_path if item.icon_path else "")
            
            cmds.menuItem(
                item.menu_label,
                parent=parent,
                command=command_str,
                image=icon_path,
                optionBox=is_opt_box  # <-- 關鍵旗標
            )
        
        log.info(f"成功建立 {len(sorted_data)} 個菜單項。")