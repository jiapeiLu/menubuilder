# controller.py

"""
Menubuilder - Controller Module

這個模組是 Menubuilder 工具的核心，扮演 MVC 架構中的「控制器(Controller)」角色。

它負責：
- 處理來自 UI (View) 的所有使用者事件（按鈕點擊、列表選擇等）。
- 協調 DataHandler (Model) 進行資料的讀取與儲存。
- 呼叫 MenuGenerator 來在 Maya 中實際生成菜單。
- 管理整個應用程式的狀態和業務邏輯。
"""
import functools # 導入 functools 以便使用 wraps
import webbrowser
from .logger import log  # 從我們建立的logger模組導入已經配置好的log實例
from .setting_reader import current_setting
from .ui import MenuBuilderUI, IconBrowserDialog
from .data_handler import DataHandler,MenuItemData
from .script_parser import ScriptParser
from PySide2 import QtWidgets, QtCore
from .menu_generator import MenuGenerator # 導入 MenuGenerator
from maya import cmds, mel
import os
from pathlib import Path

from menubuilder import __version__, __author__

def block_ui_signals(widget_name: str):
    """
    一個可傳參的裝飾器工廠，用於在執行函式期間暫時阻斷指定UI元件的信號。

    Args:
        widget_name (str): 在 self.ui 中要阻斷信號的元件的屬性名稱，
                           例如 'menu_tree_view'。
    
    Returns:
        Callable: 一個真正的裝飾器。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # 獲取要操作的 UI 元件
            widget_to_block = getattr(self.ui, widget_name, None)
            
            if not widget_to_block:
                log.warning(f"在 block_ui_signals 中找不到名為 {widget_name} 的 UI 元件。")
                return func(self, *args, **kwargs)

            # 使用 try...finally 確保信號總能被恢復
            try:
                widget_to_block.blockSignals(True)
                log.debug(f"裝飾器: 已阻斷 {widget_name} 的信號。")
                result = func(self, *args, **kwargs)
            finally:
                widget_to_block.blockSignals(False)
                log.debug(f"裝飾器: 已恢復 {widget_name} 的信號。")
            
            return result
        return wrapper
    return decorator

def preserve_ui_state(func):
    """
    一個裝飾器，用於在執行會刷新UI樹的操作前後，自動保存和還原其展開狀態。

    這解決了因 `populate_menu_tree` 執行 `clear()` 而導致整個樹摺疊的問題，
    極大地提升了使用者體驗。

    Args:
        func (Callable): 被裝飾的目標函式 (必須是 Controller 的一個方法)。

    Returns:
        Callable: 包裝後的函式。
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'ui'):
            return func(self, *args, **kwargs)

        expansion_state = self.ui.get_expansion_state()
        log.debug(f"裝飾器: 狀態已記錄。準備執行 '{func.__name__}'...")

        try:
            result = func(self, *args, **kwargs)
        finally:
            self.ui.set_expansion_state(expansion_state)
            log.debug("裝飾器: UI狀態已還原。")
        
        return result
    return wrapper

