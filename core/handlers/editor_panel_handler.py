# menubuilder/core/handlers/editor_panel_handler.py

from PySide2 import QtWidgets, QtCore
from maya import cmds, mel
import os

from ..logger import log
from ..translator import tr
from ..script_parser import ScriptParser
from ..decorators import preserve_ui_state, block_ui_signals

# 為了型別提示 (Type Hinting) 而導入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..controller import MenuBuilderController
    from ..ui import MenuBuilderUI

class EditorPanelHandler:
    """
    專門處理所有與右側「屬性編輯面板」相關的 UI 與邏輯。
    """
    def __init__(self, controller: "MenuBuilderController"):
        log.debug(f'初始化{self.__class__.__name__}')
        self.controller:MenuBuilderController = controller
        self.ui:MenuBuilderUI = controller.ui

    def connect_signals(self):
        """連接所有與編輯面板相關的 UI 信號。"""
        self.ui.browse_button.clicked.connect(self.on_browse_script_clicked)
        self.ui.function_list.currentItemChanged.connect(self.on_function_selected)
        self.ui.icon_buildin_btn.clicked.connect(self.on_browse_icon_clicked)
        self.ui.icon_browse_btn.clicked.connect(self.on_browse_custom_icon_clicked)
        self.ui.add_update_button.clicked.connect(self.on_add_item_clicked)
        self.ui.cancel_edit_button.clicked.connect(self.on_cancel_edit)
        self.ui.test_run_button.clicked.connect(self.on_test_run_clicked)
        log.debug("EditorPanelHandler signals connected.")

    def on_browse_script_clicked(self):
        """當瀏覽按鈕被點擊時觸發。"""
        start_dir = cmds.internalVar(userScriptDir = True)
        if self.controller.current_selected_script_path:
            start_dir = os.path.dirname(self.controller.current_selected_script_path)

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self.ui, tr("dialog_title_select_script"), start_dir, "Python Files (*.py)")
        
        if not file_path:
            self.controller.current_selected_script_path = None
            self.ui.current_script_path_label.clear()
            return
            
        self.controller.current_selected_script_path = file_path
        self.ui.current_script_path_label.setText(file_path)
        
        self.ui.function_list.clear()
        functions = ScriptParser.parse_py_file(file_path)
        self.ui.function_list.addItems(functions)
        log.info(f"從 {file_path} 解析出 {len(functions)} 個函式。")

    def on_function_selected(self, current, previous):
        """當函式列表中的選項改變時觸發。"""
        if not current or not self.controller.current_selected_script_path:
            return
        
        func_name = current.text()
        module_name = os.path.basename(self.controller.current_selected_script_path).replace('.py', '')

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
        self.ui.python_radio.setChecked(True)

    @preserve_ui_state
    def on_cancel_edit(self):
        """
        處理使用者取消編輯的操作 (例如按下 ESC 鍵)。
        """
        # 只有當前正處於編輯模式時，這個操作才有效
        if self.controller.current_edit_item:
            log.info("使用者取消編輯，正在退出編輯模式...")
            
            # 執行退出編輯模式的標準流程
            self.controller.current_edit_item = None
            self.controller._refresh_ui_tree_and_paths()
            self.controller._refresh_editor_panel()

    @preserve_ui_state
    def on_add_item_clicked(self):
        """處理「新增/更新」按鈕，並在操作後徹底重設狀態。"""
        edited_data = self.ui.get_attributes_from_fields()
        if not edited_data.menu_label:
            return

        item_to_update = self.controller.current_edit_item.data(0, QtCore.Qt.UserRole) if self.controller.current_edit_item else None
        
        if self.controller._is_name_conflict(edited_data.menu_label, edited_data.sub_menu_path, item_to_update):
            return

        self.controller._sync_data_from_ui()

        if self.controller.current_edit_item:
            # --- 更新現有項目的邏輯 (不變) ---
            item_data_to_update = self.controller.current_edit_item.data(0, QtCore.Qt.UserRole)
            log.info(f"更新項目 '{item_data_to_update.menu_label}'...")
            
            item_data_to_update.menu_label = edited_data.menu_label
            item_data_to_update.sub_menu_path = edited_data.sub_menu_path
            item_data_to_update.icon_path = edited_data.icon_path
            item_data_to_update.function_str = edited_data.function_str
            item_data_to_update.command_type = edited_data.command_type
            
            self.controller.current_edit_item = None
        else:
            # --- [核心修正] 新增項目的邏輯 ---
            target = self.controller.insertion_target_item_data
            if target:
                try:
                    # 找到目標在列表中的索引
                    target_index = self.controller.current_menu_data.index(target)
                    # 在目標的下一個位置插入新項目
                    self.controller.current_menu_data.insert(target_index + 1, edited_data)
                    log.info(f"已在 '{target.menu_label}' 之後插入新項目: {edited_data.menu_label}")
                except ValueError:
                    # 如果出錯 (極罕見)，則退回至預設行為
                    log.warning("找不到插入目標，將項目附加到列表末尾。")
                    self.controller.current_menu_data.append(edited_data)
                finally:
                    # 無論成功或失敗，都必須重設狀態，避免影響下一次操作
                    self.controller.insertion_target_item_data = None
            else:
                # 如果沒有指定插入目標 (例如直接在編輯器中新增)，則附加到末尾
                self.controller.current_menu_data.append(edited_data)
                log.info(f"已將新項目附加到列表末尾: {edited_data.menu_label}")
        
        self.controller.set_dirty(True)
        self.controller._refresh_ui_tree_and_paths()
        self.controller._refresh_editor_panel()

    def on_browse_icon_clicked(self):
        """當'瀏覽內建圖示'按鈕被點擊時，創建並顯示圖示瀏覽器。"""
        from ..ui import IconBrowserDialog
        icon_browser = IconBrowserDialog(self.ui) # 需從 ui 模組獲取
        icon_browser.icon_selected.connect(self.on_icon_selected_from_browser)
        icon_browser.exec_()

    def on_browse_custom_icon_clicked(self):
        """處理'瀏覽自訂圖示'按鈕的點擊事件。"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.ui, tr("dialog_title_select_icon"), "", "Image Files (*.png *.svg *.jpg *.bmp)"
        )
        if file_path:
            self.ui.icon_input.setText(file_path)

    def on_icon_selected_from_browser(self, icon_path: str):
        """當圖示瀏覽器發出'icon_selected'信號時，接收圖示路徑並更新UI。"""
        self.ui.icon_input.setText(icon_path)

    def on_test_run_clicked(self):
        """即時測試編輯器中的指令，並將結果輸出到 Script Editor。"""
        code_to_run = self.ui.manual_cmd_input.toPlainText().strip()
        is_mel = self.ui.mel_radio.isChecked()
        
        # No code skip action
        if not code_to_run: return

        log.info("\n" + "="*50)
        log.info("--- Menubuilder: Attempting Test Run ---")
        success = False
        error_info = ""

        try:
            if not is_mel:
                log.info("Executing as PYTHON:\n")
                log.info(code_to_run)
                exec(code_to_run, globals(), locals())

            else:
                log.info("Executing as MEL:\n")
                log.info(code_to_run)
                mel.eval(code_to_run)
            success = True
        
        except Exception as e:
            error_info = f"# Error: {e}"
            success = False
        
        # --- 格式化最終輸出 ---
        if success:
            log.info("\n\nExecuted successfully.")
            cmds.inViewMessage(amg=f"<hl>{tr('controller_info_test_run_success')}</hl>", pos='midCenter', fade=True)
        else:
            cmds.warning(f"{tr('controller_warn_test_run_failed')} {error_info}")
        log.info("--- Test Run Finished ---")
        log.info("="*50 + "\n")

