# core/controller.py
import functools # 導入 functools 以便使用 wraps
from .logger import log  # 從我們建立的logger模組導入已經配置好的log實例
#phase1 新增
from .setting_reader import current_setting
from .ui import MenuBuilderUI
from .data_handler import DataHandler
#phase2 新增
from .script_parser import ScriptParser
from PySide2 import QtWidgets
#phase3 新增
from .menu_generator import MenuGenerator # 導入 MenuGenerator
import maya.cmds as cmds
import os

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
        self.current_selected_script_path = None # <-- [新增] 用於儲存當前腳本的路徑
        self._load_initial_data()
        self._connect_signals()
        log.info("MenuBuilderController 初始化完成。")

    def _connect_signals(self):
        """集中管理所有UI信號的連接。"""
        self.ui.browse_button.clicked.connect(self.on_browse_script_clicked)
        self.ui.function_list.currentItemChanged.connect(self.on_function_selected)
        self.ui.add_update_button.clicked.connect(self.on_add_item_clicked)
        self.ui.delete_button.clicked.connect(self.on_delete_item_clicked)
        self.ui.save_button.clicked.connect(self.on_save_config_clicked)
        self.ui.build_menus_button.clicked.connect(self.on_build_menu_clicked)

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

    def on_save_config_clicked(self):
        """儲存當前的菜單結構到檔案。"""
        config_name = current_setting.get("menuitems") # 從設定檔取得要儲存的檔名
        self.data_handler.save_menu_config(config_name, self.current_menu_data)

    def on_build_menu_clicked(self):
        """當'生成/刷新菜單'按鈕被點擊時觸發。"""
        log.info("開始生成/刷新 Maya 菜單...")
        
        # 1. 清除舊菜單
        self.menu_generator.clear_existing_menus()
        
        # 2. 用當前編輯的資料建立新菜單
        self.menu_generator.build_from_config(self.current_menu_data)
        
        # 3. 給予使用者反饋
        cmds.inViewMessage(amg='<hl>菜單已成功生成/刷新！</hl>', pos='midCenter', fade=True)


    def show_ui(self):
        log.info("顯示 Menubuilder UI。")
        try:
            self.ui.show()
        except Exception as e:
            log.error(f"顯示UI時發生錯誤: {e}", exc_info=True) # exc_info=True 會記錄完整的錯誤堆疊