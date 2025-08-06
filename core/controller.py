# core/controller.py
from .logger import log  # 從我們建立的logger模組導入已經配置好的log實例
#phase1 新增
from .setting_reader import current_setting
from .ui import MenuBuilderUI
from .data_handler import DataHandler

class MenuBuilderController:
    def __init__(self):
        log.info("MenuBuilderController 初始化開始...")
        self.data_handler = DataHandler()
        self.ui = MenuBuilderUI(self)
        self.current_menu_data = [] # 重要：用來儲存當前編輯的菜單資料
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

    def _load_initial_data(self):
        """載入設定中指定的預設菜單設定檔。"""
        default_config = current_setting.get("menuitems")
        if not default_config:
            log.warning("在 setting.json 中未指定預設的 'menuitems'。")
            return
            
        log.info(f"正在載入預設菜單設定檔: {default_config}.json")
        menu_data = self.data_handler.load_menu_config(default_config)
        
        if menu_data:
            self.ui.populate_menu_tree(menu_data)
            
        self.current_menu_data = self.data_handler.load_menu_config(default_config)
        if self.current_menu_data:
            self.ui.populate_menu_tree(self.current_menu_data)

    def on_browse_script_clicked(self):
        """當瀏覽按鈕被點擊時觸發。"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, "選擇 Python 腳本", "", "Python Files (*.py)")
        if not file_path:
            return
            
        self.ui.function_list.clear()
        functions = ScriptParser.parse_py_file(file_path)
        self.ui.function_list.addItems(functions)
        log.info(f"從 {file_path} 解析出 {len(functions)} 個函式。")

    def on_function_selected(self, current, previous):
        """當函式列表中的選項改變時觸發。"""
        if not current:
            return
        
        func_name = current.text()
        generated_label = ScriptParser.generate_label_from_string(func_name)
        
        # 將生成的標籤和函式名填入右側的屬性編輯器
        self.ui.label_input.setText(generated_label)
        
        # (這裡也可以預先填入其他欄位，例如從 manual_cmd_input 取得完整指令)

    # 新增方法:
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

    def show_ui(self):
        log.info("顯示 Menubuilder UI。")
        try:
            self.ui.show()
        except Exception as e:
            log.error(f"顯示UI時發生錯誤: {e}", exc_info=True) # exc_info=True 會記錄完整的錯誤堆疊