# menubuilder/core/handlers/settings_handler.py

from PySide2 import QtWidgets
from ..logger import log
from .. import setting_reader # 為了存取 current_setting 和 save_setting
from ..decorators import preserve_ui_state

# 為了型別提示 (Type Hinting) 而導入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..controller import MenuBuilderController
    from ..ui import MenuBuilderUI

class SettingsHandler:
    """
    一個專門處理所有與「設定」選單相關邏輯的類別。
    """
    def __init__(self, controller):
        """
        初始化 SettingsHandler。

        Args:
            controller (MenuBuilderController): 主控制器的實例，用於存取 UI 和共享資料。
        """
        log.debug(f'初始化{self.__class__.__name__}')
        self.controller:MenuBuilderController = controller
        self.ui:MenuBuilderUI = controller.ui

        self._populate_settings_menus()
    
    def connect_signals(self):
        """
        [新增] 連接所有與此 Handler 相關的 UI 信號。
        """
        self.ui.language_action_group.triggered.connect(self.on_language_changed)
        self.ui.log_level_action_group.triggered.connect(self.on_log_level_changed)
        self.ui.default_menu_action_group.triggered.connect(self.on_default_menu_changed)
        log.debug("SettingsHandler signals connected.")
    
    def _populate_settings_menus(self):
        """一次性填充所有設定相關的子選單。"""
        # --- 1. 填充語言選單 ---
        current_lang = setting_reader.current_setting.get('language', 'en_us')
        for lang_code in setting_reader.current_setting.get('languages_modes', ['en_us']):
            action = QtWidgets.QAction(lang_code, self.ui, checkable=True, checked=(lang_code == current_lang))
            action.setData(lang_code)
            self.ui.language_menu.addAction(action)
            self.ui.language_action_group.addAction(action)
            
        # --- 2. 填充日誌等級選單 ---
        current_log_level = setting_reader.current_setting.get('log_level', 'INFO').upper()
        for level in setting_reader.current_setting.get('log_modes', ['INFO', 'DEBUG']):
            action = QtWidgets.QAction(level, self.ui, checkable=True, checked=(level == current_log_level))
            action.setData(level)
            self.ui.log_level_menu.addAction(action)
            self.ui.log_level_action_group.addAction(action)
            
        # --- 3. 填充預設菜單選單 ---
        current_default_menu = setting_reader.current_setting.get('menuitems', '')
        menu_files = [f.stem for f in self.controller.data_handler.MENUITEMS_DIR.glob("*.json")]
        for menu_name in sorted(menu_files):
            action = QtWidgets.QAction(menu_name, self.ui, checkable=True, checked=(menu_name == current_default_menu))
            action.setData(menu_name)
            self.ui.default_menu_menu.addAction(action)
            self.ui.default_menu_action_group.addAction(action)

    @preserve_ui_state
    def on_language_changed(self, action):
        """當語言選項被點擊時觸發。"""
        new_lang = action.data()
        log.info(f"語言已切換至: {new_lang}")
        
        setting_reader.current_setting['language'] = new_lang
        setting_reader.save_setting(setting_reader.current_setting)
        
        from .. import translator
        translator.tr = translator.initialize_translator()
        self.ui.retranslate_ui()

    def on_log_level_changed(self, action):
        """當日誌等級選項被點擊時觸發。"""
        new_level = action.data()
        log.info(f"日誌等級已切換至: {new_level}")
        
        setting_reader.current_setting['log_level'] = new_level
        setting_reader.save_setting(setting_reader.current_setting)
        
        from .. import logger
        logger.log = logger.setup_logger(setting_reader.current_setting)
        
        QtWidgets.QMessageBox.information(self.ui, "Log Level Changed", f"Log level has been set to '{new_level}'.")
        log.info(f"--- Log level changed to {new_level} ---")

    def on_default_menu_changed(self, action):
        """當預設菜單選項被點擊時觸發。"""
        new_menu = action.data()
        log.info(f"預設啟動菜單已設定為: {new_menu}")
        
        setting_reader.current_setting['menuitems'] = new_menu
        setting_reader.save_setting(setting_reader.current_setting)
        
        QtWidgets.QMessageBox.information(self.ui, "Default Menu Changed", 
                                f"'{new_menu}' has been set as the default menu on startup.")