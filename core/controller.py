# core/controller.py
import functools # 導入 functools 以便使用 wraps
from .logger import log  # 從我們建立的logger模組導入已經配置好的log實例
#phase1 新增
from .setting_reader import current_setting
from .ui import MenuBuilderUI
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
    一個裝飾器，用於在執行函式前後自動保存和還原UI的狀態。
    它會處理樹狀視圖的展開狀態。
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
    def __init__(self):
        log.info("MenuBuilderController 初始化開始...")
        self.data_handler = DataHandler()
        self.menu_generator = MenuGenerator() # 實例化 MenuGenerator
        self.ui = MenuBuilderUI(self)
        self.current_menu_data = [] # 重要：用來儲存當前編輯的菜單資料
        self.current_selected_script_path = None # <-- 用於儲存當前腳本的路徑
        self.current_edit_item_data = None # [新增] 用於追蹤當前正在編輯的項目
        self._signals_connected = False # [新增] 初始化信號連接旗標 AI 強烈建議加上避免重覆C++底層重覆呼叫?
        self._load_initial_data()
        self._connect_signals()
        log.info("MenuBuilderController 初始化完成。")

    def _connect_signals(self):
        """集中管理所有UI信號的連接。
        使用旗標確保這個函式只會被成功執行一次。
        """
        # [核心修改] 只有在尚未連接過信號時，才執行連接操作
        if self._signals_connected:
            log.debug("信號已經連接過，跳過。")
            return
        log.debug("正在進行初次信號連接...")
        self.ui.browse_button.clicked.connect(self.on_browse_script_clicked)
        self.ui.function_list.currentItemChanged.connect(self.on_function_selected)
        self.ui.add_update_button.clicked.connect(self.on_add_item_clicked)
        self.ui.delete_button.clicked.connect(self.on_delete_item_clicked)
        self.ui.build_menus_button.clicked.connect(self.on_build_menu_clicked)
        self.ui.menu_tree_view.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.ui.menu_tree_view.customContextMenuRequested.connect(self.ui.on_tree_context_menu)
        self.ui.menu_tree_view.itemChanged.connect(self.on_tree_item_renamed) # [新增] 連接項目變更(編輯完成)的信號
        
        # [新增] 連接檔案菜單的動作
        self.ui.open_action.triggered.connect(self.on_file_open)
        self.ui.merge_action.triggered.connect(self.on_file_merge)
        self.ui.save_action.triggered.connect(self.on_save_config_clicked)
        self.ui.save_as_action.triggered.connect(self.on_file_save_as)
        self.ui.exit_action.triggered.connect(self.ui.close) # 直接連接到視窗的關閉方法

        # [新增] 在所有連接完成後，將旗標設為 True
        self._signals_connected = True
        log.debug("信號連接完成。")
        
    def _load_initial_data(self):
        """載入設定中指定的預設菜單設定檔。"""
        default_config = current_setting.get("menuitems")
        if not default_config:
            log.warning("在 setting.json 中未指定預設的 'menuitems'。")
            return
            
        log.info(f"正在載入預設菜單設定檔: {default_config}.json")
        
        # 載入資料並存入 self.current_menu_data
        self.current_menu_data = self.data_handler.load_menu_config(default_config)
        
        # 如果成功載入資料，則刷新UI
        if self.current_menu_data:
            self.ui.populate_menu_tree(self.current_menu_data)

    def show_ui(self):
        log.info("顯示 Menubuilder UI。")
        try:
            self.ui.show()
        except Exception as e:
            log.error(f"顯示UI時發生錯誤: {e}", exc_info=True) # exc_info=True 會記錄完整的錯誤堆疊

    def on_browse_script_clicked(self):
        """當瀏覽按鈕被點擊時觸發。"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, "選擇 Python 腳本", "", "Python Files (*.py)")
        if not file_path:
            self.current_selected_script_path = None # <-- [新增] 如果取消選擇，則清空路徑
            return
            
        self.current_selected_script_path = file_path # <-- [新增] 儲存選擇的路徑
            
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

    @preserve_ui_state # <-- 應用裝飾器
    def on_add_item_clicked(self):
        """將右側編輯器的內容轉換為一個新的菜單項並加入。"""
        # 1. 從UI收集資料
        # (需要先在ui.py中實現 get_attributes_from_fields 方法)
        new_item_data = self.ui.get_attributes_from_fields() 
        
        # 2. 加入到記憶體的列表中
        self.current_menu_data.append(new_item_data)
        log.info(f"新增菜單項: {new_item_data.menu_label}")
        
        # 3. 刷新UI
        self.ui.populate_menu_tree(self.current_menu_data)

    @preserve_ui_state # <-- 應用裝飾器
    def on_delete_item_clicked(self):
        """刪除左側樹狀視圖中當前選擇的項目。"""
        # (這部分邏輯較複雜，需要先在UI中確定如何識別被選中的項目)
        # (一個簡單的實現是基於 label 和 path 來查找並刪除)
        selected_items = self.ui.menu_tree_view.selectedItems()
        if not selected_items:
            log.warning("請先在左側列表中選擇要刪除的項目。")
            return
            
        # 這裡只處理單選刪除
        selected_label = selected_items[0].text(0)
        
        # 從 self.current_menu_data 中找到並移除對應的項目
        item_to_remove = None
        for item in self.current_menu_data:
            if item.menu_label == selected_label: # 這裡的匹配邏輯可以做得更精確
                item_to_remove = item
                break
                
        if item_to_remove:
            self.current_menu_data.remove(item_to_remove)
            log.info(f"已刪除菜單項: {item_to_remove.menu_label}")
            self.ui.populate_menu_tree(self.current_menu_data)

        #[新增] 同步資料
    def _sync_data_from_ui(self):
        """核心同步函式：從UI掃描最新狀態，並更新記憶體中的資料列表。"""
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
        """當'生成/刷新菜單'按鈕被點擊時觸發。"""
        
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
        
        # 載入新資料並完全覆蓋現有資料
        new_data = self.data_handler.load_menu_config(config_name)
        self.current_menu_data = new_data
        
        # 刷新UI
        self.ui.populate_menu_tree(self.current_menu_data)
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
        # 使用更新後的資料進行儲存
        self.data_handler.save_menu_config(config_name, self.current_menu_data)
        log.info(f"已將當前設定另存為: {file_path}")

    # [新增] 雙擊事件的處理函式
    def on_tree_item_double_clicked(self, item, column):
        """當樹狀列表中的項目被雙擊時觸發。"""
        item_data = item.data(0, QtCore.Qt.UserRole)
        if not item_data:
            log.debug("雙擊的是一個文件夾，可編輯名稱。")
            self.current_edit_item_data = None # 清空編輯目標
            self.ui.add_update_button.setText("新增至結構") # 按鈕文字還原
            return
        
        log.info(f"正在編輯項目: {item_data.menu_label}")
        # 1. 記錄當前正在編輯的項目
        self.current_edit_item_data = item_data
        
        # 2. 呼叫UI方法，將資料填入右側面板
        self.ui.set_attributes_to_fields(item_data)
        
        # 3. [UX優化] 將按鈕文字從「新增」改為「更新」
        self.ui.add_update_button.setText("更新項目 (Update)")

    # [修改] on_add_item_clicked 方法，使其能處理更新邏輯
    @preserve_ui_state
    def on_add_item_clicked(self):
        """
        處理'新增/更新'按鈕的點擊事件。
        如果當前有正在編輯的項目，則執行更新；否則執行新增。
        """
        # 從UI面板獲取當前所有欄位的資料
        edited_data = self.ui.get_attributes_from_fields()
        if not edited_data.menu_label or not edited_data.function_str:
            log.warning("請確保'菜單標籤'和'指令'欄位不為空。")
            return

        if self.current_edit_item_data:
            # --- 執行更新邏輯 ---
            log.info(f"更新項目 '{self.current_edit_item_data.menu_label}'...")
            # 直接修改記憶體中原有的 MenuItemData 物件的屬性
            self.current_edit_item_data.menu_label = edited_data.menu_label
            self.current_edit_item_data.sub_menu_path = edited_data.sub_menu_path
            self.current_edit_item_data.order = edited_data.order
            self.current_edit_item_data.icon_path = edited_data.icon_path
            self.current_edit_item_data.is_dockable = edited_data.is_dockable
            self.current_edit_item_data.is_option_box = edited_data.is_option_box
            self.current_edit_item_data.function_str = edited_data.function_str
            
            # 清除編輯狀態並還原按鈕文字
            self.current_edit_item_data = None
            self.ui.add_update_button.setText("新增至結構")
        else:
            # --- 執行新增邏輯 ---
            self.current_menu_data.append(edited_data)
            log.info(f"新增菜單項: {edited_data.menu_label}")
        
        # 最後，無論是新增還是更新，都刷新整個UI樹
        self.ui.populate_menu_tree(self.current_menu_data)

    def on_context_send_path(self, path: str):
        """接收來自右鍵選單的路徑，並更新到UI輸入框中。"""
        log.debug(f"從右鍵選單接收到路徑: {path}")
        self.ui.path_input.setText(path)
        # 順便清空標籤和指令，準備新增
        self.ui.label_input.clear()
        self.ui.manual_cmd_input.clear()
        self.current_edit_item_data = None
        self.ui.add_update_button.setText("新增至結構")


    def on_context_add_under(self, parent_path: str):
        """在指定的父路徑下準備新增一個項目。"""
        log.debug(f"準備在 '{parent_path}' 下新增項目。")
        self.on_context_send_path(parent_path) # 直接復用上面的函式來清空和設定路徑
        self.ui.label_input.setFocus() # 將游標焦點設在標籤輸入框，方便使用者輸入

    @preserve_ui_state
    def on_context_delete(self, item: QtWidgets.QTreeWidgetItem):
        """處理刪除操作，可能是單一項目或整個文件夾。"""
        item_data = item.data(0, QtCore.Qt.UserRole)
        item_path = self.ui.get_path_for_item(item)
        
        items_to_delete = []
        
        # 先同步一次資料，確保 self.current_menu_data 是最新的
        self._sync_data_from_ui()

        if item.childCount() > 0:
            # --- 刪除整個文件夾 ---
            reply = QtWidgets.QMessageBox.question(
                self.ui, '確認刪除', 
                f"您確定要刪除 '{item_path}' 及其下的所有內容嗎？\n此操作無法復原。",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, 
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                return # 使用者取消操作
            
            # 找出所有路徑符合的項目 (包括自身和所有子項目)
            items_to_delete = [
                data for data in self.current_menu_data 
                if data.sub_menu_path == item_path or data.sub_menu_path.startswith(item_path + '/')
            ]
            # 如果點擊的文件夾本身是一個功能項，也把它加進去
            if item_data and item_data not in items_to_delete:
                items_to_delete.append(item_data)
        else:
            # --- 刪除單一項目 ---
            if item_data:
                items_to_delete.append(item_data)
        
        if items_to_delete:
            log.info(f"準備刪除 {len(items_to_delete)} 個項目...")
            # 從主資料列表中移除這些項目
            self.current_menu_data = [d for d in self.current_menu_data if d not in items_to_delete]
            self.ui.populate_menu_tree(self.current_menu_data)
    
    
    def on_tree_item_renamed(self, item, column):
        """當樹狀視圖中的項目文字被使用者編輯後觸發。"""
        # 為了防止在我們自己刷新UI時觸發無限循環，需要一個旗標來暫時禁用此功能
        if not self.ui.menu_tree_view.signalsBlocked():
            
            # 獲取舊的路徑和新的名稱
            # 獲取舊路徑比較複雜，我們需要一個方法來從item反向推導
            # 但更簡單的方法是，在編輯前就記錄下舊的狀態
            # 這裡我們先用一個簡化的邏輯，假設我們可以拿到舊路徑
            
            # 重新思考：一個更穩健的方法是直接在觸發時同步所有資料
            # 因為我們無法輕易得知「舊的」名稱是什麼
            
            log.info("偵測到項目名稱變更，準備同步所有UI狀態...")
            
            # 使用我們已經存在的同步函式，它會處理好一切
            # 因為 get_ordered_data_from_tree 會重新計算所有路徑
            self._sync_data_from_ui()
            
            # 為了讓UI上的顯示（特別是文件夾的路徑）也更新，
            # 在同步資料後，最好再用更新後的資料刷新一次UI
            # 為了避免無限循環，我們在刷新前後阻擋/解除信號
            self.ui.menu_tree_view.blockSignals(True)
            self.ui.populate_menu_tree(self.current_menu_data)
            self.ui.menu_tree_view.blockSignals(False)
            
            log.info("項目重命名完成，資料與UI已同步。")