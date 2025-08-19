# menubuilder/core/handlers/file_io_handler.py

from PySide2 import QtWidgets
from pathlib import Path
from maya import cmds, mel

from ..logger import log
from ..translator import tr
from ..dto import MenuItemData

# 為了型別提示 (Type Hinting) 而導入
from typing import TYPE_CHECKING, List
if TYPE_CHECKING:
    from ..controller import MenuBuilderController
    from ..ui import MenuBuilderUI

class FileIOHandler:
    """
    專門處理所有與檔案 I/O 相關的邏輯，如開啟、儲存、合併等。
    """
    def __init__(self, controller: "MenuBuilderController"):
        log.debug(f'初始化{self.__class__.__name__}')
        self.controller:MenuBuilderController = controller
        self.ui:MenuBuilderUI = controller.ui
        self.data_handler = controller.data_handler # 方便快速存取

    def connect_signals(self):
        """連接所有與檔案操作相關的 UI 信號。"""
        self.ui.open_action.triggered.connect(self.on_file_open)
        self.ui.merge_action.triggered.connect(self.on_file_merge)
        self.ui.save_action.triggered.connect(self.on_save_config_clicked)
        self.ui.save_as_action.triggered.connect(self.on_file_save_as)
        self.ui.import_from_shelf_action.triggered.connect(self.on_import_from_shelf)
        self.ui.exit_action.triggered.connect(self.on_file_exit)
        # 主面板上的儲存按鈕也屬於檔案操作
        self.ui.save_button.clicked.connect(self.on_save_config_clicked)
        log.debug("FileIOHandler signals connected.")

    # --- 以下是從主控制器遷移過來的函式 ---

    def _update_ui_title(self):
        """輔助函式，用來通知UI更新標題。"""
        self.ui.update_tree_view_title(self.controller.current_config_name)

    def on_file_exit(self):
        """
        處理「離開」動作，關閉主視窗。
        """
        log.info("使用者點擊離開，正在關閉視窗...")
        # self.ui 是指向主視窗(QMainWindow)的參考，直接呼叫它的 close() 方法即可
        self.ui.close()

    def on_save_config_clicked(self):
        """儲存當前的菜單結構到檔案。"""
        self.controller._sync_data_from_ui()
        # 注意：此處儲存的是當前 controller 內的 config name
        self.data_handler.save_menu_config(self.controller.current_config_name, self.controller.current_menu_data)
        self.controller.set_dirty(False)

    def on_file_open(self):
        """處理 '開啟' 動作。"""
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, tr('controller_open_config_title'), default_dir, "JSON Files (*.json)")
        
        if not file_path:
            return
        
        config_name = Path(file_path).stem
        self.controller.current_config_name = config_name

        new_data = self.data_handler.load_menu_config(config_name)
        self.controller.current_menu_data = new_data
        
        # [重構] 呼叫 Controller 的集中刷新函式
        self.controller._refresh_ui_tree_and_paths()
        self.ui.auto_expand_single_root()
        self._update_ui_title()
        self.controller.set_dirty(False)

    def on_file_merge(self):
        """處理 '合併' 動作。"""
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, tr('controller_merge_config_title'), default_dir, "JSON Files (*.json)")

        if not file_path:
            return
            
        config_name = Path(file_path).stem
        new_data = self.data_handler.load_menu_config(config_name)

        if new_data:
            self.controller.current_menu_data.extend(new_data)
            # [重構] 呼叫 Controller 的集中刷新函式
            self.controller._refresh_ui_tree_and_paths()
            self.ui.auto_expand_single_root()

    def on_file_save_as(self):
        """處理 '另存為' 動作。"""
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self.ui, tr('controller_save_as_config_title'), default_dir, "JSON Files (*.json)")

        if not file_path:
            return
            
        self.controller._sync_data_from_ui()

        config_name = Path(file_path).stem
        self.controller.current_config_name = config_name
        self.data_handler.save_menu_config(config_name, self.controller.current_menu_data)
        self._update_ui_title()
        self.controller.set_dirty(False)

    def _perform_shelf_import(self, shelf_names: List[str]) -> List[MenuItemData]:
        """
        [新增] 根據提供的 Shelf 名稱列表，讀取其內容並轉換為 MenuItemData 物件列表。
        """
        new_menu_items = []
        for shelf_name in shelf_names:
            log.info(f"正在從 Shelf '{shelf_name}' 匯入...")
            try:
                # 獲取一個 Shelf 下的所有子元件 (按鈕、分隔線等)
                shelf_buttons = cmds.shelfLayout(shelf_name, query=True, childArray=True)
                if not shelf_buttons:
                    continue

                for button in shelf_buttons:
                    # 我們只關心 shelfButton 類型的元件
                    if cmds.objectTypeUI(button) != 'shelfButton':
                        continue
                    
                    # 提取按鈕屬性
                    command = cmds.shelfButton(button, query=True, command=True)
                    # 嘗試獲取註解 (通常是工具提示)，如果沒有則用標籤
                    label = cmds.shelfButton(button, query=True, annotation=True)
                    if not label:
                        label = cmds.shelfButton(button, query=True, label=True)
                    if not label: # 如果都沒有，則使用按鈕的物件名
                        label = button
                    
                    icon = cmds.shelfButton(button, query=True, image=True)
                    
                    # 判斷指令類型
                    command_type = cmds.shelfButton(button, query=True, sourceType =True)

                    # 創建 MenuItemData 物件
                    item_data = MenuItemData(
                        sub_menu_path=shelf_name, # 使用 Shelf 名稱作為預設路徑
                        menu_label=label.strip(),
                        function_str=command,
                        icon_path=icon if icon != "commandButton.png" else "", # 忽略預設圖示
                        command_type=command_type
                    )
                    new_menu_items.append(item_data)
            except Exception as e:
                log.error(f"匯入 Shelf '{shelf_name}' 時發生錯誤: {e}", exc_info=True)
        
        return new_menu_items

    def on_import_from_shelf(self):
        """
        處理「從 Shelf 匯入」的動作。
        [最終版本]
        """
        # 因為 ShelfImportDialog 已經被移到新檔案，我們需要修正 import 路徑
        from ..shelf_import import ShelfImportDialog
        dialog = ShelfImportDialog(self.ui)
        
        # exec_() 會顯示對話框，並等待使用者操作
        # 如果使用者點擊 "Import"，它會返回 True
        if dialog.exec_(): 
            selected_shelves = dialog.get_selected_shelves()
            if not selected_shelves:
                return

            log.info(f"使用者選擇了要匯入的 Shelves: {selected_shelves}")
            
            # 呼叫核心邏輯，獲取轉換後的 MenuItemData 列表
            new_items = self._perform_shelf_import(selected_shelves)
            
            if new_items:
                # 將新項目添加到當前的菜單資料中
                self.controller.current_menu_data.extend(new_items)
                self.controller.set_dirty(True)
                # 呼叫主控制器的刷新方法，更新整個 UI
                self.controller._refresh_ui_tree_and_paths()