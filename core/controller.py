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
from .logger import log  # 從我們建立的logger模組導入已經配置好的log實例
#phase1 新增
from .setting_reader import current_setting
from .ui import MenuBuilderUI, IconBrowserDialog
from .data_handler import DataHandler
#phase2 新增
from .script_parser import ScriptParser
from PySide2 import QtWidgets, QtCore
#phase3 新增
from .menu_generator import MenuGenerator # 導入 MenuGenerator
import maya.cmds as cmds
import os
from pathlib import Path

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
    @functools.wraps(func)  # 這可以保持原函式的名稱、文檔等元數據
    def wrapper(self, *args, **kwargs):
        # 參數中的 'self' 就是 MenuBuilderController 的實例
        if not hasattr(self, 'ui'):
            # 安全檢查，確保ui物件存在
            return func(self, *args, **kwargs)

        # 1. 記錄 -> 執行前的 "Setup"
        expansion_state = self.ui.get_expansion_state()
        log.debug(f"裝飾器: 狀態已記錄。準備執行 '{func.__name__}'...")

        # 使用 try...finally 來確保即使函式出錯，還原步驟依然會執行
        try:
            # 2. 操作 -> 執行原始函式 (例如 on_delete_item_clicked)
            result = func(self, *args, **kwargs)
        finally:
            # 4. 還原 -> 執行後的 "Teardown"
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
        self.menu_generator = MenuGenerator() # 實例化 MenuGenerator
        self.ui = MenuBuilderUI(self)
        self.current_menu_data = [] # 用來儲存當前編輯的菜單資料
        self.current_selected_script_path = None # 用於儲存當前腳本的路徑
        self.current_config_name = None # 用於儲存當前設定檔名稱
        self.current_edit_item = None # 用於追蹤當前正在編輯的項目
        self._signals_connected = False # 初始化信號連接旗標 AI 強烈建議加上避免重覆C++底層重覆呼叫?
        self._load_initial_data()
        self._connect_signals()
        log.info("MenuBuilderController 初始化完成。")

    def _connect_signals(self):
        """
        集中管理所有 UI 元件的信號與槽(slots)的連接。
        
        使用 `_signals_connected` 旗標來確保這個連接過程在程式的生命週期中
        只會被執行一次，以避免因模組重載(reload)導致的信號重複連接問題。
        """
        # [核心修改] 只有在尚未連接過信號時，才執行連接操作
        if self._signals_connected:
            log.debug("信號已經連接過，跳過。")
            return
        log.debug("正在進行初次信號連接...")
        self.ui.browse_button.clicked.connect(self.on_browse_script_clicked)
        self.ui.function_list.currentItemChanged.connect(self.on_function_selected)
        self.ui.icon_buildin_btn.clicked.connect(self.on_browse_icon_clicked)
        self.ui.icon_browse_btn.clicked.connect(self.on_browse_custom_icon_clicked) #[新增] 連接圖示瀏覽按鈕的點擊信號
        self.ui.add_update_button.clicked.connect(self.on_add_item_clicked)
        self.ui.delete_button.clicked.connect(self.on_delete_item_clicked)
        self.ui.build_menus_button.clicked.connect(self.on_build_menu_clicked)
        self.ui.menu_tree_view.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.ui.menu_tree_view.customContextMenuRequested.connect(self.ui.on_tree_context_menu)
        self.ui.menu_tree_view.itemChanged.connect(self.on_tree_item_renamed) # 連接項目變更(編輯完成)的信號
        # [修改] 連接到新的自訂信號
        self.ui.menu_tree_view.drop_event_completed.connect(self.on_drop_event_completed)


        #self.ui.dockable_checkbox.stateChanged.connect(self.on_dockable_checkbox_changed)
        # 連接檔案菜單的動作
        self.ui.open_action.triggered.connect(self.on_file_open)
        self.ui.merge_action.triggered.connect(self.on_file_merge)
        self.ui.save_action.triggered.connect(self.on_save_config_clicked)
        self.ui.save_as_action.triggered.connect(self.on_file_save_as)
        self.ui.exit_action.triggered.connect(self.ui.close) # 直接連接到視窗的關閉方法
        # [新增] 連接 OptionBox 核取方塊的狀態變化信號
        self.ui.option_box_checkbox.stateChanged.connect(self.on_option_box_changed)


        # 在所有連接完成後，將旗標設為 True
        self._signals_connected = True
        log.debug("信號連接完成。")
        
    def _load_initial_data(self):
        """載入設定中指定的預設菜單設定檔。"""
        default_config = current_setting.get("menuitems")
        self.current_config_name = default_config # [新增] 記錄檔名
        if not default_config:
            log.warning("在 setting.json 中未指定預設的 'menuitems'。")
            return
            
        log.info(f"正在載入預設菜單設定檔: {default_config}.json")
        
        # 載入資料並存入 self.current_menu_data
        self.current_menu_data = self.data_handler.load_menu_config(default_config)
        
        # 如果成功載入資料，則刷新UI
        if self.current_menu_data:
            self.ui.populate_menu_tree(self.current_menu_data)
        self._update_ui_title() # 更新UI標題

    def show_ui(self):
        log.info("顯示 Menubuilder UI。")
        try:
            self.ui.show()
        except Exception as e:
            log.error(f"顯示UI時發生錯誤: {e}", exc_info=True) # exc_info=True 會記錄完整的錯誤堆疊

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
        
        # --- 1. 獲取必要的資訊 ---
        # 函式名稱 (e.g., "findKeyRange")
        func_name = current.text()
        
        # 從完整路徑中提取不含副檔名的模組名 (e.g., "autoTimeRange")
        module_name = os.path.basename(self.current_selected_script_path).replace('.py', '')

        # --- 2. 生成指令和標籤 ---
        # 生成標籤 (e.g., "Find Key Range")
        generated_label = ScriptParser.generate_label_from_string(func_name)
        
        # 生成可執行的完整指令
        # 使用 importlib.reload() 是更現代、更推薦的做法
        # 這裡用 reload() 是為了簡化，但在Python 3中，它其實是 importlib.reload
        command_to_run = (
            f"import {module_name}\n"
            f"from importlib import reload\n"
            f"reload({module_name})\n"
            f"{module_name}.{func_name}()"
        )
        
        # --- 3. 更新 UI ---
        # 更新標籤輸入框
        self.ui.label_input.setText(generated_label)
        
        # 切換到「手動輸入指令」分頁 (索引值為 1)
        self.ui.input_tabs.setCurrentIndex(1)
        
        # 將生成的指令填入文字框
        self.ui.manual_cmd_input.setText(command_to_run)
        
        log.debug(f"已生成指令並填入UI: {command_to_run}")

    @preserve_ui_state
    def on_delete_item_clicked(self):
        """[優化後] 刪除左側樹狀視圖中當前選擇的項目。"""
        selected_items = self.ui.menu_tree_view.selectedItems()
        if not selected_items:
            log.warning("請先在左側列表中選擇要刪除的項目。")
            return
            
        # 從UI項目中直接獲取關聯的 MenuItemData 物件
        item_to_remove_data = selected_items[0].data(0, QtCore.Qt.UserRole)
        
        if item_to_remove_data:
            # 從 self.current_menu_data 中找到並移除同一個物件實例
            self.current_menu_data.remove(item_to_remove_data)
            log.info(f"已刪除菜單項: {item_to_remove_data.menu_label}")
            self.ui.populate_menu_tree(self.current_menu_data)
        else:
            log.warning("無法刪除，所選項目是一個文件夾或沒有關聯資料。請使用右鍵選單刪除文件夾。")

        #[新增] 同步資料
    
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
        
        # [核心] 更新 self.current_menu_data 和每個項目的 order
        # 我們不僅要更新列表，還要更新每個item的order值，以便儲存
        final_data_list = []
        for i, item_data in enumerate(ordered_data_from_ui):
            item_data.order = (i + 1) * 10 # 重新計算 order 值
            final_data_list.append(item_data)
        
        self.current_menu_data = final_data_list
        log.debug("資料同步完成。")

    def on_save_config_clicked(self):
        """儲存當前的菜單結構到檔案。"""
        # 1. 先從UI同步最新的順序和結構
        self._sync_data_from_ui()
        
        # 2. 再使用更新後的資料進行儲存
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
        
        # 0. 先從UI同步最新的順序和結構
        self._sync_data_from_ui()
        log.info("開始生成/刷新 Maya 菜單...")
        
        # 1. 清除舊菜單
        self.menu_generator.clear_existing_menus()
        
        # 2. 用當前編輯的資料建立新菜單
        self.menu_generator.build_from_config(self.current_menu_data)
        
        # 3. 給予使用者反饋
        cmds.inViewMessage(amg='<hl>菜單已成功生成/刷新！</hl>', pos='midCenter', fade=True)

    def on_file_open(self):
        """處理 '開啟' 動作。"""
        log.debug("處理 '開啟' 動作...")
        # 從 data_handler 取得預設的 menuitems 資料夾路徑
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, "開啟菜單設定檔", default_dir, "JSON Files (*.json)")
        
        if not file_path:
            log.debug("使用者取消了檔案選擇。")
            return
        
        # 從完整路徑中提取不含副檔名的檔名
        config_name = Path(file_path).stem
        self.current_config_name = config_name # 記錄檔名

        # 載入新資料並完全覆蓋現有資料
        new_data = self.data_handler.load_menu_config(config_name)
        self.current_menu_data = new_data
        
        # 刷新UI
        self.ui.populate_menu_tree(self.current_menu_data)
        self._update_ui_title() # 更新UI標題
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
            # [核心] 將新資料附加到現有資料列表的末尾
            self.current_menu_data.extend(new_data)
            # 刷新UI
            self.ui.populate_menu_tree(self.current_menu_data)
            log.info(f"已成功將 {file_path} 的內容合併至當前設定。")

    def on_file_save_as(self):
        """處理 '另存為' 動作。"""
        log.debug("處理 '另存為' 動作...")
        default_dir = str(self.data_handler.MENUITEMS_DIR)
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self.ui, "另存為菜單設定檔", default_dir, "JSON Files (*.json)")

        if not file_path:
            return
            
        # [重要] 在儲存前，先從UI同步最新的順序和結構
        self._sync_data_from_ui()

        config_name = Path(file_path).stem
        self.current_config_name = config_name # [新增] 記錄檔名
        self.data_handler.save_menu_config(config_name, self.current_menu_data)
        self._update_ui_title() # [新增] 更新UI標題
        log.info(f"已將當前設定另存為: {file_path}")

    def on_tree_item_double_clicked(self, item, column):
        """
        當樹狀列表中的項目被雙擊時觸發，讓工具進入「編輯模式」。

        Args:
            item (QtWidgets.QTreeWidgetItem): 被雙擊的UI項目。
            column (int): 被雙擊的欄位索引。
        """
        item_data = item.data(0, QtCore.Qt.UserRole)
        if not item_data:
            log.debug("雙擊的是一個文件夾，無操作。")
            self.current_edit_item = None
        else:
            log.info(f"正在編輯項目: {item_data.menu_label}")
            self.current_edit_item = item
        
        # 統一呼叫刷新函式
        self._refresh_editor_panel()

    @preserve_ui_state
    def on_add_item_clicked(self):
        """
        處理「新增/更新」按鈕的點擊事件。

        此函式具有雙重職責：
        - 如果 `self.current_edit_item` 有值 (處於編輯模式)，則將
          UI 面板的內容更新到該資料物件上。
        - 如果為 `None` (處於新增模式)，則創建一個新的資料物件並附加到列表中。
        
        操作完成後，會刷新UI樹並退出編輯模式。
        """
        edited_data = self.ui.get_attributes_from_fields()
        if not edited_data.menu_label or not edited_data.function_str:
            log.warning("請確保'菜單標籤'和'指令'欄位不為空。")
            return

        # 先從UI同步最新的資料狀態
        self._sync_data_from_ui()

        if self.current_edit_item:
            # --- 執行更新邏輯 ---
            item_data_to_update = self.current_edit_item.data(0, QtCore.Qt.UserRole)
            log.info(f"更新項目 '{item_data_to_update.menu_label}'...")
            # 直接修改記憶體中原有的 MenuItemData 物件的屬性
            # 因為 item_data 是 class 物件，這裡是引用，所以修改會生效
            item_data_to_update.menu_label = edited_data.menu_label
            item_data_to_update.sub_menu_path = edited_data.sub_menu_path
            item_data_to_update.order = edited_data.order
            item_data_to_update.icon_path = edited_data.icon_path
            item_data_to_update.is_option_box = edited_data.is_option_box
            item_data_to_update.function_str = edited_data.function_str
            
            # 清除編輯狀態
            self.current_edit_item = None
            self._refresh_editor_panel() # 這會清除高亮和還原按鈕文字

        else:
            # --- 執行新增邏輯 ---
            self.current_menu_data.append(edited_data)
            log.info(f"新增菜單項: {edited_data.menu_label}")
        
        # 最後，無論是新增還是更新，都用更新後的 self.current_menu_data 刷新整個UI樹
        self.ui.populate_menu_tree(self.current_menu_data)

    def on_context_send_path(self, path: str):
        """接收來自右鍵選單的路徑，並更新到UI輸入框中。"""
        log.debug(f"從右鍵選單接收到路徑: {path}")
        self.ui.path_input.setText(path)

    def on_context_add_under(self, parent_path: str):
        """在指定的父路徑下準備新增一個項目。"""
        log.debug(f"準備在 '{parent_path}' 下新增項目。")
        
        # 1. 準備編輯器欄位
        self.ui.path_input.setText(parent_path)
        self.ui.label_input.clear()
        self.ui.manual_cmd_input.clear()
        
        # 2. 進入「新增模式」
        self.current_edit_item = None
        
        # 3. [新增] 呼叫統一的刷新函式來更新UI狀態 (包括禁用 isOptionBox)
        self._refresh_editor_panel()

        self.ui.label_input.setFocus()

    @preserve_ui_state
    def on_context_delete(self, item: QtWidgets.QTreeWidgetItem):
        """[修正後] 處理刪除操作，可能是單一項目或整個文件夾。"""
        # 安全檢查，確保傳入的是正確的物件類型
        if not isinstance(item, QtWidgets.QTreeWidgetItem):
            log.error(f"刪除操作收到了錯誤的物件類型: {type(item)}")
            return

        item_path = self.ui.get_path_for_item(item)
        item_data = item.data(0, QtCore.Qt.UserRole)
        
        items_to_delete = []
        
        # 先從UI同步一次資料，確保 self.current_menu_data 是最新的
        self._sync_data_from_ui()

        # 判斷是文件夾還是單一項目
        is_folder = item.childCount() > 0 or not item_data

        if is_folder:
            # --- 刪除整個文件夾 ---
            reply = QtWidgets.QMessageBox.question(
                self.ui, '確認刪除', 
                f"您確定要刪除 '{item_path}' 及其下的所有內容嗎？\n此操作無法復原。",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return
            
            # 找出所有路徑符合的項目
            items_to_delete = [
                data for data in self.current_menu_data 
                if data.sub_menu_path == item_path or data.sub_menu_path.startswith(item_path + '/')
            ]
            if item_data and item_data not in items_to_delete:
                items_to_delete.append(item_data)
        else:
            # --- 刪除單一項目 ---
            if item_data:
                items_to_delete.append(item_data)
        
        if items_to_delete:
            log.info(f"準備刪除 {len(items_to_delete)} 個項目...")
            self.current_menu_data = [d for d in self.current_menu_data if d not in items_to_delete]
            self.ui.populate_menu_tree(self.current_menu_data)
    
    
    def on_tree_item_renamed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        """
        [最終版] 當項目文字被編輯後觸發，並完美保持自身及其後代的展開狀態。
        """
        if self.ui.menu_tree_view.signalsBlocked():
            return

        # 1. 獲取新舊名稱和路徑
        new_name = item.text(0)
        old_path = None
        for path, ui_item in self.ui.item_map.items():
            if ui_item == item:
                old_path = path
                break
        
        if old_path is None: # 安全檢查
            self._sync_data_from_ui()
            self.ui.populate_menu_tree(self.current_menu_data)
            return

        old_name = old_path.split('/')[-1]
        if new_name == old_name: return

        parent_path = "/".join(old_path.split('/')[:-1])
        new_path = f"{parent_path}/{new_name}" if parent_path else new_name

        # 2. 記錄原始的展開狀態
        expansion_state_before = self.ui.get_expansion_state()

        # 3. [核心修正] 創建新的展開狀態集合
        new_expansion_state = set()
        for path in expansion_state_before:
            # 檢查路徑是否正好是被重命名的路徑，或者是它的子路徑
            if path == old_path or path.startswith(old_path + '/'):
                corrected_path = path.replace(old_path, new_path, 1)
                new_expansion_state.add(corrected_path)
            else:
                new_expansion_state.add(path)
        
        # 4. 執行同步和UI刷新
        self._sync_data_from_ui()
        self.ui.menu_tree_view.blockSignals(True)
        self.ui.populate_menu_tree(self.current_menu_data)
        
        # 5. 使用新的展開狀態來還原UI
        self.ui.set_expansion_state(new_expansion_state)
        
        self.ui.menu_tree_view.blockSignals(False)
        log.info("項目重命名完成，已恢復展開狀態。")
            
    def on_browse_icon_clicked(self):
        """當'瀏覽圖示'按鈕被點擊時，創建並顯示圖示瀏覽器。"""
        log.debug("開啟圖示瀏覽器...")
        # 將主UI視窗 (self.ui) 作為父級傳遞給對話框
        icon_browser = IconBrowserDialog(self.ui)
        
        # [核心] 連接對話框的自訂信號到Controller的處理函式上
        icon_browser.icon_selected.connect(self.on_icon_selected_from_browser)
        
        # 以非阻塞模式執行對話框
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
            # 將選擇的檔案路徑設定到輸入框中
            # textChanged 信號會自動觸發預覽更新
            self.ui.icon_input.setText(file_path)
            log.info(f"選擇了自訂圖示: {file_path}")

    def on_icon_selected_from_browser(self, icon_path: str):
        """當圖示瀏覽器發出'icon_selected'信號時，接收圖示路徑並更新UI。"""
        log.debug(f"接收到選擇的圖示路徑: {icon_path}")
        self.ui.icon_input.setText(icon_path)
    
    def _update_ui_title(self):
        """一個新的輔助函式，用來通知UI更新標題。"""
        self.ui.update_tree_view_title(self.current_config_name)

    def _refresh_editor_panel(self):
        """
        [修正後] 根據 self.current_edit_item 的狀態，刷新右側編輯面板。
        """
        # 先清除所有舊的高亮
        self.ui.clear_all_highlights()

        if self.current_edit_item:
            # --- 編輯模式 ---
            # 從 item 中獲取 data
            item_data = self.current_edit_item.data(0, QtCore.Qt.UserRole)
            
            # 高亮當前編輯的項目
            self.ui.set_item_highlight(self.current_edit_item, True)
            
            self.ui.set_attributes_to_fields(item_data)
            self.ui.add_update_button.setText("更新項目 (Update)")
            self.ui.option_box_checkbox.setEnabled(True)
        else:
            # --- 新增模式 ---
            self.ui.add_update_button.setText("新增至結構")
            self.ui.option_box_checkbox.setEnabled(False)
            self.ui.option_box_checkbox.setChecked(False)

    def _apply_option_box_change(self, item_data_to_change, should_be_option_box):
        """
        [新增] 一個統一的、權威的函式，用來處理 is_option_box 狀態的變更。
        """
        if item_data_to_change.is_option_box != should_be_option_box:
            log.debug(f"'{item_data_to_change.menu_label}' 的 is_option_box 狀態變更為: {should_be_option_box}")
            item_data_to_change.is_option_box = should_be_option_box
        
        # 狀態變更後，總是同步並刷新UI
        self._sync_data_from_ui()
        self.ui.populate_menu_tree(self.current_menu_data)
        # 刷新右側面板
        self._refresh_editor_panel()

    @preserve_ui_state
    def on_option_box_changed(self, state):
        """[最終版] 當'作為選項框'核取方塊的狀態改變時觸發，並執行最完整的驗證。"""
        if state > 0: # 嘗試勾選
            if not self.current_edit_item:
                QtWidgets.QMessageBox.warning(self.ui, "操作無效", "請先從左側雙擊一個項目以進入編輯模式。")
                self.ui.option_box_checkbox.setChecked(False)
                return

            # --- [核心修正] 執行更嚴謹的父級驗證 ---
            
            # 1. 根據正在編輯的資料，反向找到它在UI中的QTreeWidgetItem
            current_ui_item = None
            item_path = f"{self.current_edit_item.sub_menu_path}/{self.current_edit_item.menu_label}" if self.current_edit_item.sub_menu_path else self.current_edit_item.menu_label
            if item_path in self.ui.item_map:
                current_ui_item = self.ui.item_map[item_path]

            if not current_ui_item:
                log.error("無法在UI樹中找到對應的編輯項目。")
                self.ui.option_box_checkbox.setChecked(False)
                return

            # 2. 找到在它視覺正上方的項目
            item_above = self.ui.menu_tree_view.itemAbove(current_ui_item)

            # 3. 執行新的驗證規則
            error_message = ""
            if not item_above:
                # 規則1 (部分情況): 如果 itemAbove 不存在，代表它可能是根目錄的第一個項目
                error_message = "項目不能作為其所在層級的第一個選項框。"
            elif current_ui_item.parent() != item_above.parent():
                 # 規則1 (另一種情況): 如果父級不同，也代表它是新群組的第一個
                error_message = "項目不能作為其所在層級的第一個選項框。"
            else:
                parent_candidate_data = item_above.data(0, QtCore.Qt.UserRole)
                if not parent_candidate_data:
                    # 上方是個文件夾，不是功能項
                    error_message = "一個項目要成為選項框，它的正上方必須是一個有效的功能菜單項。"
                elif parent_candidate_data.is_option_box:
                    # 規則2: 上方項目已經是選項框
                    error_message = "一個項目不能成為另一個選項框的選項框。"

            # 4. 根據驗證結果執行操作
            if not error_message:
                # 驗證通過
                log.debug(f"項目 '{self.current_edit_item.menu_label}' 將成為選項框。")
                self.current_edit_item.is_option_box = True
                self.ui.populate_menu_tree(self.current_menu_data)
                return
            else:
                # 驗證失敗
                QtWidgets.QMessageBox.warning(self.ui, "操作無效", error_message)
                self.ui.option_box_checkbox.setChecked(False)
        
        else: # 取消勾選
            if self.current_edit_item:
                self.current_edit_item.is_option_box = False
                self.ui.populate_menu_tree(self.current_menu_data)

    @preserve_ui_state
    def on_drop_event_completed(self, source_item: QtWidgets.QTreeWidgetItem, 
                                target_item: QtWidgets.QTreeWidgetItem, 
                                indicator: QtWidgets.QAbstractItemView.DropIndicatorPosition):
        """
        [最終版] 在拖放操作完成後，執行唯一的、權威的資料同步和狀態修正。
        能精確區分「重新父級」和「成為選項框」兩種意圖。
        """
        log.debug("拖放完成，開始同步資料和狀態...")
        
        # --- [核心] 在操作前，阻斷信號，防止Bug ---
        self.ui.option_box_checkbox.blockSignals(True)
        
        try:
            # 1. 從視覺上已經改變的UI，掃描出最新的結構和順序
            # 這是我們資料的最新基礎，它反映了Qt執行的視覺移動
            self._sync_data_from_ui()
            
            # 2. 獲取被拖曳項目的資料
            source_data = source_item.data(0, QtCore.Qt.UserRole)
            if not source_data: # 如果拖的是文件夾，同步完即可，無需後續處理
                self.ui.populate_menu_tree(self.current_menu_data)
                return

            # 3. [核心邏輯] 根據拖放的「意圖」來修正資料
            should_be_option_box = False
            
            # 只有當明確地拖放到一個功能項「之上」(OnItem)時，才視為想設為選項框
            if indicator == QtWidgets.QAbstractItemView.OnItem and target_item:
                target_data = target_item.data(0, QtCore.Qt.UserRole)
                # 目標必須是一個「功能項」，且其自身不能是選項框
                if target_data and not target_data.is_option_box:
                    should_be_option_box = True
                    
                    # [關鍵修正] 如果要成為選項框，它的sub_menu_path
                    # 應該與它的新「兄弟」(也就是目標)相同，而不是成為其子級。
                    # 我們從同步後的資料中，強制修正它的路徑。
                    log.debug(f"意圖：成為選項框。將 '{source_data.menu_label}' 的路徑修正為 '{target_data.sub_menu_path}'")
                    source_data.sub_menu_path = target_data.sub_menu_path

            # 4. 更新資料
            if source_data.is_option_box != should_be_option_box:
                 log.info(f"'{source_data.menu_label}' 的 is_option_box 狀態更新為: {should_be_option_box}")
                 source_data.is_option_box = should_be_option_box
            
            # 5. 用經過二次修正的、100%正確的資料，再次完整刷新UI
            self.ui.populate_menu_tree(self.current_menu_data)
            
            # 6. 刷新右側編輯面板，確保同步
            self._refresh_editor_panel()
            
        finally:
            self.ui.option_box_checkbox.blockSignals(False)