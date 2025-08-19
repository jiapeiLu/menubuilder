# .core.controller.py

"""
Menubuilder - Controller Module

這個模組是 Menubuilder 工具的核心，扮演 MVC 架構中的「控制器(Controller)」角色。

它負責：
- 處理來自 UI (View) 的所有使用者事件（按鈕點擊、列表選擇等）。
- 協調 DataHandler (Model) 進行資料的讀取與儲存。
- 呼叫 MenuGenerator 來在 Maya 中實際生成菜單。
- 管理整個應用程式的狀態和業務邏輯。
"""
import webbrowser
from PySide2 import QtWidgets, QtCore
from maya import cmds, mel
import os
import subprocess
import sys


from .. import __version__, __author__

from .logger import log  # 從我們建立的logger模組導入已經配置好的log實例
from . import setting_reader
from .ui import MenuBuilderUI
from .script_parser import ScriptParser
from .menu_generator import MenuGenerator
from .translator import tr
from .decorators import preserve_ui_state, block_ui_signals

from .handlers.data_handler import DataHandler,MenuItemData
from .handlers.settings_handler import SettingsHandler
from .handlers.tree_interaction_handler import TreeInteractionHandler
from .handlers.editor_panel_handler import EditorPanelHandler
from .handlers.file_io_handler import FileIOHandler

