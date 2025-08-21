# menubuilder/core/handlers/tree_interaction_handler.py

from PySide2 import QtWidgets, QtCore
from ..dto import MenuItemData
from ..decorators import preserve_ui_state, block_ui_signals
from ..logger import log
from ..translator import tr
 
# 將會導致循環依賴的 import 語句，放入 if TYPE_CHECKING 區塊中
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..controller import MenuBuilderController
    from ..ui import MenuBuilderUI


class TreeInteractionHandler:
    """
    專門處理所有與左側「樹狀圖」UI 元件直接交互的邏輯。
    包括：拖曳、右鍵選單、重新命名、雙擊等。
    """
    def __init__(self, controller):
        log.debug(f'初始化{self.__class__.__name__}')
        self.controller:MenuBuilderController = controller
        self.ui:MenuBuilderUI = controller.ui

    def connect_signals(self):
        """連接所有與樹狀圖相關的 UI 信號。"""
        # [UX 優化] 新增 currentItemChanged 信號，用於單擊預覽
        self.ui.menu_tree_view.empty_space_clicked.connect(self._enter_add_mode)
        self.ui.menu_tree_view.currentItemChanged.connect(self.on_tree_item_selection_changed)
        
        self.ui.menu_tree_view.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.ui.menu_tree_view.customContextMenuRequested.connect(self.ui.on_tree_context_menu)
        self.ui.menu_tree_view.itemChanged.connect(self.on_tree_item_renamed)
        self.ui.menu_tree_view.drop_event_completed.connect(self.on_drop_event_completed)
        log.debug("TreeInteractionHandler signals connected.")
        
    
    def _enter_add_mode(self):
        """
        [最終版] 進入「新增模式」。清空所有欄位，並確保它們都處於可編輯狀態。
        """
        log.debug("Entering Add Mode...")
        # 1. 清空所有欄位
        self.ui.label_input.clear()
        self.ui.path_input.setCurrentText("")
        self.ui.icon_input.clear()
        self.ui.manual_cmd_input.clear()
        self.ui.function_list.clear()
        self.ui.current_script_path_label.clear()
        self.ui.python_radio.setChecked(True)
        #self.ui.input_tabs.setCurrentIndex(1)

        # 2. 重設 Controller 的編輯狀態
        self.controller.current_edit_item = None
        self.controller.insertion_target_item_data = None

        # 3. 直接設定 UI 狀態
        self.ui.add_update_button.setText(tr('add_to_structure_button'))
        if hasattr(self.ui, 'cancel_edit_button'):
            self.ui.cancel_edit_button.setVisible(False)

        # 4. 啟用所有欄位和按鈕，準備新增
        self.ui.set_editor_fields_enabled(True)

        # 5. 將游標聚焦，方便輸入
        self.ui.label_input.setFocus()


    def on_tree_item_selection_changed(self, current: QtWidgets.QTreeWidgetItem, previous: QtWidgets.QTreeWidgetItem):
        """
        [最終版] 只負責處理「項目之間」的切換，進入對應的模式。
        """
        if self.controller.current_edit_item:
            log.debug("Selection changed ignored: Currently in edit mode.")
            return

        # 如果 current 為 None，代表是透過程式碼或點擊空白處觸發的清空選取
        # 這種情況已經由 empty_space_clicked 信號處理，這裡直接返回即可。
        if not current:
            return

        item_data = current.data(0, QtCore.Qt.UserRole)

        # 如果選中的是資料夾或分隔線，進入新增模式
        if not item_data or item_data.is_divider:
            self._enter_add_mode()
            return
            
        # 只有選中功能項時，才進入預覽模式
        log.debug(f"Item '{item_data.menu_label}' selected. Entering Preview Mode.")
        self.ui.set_attributes_to_fields(item_data)
        self.ui.set_editor_fields_enabled(False)
        self.ui.add_update_button.setText(tr('add_to_structure_button'))

    def on_tree_item_double_clicked(self, item, column):
        """當項目被雙擊時，進入「編輯模式」。"""
        item_data = item.data(0, QtCore.Qt.UserRole)
        
        if not item_data or item_data.is_divider:
            return

        log.info(f"正在編輯項目: {item_data.menu_label}")
        self.controller.current_edit_item = item
        self.controller._refresh_editor_panel() # 呼叫主 Controller 的方法

    @preserve_ui_state
    def on_drop_event_completed(self, source_item, target_item, indicator):
        """處理合法的拖放，並確保 Option Box 正確跟隨其父物件。"""
        # --- [核心修正] ---
        # 在執行任何可能重建UI的操作前，先檢查是否處於編輯模式。
        # 如果是，則強制退出編輯模式，以避免產生指向已刪除物件的「殭屍參考」。
        if self.controller.current_edit_item:
            log.warning("拖曳操作中斷了進行中的編輯，已自動退出編輯模式。")
            # 注意：on_cancel_edit 存在於 editor_handler 中
            self.controller.editor_handler.on_cancel_edit()
        # --- 修正結束 ---

        source_data = source_item.data(0, QtCore.Qt.UserRole)
        if not source_data: return

        option_box_to_follow = self.controller._get_option_box_for_parent(source_data, self.controller.current_menu_data)
        self.controller._sync_data_from_ui()

        if option_box_to_follow:
            option_box_to_follow.sub_menu_path = source_data.sub_menu_path
            self.controller.current_menu_data.remove(option_box_to_follow)
            new_parent_index = self.controller.current_menu_data.index(source_data)
            self.controller.current_menu_data.insert(new_parent_index + 1, option_box_to_follow)
        
        self.controller.set_dirty(True)
        self.controller._refresh_ui_tree_and_paths()
        
        # 由於我們在開頭已經強制退出了編輯模式，這裡的 if 判斷將永遠為 False
        # 但保留它也無妨，程式碼依然是安全的
        if self.controller.current_edit_item:
            self.controller._refresh_editor_panel()
    
    @block_ui_signals('menu_tree_view')
    def on_tree_item_renamed(self, item, column):
        """處理重新命名，包含狀態守衛和命名衝突驗證。"""
        if self.controller.current_edit_item:
            log.debug("編輯模式中，忽略因程式化更新觸發的 itemChanged 信號。")
            return
            
        # ... (此函式內部邏輯不變，只是 self.xxx 需改為 self.controller.xxx)
        old_path = None
        for path, ui_item in self.ui.item_map.items():
            if ui_item == item:
                old_path = path
                break
        if old_path is None: return

        new_name = item.text(0)
        old_name = old_path.split('/')[-1]
        parent_path = "/".join(old_path.split('/')[:-1])
        if new_name == old_name: return

        item_data = item.data(0, QtCore.Qt.UserRole)
        if self.controller._is_name_conflict(new_name, parent_path, item_data):
            item.setText(0, old_name)
            return

        new_path = f"{parent_path}/{new_name}" if parent_path else new_name
        expansion_state_before = self.ui.get_expansion_state()
        new_expansion_state = set()
        for path in expansion_state_before:
            if path == old_path or path.startswith(old_path + '/'):
                corrected_path = path.replace(old_path, new_path, 1)
                new_expansion_state.add(corrected_path)
            else:
                new_expansion_state.add(path)
        
        self.controller._sync_data_from_ui()
        self.controller.set_dirty(True)
        self.controller._refresh_ui_tree_and_paths()
        self.ui.set_expansion_state(new_expansion_state)

    # --- 以下是處理右鍵選單的函式 ---

    @preserve_ui_state
    def on_context_delete(self, item: QtWidgets.QTreeWidgetItem):
        """
        [增加父物件判斷] 處理刪除操作，能同時刪除父物件與其選項框。
        """
        # 在執行任何可能重建UI的操作前，先檢查是否處於編輯模式。
        # 如果是，則強制退出編輯模式，以避免產生指向已刪除物件的「殭屍參考」。
        if self.controller.current_edit_item:
            log.warning("操作中斷了進行中的編輯，已自動退出編輯模式。")
            self.controller.on_cancel_edit()

        if not isinstance(item, QtWidgets.QTreeWidgetItem):
            return

        item_data = item.data(0, QtCore.Qt.UserRole)
        
        is_parent_item = False
        option_box_data_to_delete = None
        if item_data and not item_data.is_option_box:
            try:
                current_index = self.controller.current_menu_data.index(item_data)
                if (current_index + 1) < len(self.controller.current_menu_data):
                    item_after = self.controller.current_menu_data[current_index + 1]
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
                data for data in self.controller.current_menu_data 
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
            self.controller.current_menu_data = [d for d in self.controller.current_menu_data if d not in items_to_process_for_delete]
        
        self.controller.set_dirty(True)
        self.controller._refresh_ui_tree_and_paths()

    @preserve_ui_state
    def on_context_add_under(self, target_item: QtWidgets.QTreeWidgetItem):
        """
        [最終修正版] 在指定的父路徑下準備新增一個項目，並正確進入新增模式。
        """
        target_data = target_item.data(0, QtCore.Qt.UserRole)
        parent_path = ""

        if target_data:
            parent_path = target_data.sub_menu_path
            self.controller.insertion_target_item_data = target_data
        else:
            parent_path = self.ui.get_path_for_item(target_item)
            self.controller.insertion_target_item_data = None
        
        log.debug(f"準備在 '{parent_path}' 下新增項目。插入目標: {self.controller.insertion_target_item_data}")
        
        # 1. 清空編輯器並預填路徑
        self.ui.label_input.clear()
        self.ui.path_input.setCurrentText(parent_path)
        self.ui.manual_cmd_input.clear()
        
        # 2. 確保邏輯狀態已退出編輯模式
        self.controller.current_edit_item = None
        
        # 3. 刷新編輯器面板，因為 Controller 已被修正，這會進入「新增模式」
        self.controller._refresh_editor_panel()
        
        # 4. [關鍵] 確保所有欄位都可用於輸入
        self.ui.set_editor_fields_enabled(True)
        
        # 5. 將游標聚焦到標籤輸入框
        self.ui.label_input.setFocus()

    @preserve_ui_state
    def on_context_add_separator(self, target_item: QtWidgets.QTreeWidgetItem):
        """
        在指定項目的下方新增一個分隔線。
        """
        # --- [核心修正] ---
        # 在執行任何可能重建UI的操作前，先強制退出編輯模式。
        if self.controller.current_edit_item:
            log.warning("新增分隔線操作中斷了進行中的編輯，已自動退出編輯模式。")
            self.controller.editor_handler.on_cancel_edit()
        # --- 修正結束 ---

        self.controller._sync_data_from_ui()
        
        separator_data = MenuItemData(
            menu_label="---",
            is_divider=True
        )

        insert_index = len(self.controller.current_menu_data)

        if target_item:
            target_data = target_item.data(0, QtCore.Qt.UserRole)
            if target_data:
                separator_data.sub_menu_path = target_data.sub_menu_path
                try:
                    insert_index = self.controller.current_menu_data.index(target_data) + 1
                except ValueError:
                    log.warning("在資料列表中找不到目標項目，分隔線將被添加到末尾。")
            else:
                 separator_data.sub_menu_path = self.ui.get_path_for_item(target_item)
        else:
            separator_data.sub_menu_path = ""
        
        self.controller.current_menu_data.insert(insert_index, separator_data)
        
        self.controller.set_dirty(True)
        self.controller._refresh_ui_tree_and_paths()

    def on_context_send_path(self, path: str):
        """接收來自右鍵選單的路徑，並更新到UI輸入框中。"""
        log.debug(f"從右鍵選單接收到路徑: {path}")
        self.ui.path_input.setCurrentText(path)

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
        self.controller.set_dirty(True)
        self.controller._refresh_ui_tree_and_paths()

        # 如果程式正處於編輯模式，則刷新編輯器以反映變更
        if self.controller.current_edit_item:
            self.controller._refresh_editor_panel()