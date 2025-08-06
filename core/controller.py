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
        
        self._load_initial_data()
        log.info("MenuBuilderController 初始化完成。")

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

    def show_ui(self):
        log.info("顯示 Menubuilder UI。")
        try:
            self.ui.show()
        except Exception as e:
            log.error(f"顯示UI時發生錯誤: {e}", exc_info=True) # exc_info=True 會記錄完整的錯誤堆疊