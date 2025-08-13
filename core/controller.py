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
from .translator import tr
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
        language = current_setting.get('language', 'en_us')
        log.info(f"當前語言設定: {language!r} " )
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

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, tr('controller_select_script_title'), start_dir, "Python Files (*.py)")
        
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
            QtWidgets.QMessageBox.warning(self.ui, tr('controller_warn_name_conflict_title'), tr('controller_warn_name_conflict_body', label=proposed_label, path=proposed_path))
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
        
        cmds.inViewMessage(amg=f"<hl>{tr('controller_info_build_success')}</hl>", pos='midCenter', fade=True)

    def on_file_open(self):
        """處理 '開啟' 動作。"""
        log.debug("處理 '開啟' 動作...")
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, tr('controller_open_config_title'), default_dir, "JSON Files (*.json)")
        
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
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, tr('controller_merge_config_title'), default_dir, "JSON Files (*.json)")

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
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self.ui, tr('controller_save_as_config_title'), default_dir, "JSON Files (*.json)")

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
        [穩定版] 處理「新增/更新」按鈕，並在操作後徹底重設狀態。
        """
        edited_data = self.ui.get_attributes_from_fields()
        if not edited_data.menu_label:
            log.warning("請確保'菜單標籤'欄位不為空。")
            QtWidgets.QMessageBox.warning(self.ui, tr('attribute_editor_group'), tr('controller_warn_label_empty'))
            return
        
        if not edited_data.sub_menu_path:
            log.warning("請確保'菜單路徑'欄位不為空。")
            QtWidgets.QMessageBox.warning(self.ui, tr('attribute_editor_group'), tr('controller_warn_path_empty'))
            return

        item_to_update = self.current_edit_item.data(0, QtCore.Qt.UserRole) if self.current_edit_item else None
        
        if self._is_name_conflict(edited_data.menu_label, edited_data.sub_menu_path, item_to_update):
            return

        self._sync_data_from_ui()

        if self.current_edit_item:
            item_data_to_update = self.current_edit_item.data(0, QtCore.Qt.UserRole)
            log.info(f"更新項目 '{item_data_to_update.menu_label}'...")
            
            item_data_to_update.menu_label = edited_data.menu_label
            item_data_to_update.sub_menu_path = edited_data.sub_menu_path
            item_data_to_update.icon_path = edited_data.icon_path
            item_data_to_update.function_str = edited_data.function_str
            item_data_to_update.command_type = edited_data.command_type
            
            self.current_edit_item = None
            
        else:
            self.current_menu_data.append(edited_data)
            log.info(f"新增菜單項: {edited_data.menu_label}")
        
        self.ui.populate_menu_tree(self.current_menu_data)
        self._refresh_editor_panel()

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
        """
        [增加父物件判斷] 處理刪除操作，能同時刪除父物件與其選項框。
        """
        if not isinstance(item, QtWidgets.QTreeWidgetItem):
            return

        items_to_delete_data = []
        item_data = item.data(0, QtCore.Qt.UserRole)
        
        is_parent_item = False
        option_box_data_to_delete = None
        if item_data and not item_data.is_option_box:
            try:
                current_index = self.current_menu_data.index(item_data)
                if (current_index + 1) < len(self.current_menu_data):
                    item_after = self.current_menu_data[current_index + 1]
                    if item_after.is_option_box:
                        is_parent_item = True
                        option_box_data_to_delete = item_after
            except ValueError:
                pass
        
        is_folder = item.childCount() > 0 and not item_data
        
        confirm_message = ""
        items_to_process_for_delete = []

        if is_folder:
            item_path = self.ui.get_path_for_item(item)
            confirm_message = tr('controller_confirm_delete_folder', path=item_path)
            # 查找所有需要刪除的子項目
            items_to_process_for_delete = [
                data for data in self.current_menu_data 
                if data.sub_menu_path == item_path or data.sub_menu_path.startswith(item_path + '/')
            ]
        else: # 功能項、選項框、父物件
            if is_parent_item:
                confirm_message = tr('controller_confirm_delete_parent_with_option_box', name=item.text(0))
                items_to_process_for_delete.append(item_data)
                if option_box_data_to_delete:
                    items_to_process_for_delete.append(option_box_data_to_delete)
            elif item_data:
                confirm_message = tr('controller_confirm_delete_item', name=item.text(0))
                items_to_process_for_delete.append(item_data)
        
        if not items_to_process_for_delete and not is_folder:
             # 處理刪除一個沒有 item_data 的 QTreeWidgetItem (例如一個空的資料夾)
             # 我們需要從 item_map 中移除它，但 data list 中沒有東西要移除
             pass

        if confirm_message:
            reply = QtWidgets.QMessageBox.question(
                self.ui, tr('controller_confirm_delete_title'), confirm_message,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return

        if items_to_process_for_delete:
            log.info(f"準備刪除 {len(items_to_process_for_delete)} 個項目...")
            self.current_menu_data = [d for d in self.current_menu_data if d not in items_to_process_for_delete]
        
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
            tr('controller_select_custom_icon_title'), 
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
        [增加視覺區隔] 根據 self.current_edit_item 的狀態，刷新右側編輯面板並管理拖曳及可用狀態。
        """
        self.ui.clear_all_highlights()

        if self.current_edit_item:
            # --- 進入編輯模式 ---
            
            # [核心修正] 禁用左側樹狀圖，強化視覺區隔，並禁止拖曳
            self.ui.menu_tree_view.setEnabled(False)
            log.debug("已進入編輯模式，禁用樹狀圖。")

            # 原有的高亮和欄位填充邏輯不變
            self.ui.set_item_highlight(self.current_edit_item, True)
            item_data = self.current_edit_item.data(0, QtCore.Qt.UserRole)
            if not item_data:
                self.current_edit_item = None
                # 在 finally 中會恢復信號，所以這裡可以直接 return
                return

            self.ui.add_update_button.setText(tr('update_finish_editing_button'))
            self.ui.add_update_button.setStyleSheet("background-color: #446688;")
            self.ui.set_attributes_to_fields(item_data)
        else:
            # --- 退出編輯模式 / 處於新增模式 ---

            # [核心修正] 恢復左側樹狀圖的可用狀態
            self.ui.menu_tree_view.setEnabled(True)
            log.debug("已退出編輯模式，恢復樹狀圖。")
            
            self.ui.add_update_button.setText(tr('add_to_structure_button'))
            #highlight_color = QtGui.QColor("#446A3B")
            self.ui.add_update_button.setStyleSheet("")
            self.ui.python_radio.setChecked(True)
            self.ui.label_input.clear()
            self.ui.icon_input.clear()
            self.ui.manual_cmd_input.clear()
            #self.ui.input_tabs.setCurrentIndex(0)

    @preserve_ui_state
    def on_drop_event_completed(self, source_item: QtWidgets.QTreeWidgetItem, 
                                target_item: QtWidgets.QTreeWidgetItem, 
                                indicator: QtWidgets.QAbstractItemView.DropIndicatorPosition):
        """
        [恢復跟隨邏輯] 處理合法的拖放，並確保 Option Box 正確跟隨其父物件。
        """
        log.debug("拖放完成，開始同步資料和狀態...")
        
        source_data = source_item.data(0, QtCore.Qt.UserRole)
        if not source_data:
            return

        # 1. 在同步UI、打亂順序之前，先檢查被拖曳的物件身後是否跟著一個 Option Box。
        option_box_to_follow = self._get_option_box_for_parent(source_data, self.current_menu_data)

        # 2. 執行UI同步。這會將父物件移動到新位置，並在資料層面暫時「拋下」Option Box。
        self._sync_data_from_ui()

        # 3. 如果我們在第一步記住了有 Option Box 需要跟隨，現在就來手動修正它的位置和路徑。
        if option_box_to_follow:
            # 首先，更新它的路徑，使其與父物件的新路徑保持一致
            option_box_to_follow.sub_menu_path = source_data.sub_menu_path
            
            # 然後，在資料列表中，把它從舊的位置移除，再插入到父物件的新位置後面
            self.current_menu_data.remove(option_box_to_follow)
            new_parent_index = self.current_menu_data.index(source_data)
            self.current_menu_data.insert(new_parent_index + 1, option_box_to_follow)
            log.debug(f"已將 Option Box '{option_box_to_follow.menu_label}' 移動到其父物件的新位置。")

        # 4. 用完全修正後的、完美的資料列表，徹底重繪 UI。
        self.ui.populate_menu_tree(self.current_menu_data)
        
        if self.current_edit_item:
            self._refresh_editor_panel()
        
    def on_about(self):
        """
        顯示一個「關於」對話框。
        """
        about_text = f"""
            <b>{tr('about_dialog_main_header')}</b>
            <p>{tr('about_dialog_version')} {__version__}</p>
            <p>{tr('about_dialog_description')}</p>
            <p>{tr('about_dialog_author')} <i>{__author__}</i></p>
            <p>{tr('about_dialog_credits')}</p>
            """
        QtWidgets.QMessageBox.about(
            self.ui,
            tr('about_dialog_title'),
            about_text
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
            cmds.warning(tr('controller_warn_test_run_empty'))
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
                print(code_to_run )
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
                print(code_to_run)
                result = mel.eval(code_to_run)
                success = True

        except Exception as e:
            error_info = f"# Error: {e}"
            success = False

        # --- 格式化最終輸出 ---
        if success:

            print("\n\nExecuted successfully.")
            cmds.inViewMessage(amg=f"<hl>{tr('controller_info_test_run_success')}</hl>", pos='midCenter', fade=True)
        else:
            print("Execution failed!")
            print(error_info)
            # 使用 Maya 的 warning 彈出一個更明顯的錯誤提示
            cmds.warning(f"{tr('controller_warn_test_run_failed')} {error_info}")
        
        print("--- Test Run Finished ---")
        print("="*50 + "\n")
    
    @preserve_ui_state
    def on_context_toggle_option_box(self, item: QtWidgets.QTreeWidgetItem):
        """
        處理來自右鍵選單的「設為/取消選項框」操作。
        """
        if not item: return
        item_data = item.data(0, QtCore.Qt.UserRole)
        if not item_data: return

        # 切換 is_option_box 狀態
        new_state = not item_data.is_option_box
        item_data.is_option_box = new_state
        log.debug(f"項目 '{item_data.menu_label}' 的 is_option_box 狀態由右鍵選單變更為: {new_state}")

        # 刷新UI以顯示變更
        self.ui.populate_menu_tree(self.current_menu_data)

        # 如果程式正處於編輯模式，則刷新編輯器以反映變更
        if self.current_edit_item:
            self._refresh_editor_panel()

    def _is_parent_item(self, parent_candidate: MenuItemData, data_list: list) -> bool:
        """
        輔助函式：檢查一個給定的項目在指定的資料列表中，是否為「父物件」。
        """
        if not parent_candidate or parent_candidate.is_option_box:
            return False
        try:
            current_index = data_list.index(parent_candidate)
            if (current_index + 1) < len(data_list):
                item_after = data_list[current_index + 1]
                return item_after.is_option_box
        except ValueError:
            return False
        return False

    def _get_option_box_for_parent(self, parent_item: MenuItemData, data_list: list) -> MenuItemData :
        """
        輔助函式：如果給定的項目是父物件，則查找並返回其對應的 Option Box 物件。
        """
        try:
            current_index = data_list.index(parent_item)
            if (current_index + 1) < len(data_list):
                item_after = data_list[current_index + 1]
                if item_after.is_option_box:
                    return item_after
        except ValueError:
            return None
        return None
    
    def on_cancel_edit(self):
        """
        處理使用者取消編輯的操作 (例如按下 ESC 鍵)。
        """
        # 只有當前正處於編輯模式時，這個操作才有效
        if self.current_edit_item:
            log.info("使用者取消編輯，正在退出編輯模式...")
            
            # 執行退出編輯模式的標準流程
            self.current_edit_item = None
            self._refresh_editor_panel()