class MenuBuilderController:
    """
    Menubuilder 工具的核心，扮演 MVC 架構中的控制器(Controller)角色。

    作為應用程式的大腦，它持有 View (MenuBuilderUI) 和 Model (DataHandler)
    的實例。它負責將UI發出的信號連接到對應的處理函式(slots)，在這些函式中
    執行所有的業務邏輯、資料處理和流程控制，並在必要時命令UI進行更新。
    """
    def __init__(self):
        """
        [修正初始化順序] 初始化 Controller、所有核心模組以及應用程式的狀態變數。
        """
        log.info("MenuBuilderController 初始化開始...")

        # 1. 先初始化所有非 UI 的核心模組和狀態變數
        self.data_handler = DataHandler()
        self.menu_generator = MenuGenerator()
        self.current_menu_data = []
        self.current_selected_script_path = None
        self.current_config_name = None
        self.current_edit_item = None
        self.insertion_target_item_data = None
        self.is_dirty = False
        self._signals_connected = False
        
        # 2. 創建 UI 實例，並將其賦值給 self.ui
        #    這一步會運行 UI 的 _init_ui，但還不會做任何依賴 Controller 後續狀態的操作
        self.ui = MenuBuilderUI(self)

        # 3. 現在 self.ui 已經存在，我們可以安全地創建所有依賴它的 Handlers
        self.settings_handler = SettingsHandler(self)
        self.tree_handler = TreeInteractionHandler(self)
        self.editor_handler = EditorPanelHandler(self)
        self.file_io_handler = FileIOHandler(self)

        # 5. 在所有元件都已創建並連接好之後，才執行第一次 UI 翻譯和刷新
        self.ui.retranslate_ui()

        # 4. 執行所有後續的初始化步驟
        self._load_initial_data()
        self._connect_signals()
        
        log.info("MenuBuilderController 初始化完成。")


    def _update_path_combobox(self):
        """
        [UX 優化] 掃描當前菜單資料，更新路徑下拉選單的選項。
        [正式版本]
        """
        log.debug("Updating path combobox options...")
        # 使用 set 來自動處理重複的路徑
        existing_paths = set()
        for item_data in self.current_menu_data:
            if item_data.sub_menu_path:
                existing_paths.add(item_data.sub_menu_path)

        # 為了避免觸發不必要的信號，並保持使用者輸入，先阻斷信號
        self.ui.path_input.blockSignals(True)
        current_text = self.ui.path_input.currentText()

        self.ui.path_input.clear()
        # 將路徑排序後加入
        self.ui.path_input.addItems(sorted(list(existing_paths)))

        # 嘗試恢復使用者可能正在輸入的文字
        self.ui.path_input.setCurrentText(current_text)
        self.ui.path_input.blockSignals(False)
        log.debug(f"Path combobox updated with {len(existing_paths)} unique paths.")


    def _refresh_ui_tree_and_paths(self):
        """
        [重構] 一個集中的函式，用於刷新UI樹狀圖和路徑下拉選單。
        """
        self.ui.populate_menu_tree(self.current_menu_data)
        self._update_path_combobox()


    def set_dirty(self, dirty: bool):
        """
        設定檔案的 '髒' 狀態，並更新視窗標題以反映此狀態。
        """
        if self.is_dirty == dirty: # 如果狀態沒變，則不做任何事
            return
            
        self.is_dirty = dirty
        # 通知 UI 更新標題
        self.file_io_handler._update_ui_title()
        log.debug(f"檔案狀態已設為 Dirty: {self.is_dirty}")


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

        self.ui.build_menus_button.clicked.connect(self.on_build_menu_clicked)
        
        self.tree_handler.connect_signals()
        self.editor_handler.connect_signals()
        self.file_io_handler.connect_signals()
        self.settings_handler.connect_signals()

        self.ui.open_config_folder_action.triggered.connect(self.on_open_config_folder)
        self.ui.about_action.triggered.connect(self.on_about)
        self.ui.github_action.triggered.connect(self.on_view_on_github)

        self._signals_connected = True
        log.debug("信號連接完成。")
        
    def _load_initial_data(self):
        """載入設定中指定的預設菜單設定檔。"""
        # 從管理器獲取設定
        default_config = setting_reader.settings_manager.current_setting.get("menuitems")
        self.current_config_name = default_config
        if not default_config:
            log.warning("在 setting.json 中未指定預設的 'menuitems'。")
            return
            
        log.info(f"正在載入預設菜單設定檔: {default_config}.json")
        self.current_menu_data = self.data_handler.load_menu_config(default_config)
        
        if self.current_menu_data:
            # 呼叫新的集中刷新函式
            self._refresh_ui_tree_and_paths()
            self.ui.auto_expand_single_root()
            
        self.file_io_handler._update_ui_title()

    def show_ui(self):
        log.info("顯示 Menubuilder UI。")
        
        try:
            self.ui.center_on_screen()
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
            # [重構] 呼叫新的集中刷新函式
            self._refresh_ui_tree_and_paths()
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

    @block_ui_signals('menu_tree_view')
    def _refresh_editor_panel(self):
        """
        [最終版] 只負責處理「進入」和「退出」編輯模式的 UI 狀態。
        """
        self.ui.clear_all_highlights()
        cancel_button_exists = hasattr(self.ui, 'cancel_edit_button')

        if self.current_edit_item:
            # --- 進入編輯模式 ---
            self.ui.menu_tree_view.setEnabled(False)
            if cancel_button_exists:
                self.ui.cancel_edit_button.setVisible(True)

            self.ui.set_item_highlight(self.current_edit_item, True)
            item_data = self.current_edit_item.data(0, QtCore.Qt.UserRole)
            if not item_data:
                self.current_edit_item = None
                return

            self.ui.add_update_button.setText(tr('update_finish_editing_button'))
            self.ui.add_update_button.setStyleSheet("background-color: #446688;")
            self.ui.set_attributes_to_fields(item_data)
            self.ui.set_editor_fields_enabled(True)
        else:
            # --- 退出編輯模式 ---
            # 退出編輯模式後，UI 狀態應由觸發者（例如 on_cancel_edit 或 on_tree_item_selection_changed）決定
            # 此處只重設與編輯模式直接相關的 UI 元素。
            self.ui.menu_tree_view.setEnabled(True)
            if cancel_button_exists:
                self.ui.cancel_edit_button.setVisible(False)
            
            self.ui.add_update_button.setText(tr('add_to_structure_button'))
            self.ui.add_update_button.setStyleSheet("")    


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
    
    def on_open_config_folder(self):
        """
        [新增] 在系統的檔案總管中開啟 menuitems 設定檔所在的資料夾。
        此方法為跨平台。
        """
        folder_path = self.data_handler.MENUITEMS_DIR
        
        if not folder_path.exists():
            log.error(f"設定檔資料夾不存在: {folder_path}")
            QtWidgets.QMessageBox.warning(self.ui, "Error", f"Folder not found:\n{folder_path}")
            return

        log.info(f"正在開啟資料夾: {folder_path}")
        try:
            if sys.platform == "win32":
                # Windows
                subprocess.run(['explorer', str(folder_path)])
            elif sys.platform == "darwin":
                # macOS
                subprocess.run(['open', str(folder_path)])
            else:
                # Linux
                subprocess.run(['xdg-open', str(folder_path)])
        except Exception as e:
            log.error(f"無法開啟資料夾: {e}")
            QtWidgets.QMessageBox.critical(self.ui, "Error", f"Could not open the folder:\n{e}")
