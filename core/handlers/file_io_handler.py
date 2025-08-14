# menubuilder/core/handlers/file_io_handler.py

from PySide2 import QtWidgets
from pathlib import Path

from ..logger import log
from ..translator import tr
 
# 為了型別提示 (Type Hinting) 而導入
from typing import TYPE_CHECKING
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
        # 主面板上的儲存按鈕也屬於檔案操作
        self.ui.save_button.clicked.connect(self.on_save_config_clicked)
        log.debug("FileIOHandler signals connected.")

    # --- 以下是從主控制器遷移過來的函式 ---

    def _update_ui_title(self):
        """輔助函式，用來通知UI更新標題。"""
        self.ui.update_tree_view_title(self.controller.current_config_name)

    def on_save_config_clicked(self):
        """儲存當前的菜單結構到檔案。"""
        self.controller._sync_data_from_ui()
        # 注意：此處儲存的是當前 controller 內的 config name
        self.data_handler.save_menu_config(self.controller.current_config_name, self.controller.current_menu_data)

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
        
        self.ui.populate_menu_tree(self.controller.current_menu_data)
        self.ui.auto_expand_single_root()
        self._update_ui_title()

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
            self.ui.populate_menu_tree(self.controller.current_menu_data)
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