class MenuBuilderController:
    """
    Menubuilder 工具的核心，扮演 MVC 架構中的控制器(Controller)角色。

    作為應用程式的大腦，它持有 View (MenuBuilderUI) 和 Model (DataHandler)
    的實例。它負責將UI發出的信號連接到對應的處理函式(slots)，在這些函式中
    執行所有的業務邏輯、資料處理和流程控制，並在必要時命令UI進行更新。
    """
    def __init__(self):
        """初始化 Controller、所有核心模組以及應用程式的狀態變數。"""
        log.info("MenuBuilderController 初始化開始...")
        self.data_handler = DataHandler()
        self.menu_generator = MenuGenerator()
        self.ui = MenuBuilderUI(self)
        self.current_menu_data = []
        self.current_selected_script_path = None
        self.current_config_name = None
        self.current_edit_item = None
        self._signals_connected = False
        self._load_initial_data()
        self._connect_signals()
        log.info("MenuBuilderController 初始化完成。")

    def _connect_signals(self):
        """
        集中管理所有 UI 元件的信號與槽(slots)的連接。
        
        使用 `_signals_connected` 旗標來確保這個連接過程在程式的生命週期中
        只會被執行一次，以避免因模組重載(reload)導致的信號重複連接問題。
        """
        if self._signals_connected:
            log.debug("信號已經連接過，跳過。")
            return
        log.debug("正在進行初次信號連接...")
        self.ui.browse_button.clicked.connect(self.on_browse_script_clicked)
        self.ui.function_list.currentItemChanged.connect(self.on_function_selected)
        self.ui.icon_buildin_btn.clicked.connect(self.on_browse_icon_clicked)
        self.ui.icon_browse_btn.clicked.connect(self.on_browse_custom_icon_clicked)
        self.ui.add_update_button.clicked.connect(self.on_add_item_clicked)
        self.ui.test_run_button.clicked.connect(self.on_test_run_clicked)
        self.ui.save_button.clicked.connect(self.on_save_config_clicked)
        self.ui.build_menus_button.clicked.connect(self.on_build_menu_clicked)
        self.ui.menu_tree_view.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.ui.menu_tree_view.customContextMenuRequested.connect(self.ui.on_tree_context_menu)
        self.ui.menu_tree_view.itemChanged.connect(self.on_tree_item_renamed)
        self.ui.menu_tree_view.drop_event_completed.connect(self.on_drop_event_completed)

        self.ui.open_action.triggered.connect(self.on_file_open)
        self.ui.merge_action.triggered.connect(self.on_file_merge)
        self.ui.save_action.triggered.connect(self.on_save_config_clicked)
        self.ui.save_as_action.triggered.connect(self.on_file_save_as)
        self.ui.exit_action.triggered.connect(self.ui.close)
        
        self.ui.option_box_checkbox.stateChanged.connect(self.on_option_box_changed)
        
        self.ui.about_action.triggered.connect(self.on_about)
        self.ui.github_action.triggered.connect(self.on_view_on_github)

        self._signals_connected = True
        log.debug("信號連接完成。")
        
    def _load_initial_data(self):
        """載入設定中指定的預設菜單設定檔。"""
        default_config = current_setting.get("menuitems")
        self.current_config_name = default_config
        if not default_config:
            log.warning("在 setting.json 中未指定預設的 'menuitems'。")
            return
            
        log.info(f"正在載入預設菜單設定檔: {default_config}.json")
        
        self.current_menu_data = self.data_handler.load_menu_config(default_config)
        
        if self.current_menu_data:
            self.ui.populate_menu_tree(self.current_menu_data)
            self.ui.auto_expand_single_root()
        self._update_ui_title()

    def show_ui(self):
        log.info("顯示 Menubuilder UI。")
        try:
            self.ui.show()
        except Exception as e:
            log.error(f"顯示UI時發生錯誤: {e}", exc_info=True)

    def on_browse_script_clicked(self):
        """當瀏覽按鈕被點擊時觸發。"""
        start_dir = ""
        if self.current_selected_script_path:
            start_dir = os.path.dirname(self.current_selected_script_path)

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, "選擇 Python 腳本", start_dir, "Python Files (*.py)")
        
        if not file_path:
            self.current_selected_script_path = None
            self.ui.current_script_path_label.clear()
            return
            
        self.current_selected_script_path = file_path
        self.ui.current_script_path_label.setText(file_path)
        
        self.ui.function_list.clear()
        functions = ScriptParser.parse_py_file(file_path)
        self.ui.function_list.addItems(functions)
        log.info(f"從 {file_path} 解析出 {len(functions)} 個函式。")

    def on_function_selected(self, current, previous):
        """
        當函式列表中的選項改變時觸發。
        將自動生成完整的執行指令，並填入到手動輸入框中。
        """
        if not current or not self.current_selected_script_path:
            return
        
        func_name = current.text()
        module_name = os.path.basename(self.current_selected_script_path).replace('.py', '')

        generated_label = ScriptParser.generate_label_from_string(func_name)
        
        command_to_run = (
            f"import {module_name}\n"
            f"from importlib import reload\n"
            f"reload({module_name})\n"
            f"{module_name}.{func_name}()"
        )
        
        self.ui.label_input.setText(generated_label)
        self.ui.input_tabs.setCurrentIndex(1)
        self.ui.manual_cmd_input.setText(command_to_run)
        self.ui.python_radio.setChecked(True) # <-- [修改] 自動選中 Python 選項
        
        log.debug(f"已生成指令並填入UI: {command_to_run}")

    @preserve_ui_state
    def on_delete_item_clicked(self):
        """[優化後] 刪除左側樹狀視圖中當前選擇的項目。"""
        selected_items = self.ui.menu_tree_view.selectedItems()
        if not selected_items:
            log.warning("請先在左側列表中選擇要刪除的項目。")
            return
            
        item_to_remove_data = selected_items[0].data(0, QtCore.Qt.UserRole)
        
        if item_to_remove_data:
            self.current_menu_data.remove(item_to_remove_data)
            log.info(f"已刪除菜單項: {item_to_remove_data.menu_label}")
            self.ui.populate_menu_tree(self.current_menu_data)
        else:
            log.warning("無法刪除，所選項目是一個文件夾或沒有關聯資料。請使用右鍵選單刪除文件夾。")
    
    def _is_name_conflict(self, proposed_label: str, proposed_path: str, item_being_updated: MenuItemData = None) -> bool:
        """
        [純資料驅動版] 檢查提議的名稱和路徑組合是否與現有項目或隱性資料夾衝突。
        """
        # 建立一個集合，用來存放所有在 proposed_path 層級下「已被佔用」的名稱
        sibling_names = set()

        # --- 第一步：從 self.current_menu_data 中收集所有「同級功能項」的名稱 ---
        for item in self.current_menu_data:
            if item is item_being_updated:
                continue  # 更新模式下，排除自身
            
            if item.sub_menu_path == proposed_path:
                sibling_names.add(item.menu_label.lower())

        # --- 第二步：從 self.current_menu_data 中推導出所有「同級隱性資料夾」的名稱 ---
        folder_prefix = f"{proposed_path}/" if proposed_path else ""
        
        for item in self.current_menu_data:
            # 我們只關心那些路徑比當前層級更深的項目，因為它們定義了子資料夾
            if item.sub_menu_path.startswith(folder_prefix) and len(item.sub_menu_path) > len(folder_prefix):
                
                # 從項目路徑中，提取出緊跟在當前層級後面的那一部分，也就是「子資料夾」的名稱
                # 例如：當前在 "Tools"，項目路徑是 "Tools/Rig/Freeze"，那麼 rest_of_path 就是 "Rig/Freeze"
                rest_of_path = item.sub_menu_path[len(folder_prefix):]
                folder_name = rest_of_path.split('/')[0]
                sibling_names.add(folder_name.lower())

        # --- 第三步：執行最終檢查 ---
        if proposed_label.lower() in sibling_names:
            log.warning(f"名稱衝突：在 '{proposed_path}' 路徑下已存在名為 '{proposed_label}' 的項目或資料夾。")
            QtWidgets.QMessageBox.warning(self.ui, "命名衝突", f"在路徑 '{proposed_path}' 下，已經存在一個同名的項目或子資料夾了。")
            return True

        return False
    
    def _sync_data_from_ui(self):
        """
        核心同步函式：從UI樹狀視圖掃描最新狀態，並更新記憶體中的資料列表。

        這是實現「UI與資料延遲同步」混合模式的關鍵。它呼叫 UI 的
        `get_ordered_data_from_tree` 方法來獲取一個完全反映使用者視覺排序
        和結構的列表，然後用這個列表覆蓋 `self.current_menu_data`，並重新
        計算所有項目的 `order` 屬性。
        """
        log.debug("從 UI 同步資料...")
        ordered_data_from_ui = self.ui.get_ordered_data_from_tree()
        
        final_data_list = []
        for i, item_data in enumerate(ordered_data_from_ui):
            item_data.order = (i + 1) * 10
            final_data_list.append(item_data)
        
        self.current_menu_data = final_data_list
        log.debug("資料同步完成。")

    def on_save_config_clicked(self):
        """儲存當前的菜單結構到檔案。"""
        self._sync_data_from_ui()
        config_name = current_setting.get("menuitems")
        self.data_handler.save_menu_config(config_name, self.current_menu_data)

    def on_build_menu_clicked(self):
        """
        處理「在Maya中產生/刷新菜單」按鈕的點擊事件。

        執行最終的菜單生成流程：
        1. 呼叫 `_sync_data_from_ui()` 確保資料與UI同步。
        2. 呼叫 `menu_generator.clear_existing_menus()` 清理舊菜單。
        3. 呼叫 `menu_generator.build_from_config()` 用最新資料生成新菜單。
        """
        self._sync_data_from_ui()
        log.info("開始生成/刷新 Maya 菜單...")
        
        self.menu_generator.clear_existing_menus()
        self.menu_generator.build_from_config(self.current_menu_data)
        
        cmds.inViewMessage(amg='<hl>菜單已成功生成/刷新！</hl>', pos='midCenter', fade=True)

    def on_file_open(self):
        """處理 '開啟' 動作。"""
        log.debug("處理 '開啟' 動作...")
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, "開啟菜單設定檔", default_dir, "JSON Files (*.json)")
        
        if not file_path:
            log.debug("使用者取消了檔案選擇。")
            return
        
        config_name = Path(file_path).stem
        self.current_config_name = config_name

        new_data = self.data_handler.load_menu_config(config_name)
        self.current_menu_data = new_data
        
        self.ui.populate_menu_tree(self.current_menu_data)
        self.ui.auto_expand_single_root()
        
        self._update_ui_title()
        log.info(f"已成功開啟並載入設定檔: {file_path}")

    def on_file_merge(self):
        """處理 '合併' 動作。"""
        log.debug("處理 '合併' 動作...")
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, "選擇要合併的設定檔", default_dir, "JSON Files (*.json)")

        if not file_path:
            return
            
        config_name = Path(file_path).stem
        new_data = self.data_handler.load_menu_config(config_name)

        if new_data:
            self.current_menu_data.extend(new_data)
            self.ui.populate_menu_tree(self.current_menu_data)
            self.ui.auto_expand_single_root()
            log.info(f"已成功將 {file_path} 的內容合併至當前設定。")

    def on_file_save_as(self):
        """處理 '另存為' 動作。"""
        log.debug("處理 '另存為' 動作...")
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self.ui, "另存為菜單設定檔", default_dir, "JSON Files (*.json)")

        if not file_path:
            return
            
        self._sync_data_from_ui()

        config_name = Path(file_path).stem
        self.current_config_name = config_name
        self.data_handler.save_menu_config(config_name, self.current_menu_data)
        self._update_ui_title()
        log.info(f"已將當前設定另存為: {file_path}")

    def on_tree_item_double_clicked(self, item, column):
        """當項目被雙擊時，進入「編輯模式」。"""
        item_data = item.data(0, QtCore.Qt.UserRole)
        
        if not item_data :
            log.debug("雙擊的是文件，只能重新命名。")
            return
        if item_data.is_divider:
            log.debug("雙擊的是分隔線，不可編輯。")
            return

        log.info(f"正在編輯項目: {item_data.menu_label}")
        self.current_edit_item = item
        
        self._refresh_editor_panel()

    @preserve_ui_state
    def on_add_item_clicked(self):
        """
        處理「新增/更新」按鈕的點擊事件。
        """
        edited_data = self.ui.get_attributes_from_fields()
        if not edited_data.menu_label: # 指令可以為空 (作為資料夾)
            log.warning("請確保'菜單標籤'欄位不為空。")
            return

        # --- [核心修正] 在執行操作前，進行名稱衝突驗證 ---
        item_to_update = self.current_edit_item.data(0, QtCore.Qt.UserRole) if self.current_edit_item else None
        
        if self._is_name_conflict(edited_data.menu_label, edited_data.sub_menu_path, item_to_update):
            return # 如果檢測到衝突，則終止操作
        # --- 驗證結束 ---

        self._sync_data_from_ui()

        if self.current_edit_item:
            # 更新操作 (舊邏輯不變)
            item_data_to_update = self.current_edit_item.data(0, QtCore.Qt.UserRole)
            log.info(f"更新項目 '{item_data_to_update.menu_label}'...")
            
            item_data_to_update.menu_label = edited_data.menu_label
            item_data_to_update.sub_menu_path = edited_data.sub_menu_path
        
        self.ui.populate_menu_tree(self.current_menu_data)

    def on_context_send_path(self, path: str):
        """接收來自右鍵選單的路徑，並更新到UI輸入框中。"""
        log.debug(f"從右鍵選單接收到路徑: {path}")
        self.ui.path_input.setText(path)

    def on_context_add_under(self, parent_path: str):
        """在指定的父路徑下準備新增一個項目。"""
        log.debug(f"準備在 '{parent_path}' 下新增項目。")
        
        self.ui.path_input.setText(parent_path)
        self.ui.label_input.clear()
        self.ui.manual_cmd_input.clear()
        
        self.current_edit_item = None
        
        self._refresh_editor_panel()

        self.ui.label_input.setFocus()

    @preserve_ui_state
    def on_context_delete(self, item: QtWidgets.QTreeWidgetItem):
        """[修正後] 處理刪除操作，可能是單一項目或整個文件夾。"""
        if not isinstance(item, QtWidgets.QTreeWidgetItem):
            log.error(f"刪除操作收到了錯誤的物件類型: {type(item)}")
            return

        item_path = self.ui.get_path_for_item(item)
        item_data = item.data(0, QtCore.Qt.UserRole)
        
        items_to_delete = []
        
        self._sync_data_from_ui()

        is_folder = item.childCount() > 0 or not item_data

        if is_folder:
            reply = QtWidgets.QMessageBox.question(
                self.ui, '確認刪除', 
                f"您確定要刪除 '{item_path}' 及其下的所有內容嗎？\n此操作無法復原。",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return
            
            items_to_delete = [
                data for data in self.current_menu_data 
                if data.sub_menu_path == item_path or data.sub_menu_path.startswith(item_path + '/')
            ]
            if item_data and item_data not in items_to_delete:
                items_to_delete.append(item_data)
        else:
            if item_data:
                items_to_delete.append(item_data)
        
        if items_to_delete:
            log.info(f"準備刪除 {len(items_to_delete)} 個項目...")
            self.current_menu_data = [d for d in self.current_menu_data if d not in items_to_delete]
            self.ui.populate_menu_tree(self.current_menu_data)
    
    
    @block_ui_signals('menu_tree_view')
    def on_tree_item_renamed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        """
        [最終穩健版] 當項目文字被編輯後觸發，能正確處理功能項和資料夾的重新命名驗證。
        """
        if self.current_edit_item:
            log.debug("正在編輯模式中，忽略因程式化更新觸發的 itemChanged 信號。")
            return

        # 1. 首先，從 item_map 中找到該 UI 物件對應的「舊路徑」，這是最可靠的資訊來源
        old_path = None
        for path, ui_item in self.ui.item_map.items():
            if ui_item == item:
                old_path = path
                break
        
        if old_path is None:
            # 如果在 map 中找不到，可能是一個極端情況或新建的項目，安全起見直接刷新返回
            self._sync_data_from_ui()
            self.ui.populate_menu_tree(self.current_menu_data)
            return

        # 2. 根據「舊路徑」和 UI 上的新文字，推導所需的所有資訊
        new_name = item.text(0)
        old_name = old_path.split('/')[-1]
        parent_path = "/".join(old_path.split('/')[:-1])

        if new_name == old_name:
            return

        # 3. 執行名稱衝突驗證
        item_data = item.data(0, QtCore.Qt.UserRole)
        if self._is_name_conflict(new_name, parent_path, item_data):
            log.warning(f"重新命名失敗，名稱 '{new_name}' 已存在。將名稱還原為 '{old_name}'。")
            # 驗證失敗，將 UI 文字還原
            item.setText(0, old_name)
            return

        # 4. 驗證通過後，才執行資料同步和 UI 刷新
        log.info(f"項目已從 '{old_name}' 重命名為 '{new_name}'。")
        new_path = f"{parent_path}/{new_name}" if parent_path else new_name
        
        expansion_state_before = self.ui.get_expansion_state()
        new_expansion_state = set()
        for path in expansion_state_before:
            if path == old_path or path.startswith(old_path + '/'):
                corrected_path = path.replace(old_path, new_path, 1)
                new_expansion_state.add(corrected_path)
            else:
                new_expansion_state.add(path)
        
        self._sync_data_from_ui()
        self.ui.populate_menu_tree(self.current_menu_data)
        self.ui.set_expansion_state(new_expansion_state)
            
    def on_browse_icon_clicked(self):
        """當'瀏覽圖示'按鈕被點擊時，創建並顯示圖示瀏覽器。"""
        log.debug("開啟圖示瀏覽器...")
        icon_browser = IconBrowserDialog(self.ui)
        icon_browser.icon_selected.connect(self.on_icon_selected_from_browser)
        icon_browser.exec_()

    def on_browse_custom_icon_clicked(self):
        """處理'瀏覽自訂圖示'按鈕的點擊事件。"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.ui, 
            "選擇自訂圖示檔案", 
            "", 
            "Image Files (*.png *.svg *.jpg *.bmp)"
        )
        if file_path:
            self.ui.icon_input.setText(file_path)
            log.info(f"選擇了自訂圖示: {file_path}")

    def on_icon_selected_from_browser(self, icon_path: str):
        """當圖示瀏覽器發出'icon_selected'信號時，接收圖示路徑並更新UI。"""
        log.debug(f"接收到選擇的圖示路徑: {icon_path}")
        self.ui.icon_input.setText(icon_path)
    
    def _update_ui_title(self):
        """一個新的輔助函式，用來通知UI更新標題。"""
        self.ui.update_tree_view_title(self.current_config_name)

    @block_ui_signals('menu_tree_view')
    def _refresh_editor_panel(self):
        """
        [最終修正版] 根據 self.current_edit_item 的狀態，刷新右側編輯面板。
        此版本透過裝飾器阻斷信號，對意外的UI刷新具有免疫力。
        """
        self.ui.clear_all_highlights()

        if self.current_edit_item:
            # ... (內部的邏輯完全不變)
            self.ui.set_item_highlight(self.current_edit_item, True)
            item_data = self.current_edit_item.data(0, QtCore.Qt.UserRole)
            if not item_data:
                self.current_edit_item = None
                return

            self.ui.add_update_button.setText("更新項目 (Update)")
            self.ui.option_box_checkbox.setEnabled(True)
            self.ui.set_attributes_to_fields(item_data)
        else:
            # --- 新增模式 ---
            self.ui.add_update_button.setText("新增至結構")
            self.ui.python_radio.setChecked(True)
            self.ui.option_box_checkbox.setEnabled(False)
            self.ui.option_box_checkbox.setChecked(False)

    @preserve_ui_state
    @block_ui_signals('menu_tree_view')
    def on_option_box_changed(self, state):
        """
        [融合使用者建議的最終版] 當'作為選項框'核取方塊的狀態改變時觸發。
        此版本使用在當前情境下穩定的 'order' 屬性來恢復編輯狀態，體驗不中斷。
        """
        if not self.current_edit_item:
            # ... (驗證邏輯不變)
            return

        item_data = self.current_edit_item.data(0, QtCore.Qt.UserRole)
        if not item_data:
            return

        should_become_option_box = state > 0
        if should_become_option_box == item_data.is_option_box:
            return

        # ... (其他驗證邏輯不變)

        # --- [核心修正] 採用 order 作為恢復編輯狀態的依據 ---
        
        # 1. 在 UI 刷新前，記下這個穩定不變的 order 值
        original_order = item_data.order
        
        # 2. 更新資料並重繪 UI
        item_data.is_option_box = should_become_option_box
        log.debug(f"項目 '{item_data.menu_label}' 的 is_option_box 狀態變更為: {should_become_option_box}")
        self.ui.populate_menu_tree(self.current_menu_data)

        # 3. 遍歷新生成的 UI 項目，找到 order 值匹配的那一個
        new_ui_item_found = None
        for ui_item in self.ui.item_map.values():
            data_on_new_item = ui_item.data(0, QtCore.Qt.UserRole)
            if data_on_new_item and data_on_new_item.order == original_order:
                new_ui_item_found = ui_item
                break  # 找到了就跳出循環

        # 4. 更新引用並恢復高亮，保持編輯模式
        if new_ui_item_found:
            self.current_edit_item = new_ui_item_found
            self.ui.set_item_highlight(self.current_edit_item, True)
            log.debug(f"成功使用 'order'({original_order}) 恢復編輯狀態。")
        else:
            log.error(f"使用 'order' 恢復狀態失敗，找不到 order 為 {original_order} 的項目。已強制退出編輯模式。")
            self.current_edit_item = None
            self._refresh_editor_panel()

    @preserve_ui_state
    def on_drop_event_completed(self, source_item: QtWidgets.QTreeWidgetItem, 
                                target_item: QtWidgets.QTreeWidgetItem, 
                                indicator: QtWidgets.QAbstractItemView.DropIndicatorPosition):
        """
        [增加新規則] 處理拖放，增加驗證：已是父物件的項目，不能成為選項框。
        """
        log.debug("拖放完成，開始同步資料和狀態...")
        
        source_data = source_item.data(0, QtCore.Qt.UserRole)
        if not source_data:
            return

        # 1. 在同步UI、打亂順序之前，先檢查被拖曳的物件是否已經是「父物件」。
        is_source_a_parent = False
        option_box_to_move_with = None
        try:
            original_index = self.current_menu_data.index(source_data)
            if (original_index + 1) < len(self.current_menu_data):
                item_after = self.current_menu_data[original_index + 1]
                if item_after.is_option_box:
                    is_source_a_parent = True
                    option_box_to_move_with = item_after
        except ValueError:
            pass

        # 2. 執行UI同步
        self._sync_data_from_ui()

        # 3. 處理「創建 Option Box」的邏輯
        should_be_option_box = False
        if indicator == QtWidgets.QAbstractItemView.OnItem and target_item:
            target_data = target_item.data(0, QtCore.Qt.UserRole)
            if target_data and not target_data.is_option_box:
                
                # --- [核心修正] 在這裡加入新的驗證規則 ---
                if not is_source_a_parent:
                    # 只有當被拖曳的物件自己不是父物件時，才允許它成為 Option Box
                    should_be_option_box = True
                    source_data.sub_menu_path = target_data.sub_menu_path
                else:
                    # 如果它已經是父物件，則阻止此操作，並給出提示
                    log.warning(f"操作被阻止：項目 '{source_data.menu_label}' 因其已有選項框，不能成為其他項目的選項框。")
                    # 保持 should_be_option_box 為 False，拖放會被視為普通的排序操作

        if source_data.is_option_box != should_be_option_box:
             source_data.is_option_box = should_be_option_box
             log.debug(f"項目 '{source_data.menu_label}' 的 is_option_box 狀態變更為: {should_be_option_box}")

        # 4. 處理 Option Box 「跟隨」的邏輯 (這部分不變)
        if option_box_to_move_with:
            option_box_to_move_with.sub_menu_path = source_data.sub_menu_path
            self.current_menu_data.remove(option_box_to_move_with)
            new_parent_index = self.current_menu_data.index(source_data)
            self.current_menu_data.insert(new_parent_index + 1, option_box_to_move_with)
            log.debug(f"已將 Option Box 移動到新位置。")

        # 5. 用最終修正後的資料，徹底重繪 UI
        self.ui.populate_menu_tree(self.current_menu_data)
        
        if self.current_edit_item:
            self._refresh_editor_panel()
        
    def on_about(self):
        """
        顯示一個「關於」對話框。
        """
        QtWidgets.QMessageBox.about(
            self.ui,
            "關於 Menubuilder",
            f"""
            <b>Menubuilder for Maya</b>
            <p>Version {__version__}</p>
            <p>一個視覺化的 Maya 菜單編輯與管理工具。</p>
            <p>開發者: <i>{__author__}</i></p>
            <p>此工具在 AI Assistant 的協作下完成開發。</p>
            """
        )

    def on_view_on_github(self):
        """
        在預設的網頁瀏覽器中打開專案的 GitHub 頁面。
        """
        url = "https://github.com/jiapeiLu/menubuilder"
        log.info(f"正在打開網頁: {url}")
        webbrowser.open(url)

    @preserve_ui_state
    def on_context_add_separator(self, target_item: QtWidgets.QTreeWidgetItem):
        """
        在指定項目的下方新增一個分隔線。
        """
        self._sync_data_from_ui()
        
        separator_data = MenuItemData(
            menu_label="---",
            is_divider=True
        )

        insert_index = len(self.current_menu_data)

        if target_item:
            target_data = target_item.data(0, QtCore.Qt.UserRole)
            if target_data:
                separator_data.sub_menu_path = target_data.sub_menu_path
                try:
                    insert_index = self.current_menu_data.index(target_data) + 1
                except ValueError:
                    log.warning("在資料列表中找不到目標項目，分隔線將被添加到末尾。")
            else:
                 separator_data.sub_menu_path = self.ui.get_path_for_item(target_item)
        else:
            separator_data.sub_menu_path = ""
        
        self.current_menu_data.insert(insert_index, separator_data)
        
        self.ui.populate_menu_tree(self.current_menu_data)

    def on_test_run_clicked(self):
        """
        即時測試編輯器中的指令，並將結果輸出到 Script Editor。
        """
        # 從 UI 獲取當前的指令和語言類型
        code_to_run = self.ui.manual_cmd_input.toPlainText().strip()
        is_mel = self.ui.mel_radio.isChecked()

        if not code_to_run:
            log.warning("指令為空，沒有可測試的內容。")
            cmds.warning("Command is empty. Nothing to test.")
            return

        # --- 以下完全是您原型中的除錯輸出邏輯 ---
        print("\n" + "="*50)
        print("--- Menubuilder: Attempting Test Run ---")
        
        result = None
        success = False
        error_info = ""

        try:
            if not is_mel: # Python radio is checked
                print("Executing as PYTHON:\n")
                print(code_to_run + "\n")
                # 優先嘗試用 eval()
                try:
                    result = eval(code_to_run, globals(), locals())
                except SyntaxError:
                    # 退回到 exec()
                    exec(code_to_run, globals(), locals())
                    result = "<Execution of statement successful (no return value)>"
                success = True
            
            else: # MEL radio is checked
                print("Executing as MEL:\n")
                print(code_to_run + "\n")
                result = mel.eval(code_to_run)
                success = True

        except Exception as e:
            error_info = f"# Error: {e}"
            success = False

        # --- 格式化最終輸出 ---
        if success:
            if result is not None:
                print(f"// Result: {repr(result)} //\n")
            print("Executed successfully.")
            cmds.inViewMessage(amg='<hl>測試執行成功！</hl>', pos='midCenter', fade=True)
        else:
            print("Execution failed!")
            print(error_info)
            # 使用 Maya 的 warning 彈出一個更明顯的錯誤提示
            cmds.warning(f"測試執行失敗: {error_info}")
        
        print("\n--- Test Run Finished ---")
        print("="*50 + "\n")