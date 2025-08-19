# ui.py

"""
Menubuilder - User Interface Module (View)

這個模組是 MVC 架構中的「視圖(View)」層。

它包含了所有使用者介面的定義，使用 PySide2 框架編寫。
主要包含 `MenuBuilderUI` (主視窗) 和 `IconBrowserDialog` (圖示瀏覽器)
等類別。它的職責是呈現資料和佈局，並在使用者操作時發出信號(signals)
給 Controller。它本身不包含任何業務邏輯。
"""

import maya.OpenMayaUI as omui
import maya.cmds as cmds
import functools

from PySide2 import QtWidgets, QtCore, QtGui
from shiboken2 import wrapInstance
from typing import List
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .controller import MenuBuilderController

from .dto import MenuItemData
from .logger import log
from .translator import tr
from .. import __version__


def get_maya_main_window():
    """
    [最終加固版] 獲取Maya主視窗的 PySide2 物件指標。
    這個方法比 MQtUtil.mainWindow() 更穩健，尤其是在啟動過程中。
    """
    try:
        # 遍歷應用程式的所有頂層視窗
        for widget in QtWidgets.QApplication.topLevelWidgets():
            # 尋找物件名稱為 "MayaWindow" 的 QMainWindow
            if widget.objectName() == "MayaWindow":
                return widget
    except Exception as e:
        log.error(f"尋找Maya主視窗時出錯: {e}")
    
    # 如果上面的方法失敗，再嘗試使用舊的方法作為備用
    try:
        main_window_ptr = omui.MQtUtil.mainWindow()
        if main_window_ptr:
            return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    except Exception as e:
        log.error(f"備用方法 MQtUtil.mainWindow() 也失敗了: {e}")

    return None

class MenuBuilderUI(QtWidgets.QMainWindow):
    """
    Menubuilder 的主 UI 視窗，扮演 MVC 架構中的視圖(View)角色。
    
    這個類別負責創建和佈局所有的UI元件，例如按鈕、列表、輸入框等。
    它接收來自 Controller 的指令來更新顯示，並在使用者操作時發出信號(signals)
    通知 Controller。它本身不包含任何業務邏輯。
    """
    def __init__(self, controller, parent = None):
        """
        初始化 MenuBuilderUI 主視窗。

        Args:
            controller (MenuBuilderController): 控制器物件的實例，用於信號連接。
        """
        if parent is None: parent = get_maya_main_window()
        super(MenuBuilderUI, self).__init__(parent)
        self.setGeometry(300, 300, 800, 700)

        self.controller:MenuBuilderController = controller
        self.item_map = {}# 儲存 QTreeWidgetItems 以便查找

        self._retranslation_list = []
        self._init_ui()

        QtWidgets.QApplication.instance().installEventFilter(self)

    def _init_ui(self):
        """初始化UI元件和佈局。"""
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        
        top_level_layout = QtWidgets.QVBoxLayout(main_widget)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        top_level_layout.addWidget(splitter)

        left_container_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_container_widget)

        self.left_label = QtWidgets.QLabel()
        self.menu_tree_view = DraggableTreeWidget()
        self.menu_tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self._retranslation_list.append((self.menu_tree_view.setHeaderLabels, "menu_structure_header", {'prop': 'header'}))
        self._retranslation_list.append((self.left_label.setText, "menu_config_title", {}))


        left_layout.addWidget(self.left_label)
        left_layout.addWidget(self.menu_tree_view)

        right_container_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_container_widget)

        self.input_tabs = QtWidgets.QTabWidget()
        file_parse_widget = QtWidgets.QWidget()
        manual_input_widget = QtWidgets.QWidget()

        self.input_tabs.addTab(file_parse_widget, tr('tab_parse_from_file'))
        self.input_tabs.addTab(manual_input_widget, tr('tab_manual_input'))
        self._retranslation_list.append((self.input_tabs.setTabText, "tab_parse_from_file", {'prop': 'tabtext', 'tab_index': 0}))
        self._retranslation_list.append((self.input_tabs.setTabText, "tab_manual_input",  {'prop': 'tabtext', 'tab_index': 1}))

        file_parse_layout = QtWidgets.QVBoxLayout(file_parse_widget)
        self.browse_button = QtWidgets.QPushButton()
        self.current_script_path_label = QtWidgets.QLineEdit()
        self.current_script_path_label.setReadOnly(True)
        self.current_script_path_label.setStyleSheet("background-color: #2E2E2E; border: none;")

        self._retranslation_list.append((self.browse_button.setText, "browse_script_button", {}))

        self.function_list = QtWidgets.QListWidget()
        file_parse_layout.addWidget(self.browse_button)
        file_parse_layout.addWidget(self.current_script_path_label)
        file_parse_layout.addWidget(self.function_list)

        # -- Tab 2: Manual Input Layout --
        manual_input_layout = QtWidgets.QVBoxLayout(manual_input_widget)
        
        # --- [新增] 指令類型選擇 ---
        # -----------------------------------------------------------------
        self.python_radio = QtWidgets.QRadioButton('Python')
        self.mel_radio = QtWidgets.QRadioButton('MEL')
        self.python_radio.setChecked(True) # 預設選中 Python
        
        # 使用 QButtonGroup 確保互斥
        self.command_type_group = QtWidgets.QButtonGroup()
        self.command_type_group.addButton(self.python_radio)
        self.command_type_group.addButton(self.mel_radio)

        command_type_layout = QtWidgets.QHBoxLayout()
        self.command_type_label = QtWidgets.QLabel()
        command_type_layout.addWidget(self.command_type_label)
        command_type_layout.addWidget(self.python_radio)
        command_type_layout.addWidget(self.mel_radio)
        command_type_layout.addStretch()

        self._retranslation_list.append((self.command_type_label.setText, "command_type_label", {}))
        # -----------------------------------------------------------------

        self.manual_cmd_input = QtWidgets.QTextEdit()
        self.test_run_button = QtWidgets.QPushButton() 

        self._retranslation_list.append((self.manual_cmd_input.setPlaceholderText, "command_input_placeholder", {}))
        self._retranslation_list.append((self.test_run_button.setText, "test_run_button", {}))

        manual_input_layout.addLayout(command_type_layout) 
        manual_input_layout.addWidget(self.manual_cmd_input)
        manual_input_layout.addWidget(self.test_run_button) 

        self.attribute_box = QtWidgets.QGroupBox()
        self.form_layout = QtWidgets.QFormLayout()
        self.label_input = QtWidgets.QLineEdit()
        self.path_input = QtWidgets.QComboBox()
        self.path_input.setEditable(True)
        icon_path_layout = QtWidgets.QHBoxLayout()
        self.icon_input = QtWidgets.QLineEdit()
        self.icon_browse_btn = QtWidgets.QPushButton()
        self.icon_buildin_btn = QtWidgets.QPushButton()

        icon_path_layout.addWidget(self.icon_input)
        icon_path_layout.addWidget(self.icon_browse_btn)
        icon_path_layout.addWidget(self.icon_buildin_btn)
        
        self.icon_preview = QtWidgets.QLabel()
        self.icon_preview.setFixedSize(32, 32)
        self.icon_preview.setStyleSheet("border: 1px solid #555; background-color: #333; border-radius: 4px;")
        self.icon_preview.setAlignment(QtCore.Qt.AlignCenter)
        
        self._retranslation_list.append((self.attribute_box.setTitle, "attribute_editor_group", {}))
        self._retranslation_list.append((self.icon_input.setPlaceholderText, "icon_placeholder", {}))
        self._retranslation_list.append((self.icon_browse_btn.setText, "custom_button", {}))
        self._retranslation_list.append((self.icon_browse_btn.setToolTip, "custom_icon_tooltip", {}))
        self._retranslation_list.append((self.icon_buildin_btn.setText, "builtin_button", {}))
        self._retranslation_list.append((self.icon_buildin_btn.setToolTip, "builtin_icon_tooltip", {}))
        self._retranslation_list.append((self.icon_preview.setText, "preview_none", {}))

        self.icon_input.textChanged.connect(self.update_icon_preview)

        self.form_layout.addRow(tr('label_form'), self.label_input)
        self.form_layout.addRow(tr('path_form'), self.path_input)
        self.form_layout.addRow(tr('icon_form'), icon_path_layout)
        self.form_layout.addRow(tr('preview_form'), self.icon_preview)
        
        self._retranslation_list.append((self.form_layout.itemAt(0, QtWidgets.QFormLayout.LabelRole).widget().setText, "label_form", {}))
        self._retranslation_list.append((self.form_layout.itemAt(1, QtWidgets.QFormLayout.LabelRole).widget().setText, "path_form", {}))
        self._retranslation_list.append((self.form_layout.itemAt(2, QtWidgets.QFormLayout.LabelRole).widget().setText, "icon_form", {}))
        self._retranslation_list.append((self.form_layout.itemAt(3, QtWidgets.QFormLayout.LabelRole).widget().setText, "preview_form", {}))

        self.attribute_box.setLayout(self.form_layout)

        # --- 建立一個垂直方向的 QSplitter ---
        # -------------------------------------------------------------
        self.right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.right_splitter.addWidget(self.input_tabs)      # 將 Tab Widget 作為上半部分
        self.right_splitter.addWidget(self.attribute_box) # 將屬性編輯器作為下半部分
        self.right_splitter.setSizes([500, 200]) 

        update_edit_layout = QtWidgets.QHBoxLayout()
        self.add_update_button = QtWidgets.QPushButton()
        self.cancel_edit_button = QtWidgets.QPushButton()
        self.cancel_edit_button.setVisible(False)
        update_edit_layout.addWidget(self.cancel_edit_button)
        update_edit_layout.addWidget(self.add_update_button)

        self.save_button = QtWidgets.QPushButton()
        self.build_menus_button = QtWidgets.QPushButton()

        # 注意：add_update_button 的文字是動態的，由 controller._refresh_editor_panel 處理
        # 因此它「不需要」被註冊到這個靜態列表中
        self._retranslation_list.append((self.cancel_edit_button.setText, "cancel_edit_button", {}))
        self._retranslation_list.append((self.save_button.setText, "save_config_button", {}))
        self._retranslation_list.append((self.build_menus_button.setText, "build_menus_button", {}))

        right_layout.addWidget(self.right_splitter)
        right_layout.addLayout(update_edit_layout)
        right_layout.addWidget(self.build_menus_button)
        right_layout.addWidget(self.save_button)

        splitter.addWidget(left_container_widget)
        splitter.addWidget(right_container_widget)
        
        splitter.setSizes([300, 450]) 

        menu_bar = self.menuBar()
        self.file_menu = menu_bar.addMenu(tr('file_menu'))

        self.open_action = self.file_menu.addAction(tr('open_action'))
        self.merge_action = self.file_menu.addAction(tr('merge_action'))
        self.save_action = self.file_menu.addAction(tr('save_action'))
        self.save_as_action = self.file_menu.addAction(tr('save_as_action'))
        self.file_menu.addSeparator()

        self.open_config_folder_action = self.file_menu.addAction(tr('open_config_folder_action')) 
        self.file_menu.addSeparator() # 在它後面再加一個分隔線

        self.import_from_shelf_action = self.file_menu.addAction(tr('import_from_shelf_action'))
        self.exit_action = self.file_menu.addAction(tr('exit_action'))

        self.settings_menu = menu_bar.addMenu(tr("settings_menu"))

        self.language_menu = self.settings_menu.addMenu(tr("language_action"))
        self.language_action_group = QtWidgets.QActionGroup(self)
        self.language_action_group.setExclusive(True)

        self.log_level_menu = self.settings_menu.addMenu(tr("log_level"))
        self.log_level_action_group = QtWidgets.QActionGroup(self)
        self.log_level_action_group.setExclusive(True)
        
        self.default_menu_menu = self.settings_menu.addMenu(tr('default_menu_on_startup'))
        self.default_menu_action_group = QtWidgets.QActionGroup(self)
        self.default_menu_action_group.setExclusive(True)


        self.help_menu = menu_bar.addMenu(tr('help_menu'))
        
        self.about_action = self.help_menu.addAction(tr('about_action'))
        self.github_action = self.help_menu.addAction(tr('github_action'))

        self._retranslation_list.append((self.file_menu.setTitle, "file_menu", {}))
        self._retranslation_list.append((self.open_action.setText, "open_action", {}))
        self._retranslation_list.append((self.merge_action.setText, "merge_action", {}))
        self._retranslation_list.append((self.save_action.setText, "save_action", {}))
        self._retranslation_list.append((self.save_as_action.setText, "save_as_action", {}))
        self._retranslation_list.append((self.open_config_folder_action.setText, "open_config_folder_action", {}))
        self._retranslation_list.append((self.import_from_shelf_action.setText, "import_from_shelf_action", {}))
        self._retranslation_list.append((self.exit_action.setText, "exit_action", {}))
        
        self._retranslation_list.append((self.settings_menu.setTitle, "settings_menu", {}))
        self._retranslation_list.append((self.language_menu.setTitle, "language_action", {}))
        self._retranslation_list.append((self.log_level_menu.setTitle, "log_level", {}))
        self._retranslation_list.append((self.default_menu_menu.setTitle, "default_menu_on_startup", {}))

        self._retranslation_list.append((self.help_menu.setTitle, "help_menu", {}))
        self._retranslation_list.append((self.about_action.setText, "about_action", {}))
        self._retranslation_list.append((self.github_action.setText, "github_action", {}))


    def retranslate_ui(self):
        """
        [修正版] 遍歷已註冊的 UI 元件列表，並根據註冊的選項，
        正確地處理不同參數數量的更新函式。
        """
        log.info("正在自動化重新翻譯 UI...")
        # --- 核心自動化邏輯 ---
        # --- 加入結束 ---

        for setter_method, key, options in self._retranslation_list:
            text = tr(key)
            
            prop = options.get('prop')

            # 使用 if/elif/else 結構來處理不同的呼叫方式
            if prop == 'tabtext':
                # 特殊情況：setTabText 需要 index 和 text 兩個參數
                setter_method(options.get('tab_index', -1), text)
            elif prop == 'header':
                # 特殊情況：setHeaderLabels 需要一個 list
                setter_method([text])
            else:
                # [修正] 預設情況：確保 text 參數被正確傳遞
                # 這將正確處理 setText, setTitle, setPlaceholderText, setToolTip 等
                setter_method(text)

        # --- 處理少數無法簡單註冊的動態文字 ---
        self.setWindowTitle(f"{tr('window_title')} v{__version__}")
        if self.controller: # 增加保護，確保 controller 已存在
            self.controller._refresh_editor_panel()
            self.update_tree_view_title(self.controller.current_config_name)
            self.populate_menu_tree(self.controller.current_menu_data)

        log.info("UI 自動化重新翻譯完成。")
        
    def center_on_screen(self):
        """
        計算螢幕中心點，並將視窗移動至該處。
        """
        # 獲取主螢幕的可用幾何區域 (不包含任務欄等)
        screen_geometry = QtWidgets.QApplication.primaryScreen().availableGeometry()
        
        # 獲取視窗自身的尺寸
        window_geometry = self.frameGeometry()
        
        # 計算中心點
        center_point = screen_geometry.center()
        
        # 將視窗的左上角移動到 (中心點 - 視窗尺寸的一半) 的位置
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())


    def populate_menu_tree(self, items: List[MenuItemData]):
        """
        根據提供的資料列表，完整地重建左側的樹狀視圖。

        這個函式不依賴傳入列表的順序。它會動態地解析每個項目的
        `sub_menu_path` 來創建或查找父級節點，確保層級結構的正確性。
        同時，它會為特殊項目（如選項框）應用自訂的視覺樣式，並將
        `MenuItemData` 物件本身附加到對應的UI項目上以便後續使用。

        Args:
            items (List[MenuItemData]): 用於渲染UI樹的菜單項資料列表。
        """
        self.menu_tree_view.blockSignals(True)
        self.menu_tree_view.clear()
        self.item_map.clear()
        
        for item_data in items:
            parent_ui_item = self.menu_tree_view.invisibleRootItem()
            
            if item_data.sub_menu_path:
                path_parts = item_data.sub_menu_path.split('/')
                full_path_key = ""
                for part in path_parts:
                    full_path_key = f"{full_path_key}/{part}" if full_path_key else part
                    
                    if full_path_key in self.item_map:
                        parent_ui_item = self.item_map[full_path_key]
                    else:
                        new_parent = QtWidgets.QTreeWidgetItem(parent_ui_item, [part])
                        new_parent.setFlags(new_parent.flags() | QtCore.Qt.ItemIsEditable)
                        self.item_map[full_path_key] = new_parent
                        parent_ui_item = new_parent

            display_label = item_data.menu_label
            
            if item_data.is_divider:
                display_label = tr('divider_text')
            elif item_data.is_option_box:
                display_label = tr('option_box_prefix', label=item_data.menu_label)

            menu_qitem = QtWidgets.QTreeWidgetItem(parent_ui_item, [display_label])
            menu_qitem.setData(0, QtCore.Qt.UserRole, item_data)

            if item_data.is_divider:
                flags = QtCore.Qt.ItemIsEnabled
                menu_qitem.setFlags(flags)
                menu_qitem.setForeground(0, QtGui.QColor("#666666"))
            elif item_data.is_option_box:
                # [核心修正] 設定 Option Box 的旗標：可以啟用和選擇，但禁止拖曳
                flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                menu_qitem.setFlags(flags)

                # 以下的視覺樣式設定不變
                menu_qitem.setToolTip(0, tr('option_box_tooltip'))
                font = menu_qitem.font(0)
                font.setItalic(True)
                menu_qitem.setFont(0, font)
                menu_qitem.setForeground(0, QtGui.QColor("#BF6969"))

            final_path = f"{item_data.sub_menu_path}/{item_data.menu_label}" if item_data.sub_menu_path else item_data.menu_label
            self.item_map[final_path] = menu_qitem

        self.menu_tree_view.blockSignals(False)
    
    def set_editor_fields_enabled(self, enabled: bool):
        """
        統一設定右側編輯器面板所有欄位的啟用/唯讀狀態，
        並包含主操作按鈕 (Add/Update)。
        """
        # 文字輸入框使用 setReadOnly
        self.label_input.setReadOnly(not enabled)
        self.icon_input.setReadOnly(not enabled)
        self.manual_cmd_input.setReadOnly(not enabled)

        # QComboBox 和 按鈕 使用 setEnabled
        self.path_input.setEnabled(enabled)
        self.icon_browse_btn.setEnabled(enabled)
        self.icon_buildin_btn.setEnabled(enabled)
        self.test_run_button.setEnabled(enabled)
        
        # 指令類型單選鈕
        self.python_radio.setEnabled(enabled)
        self.mel_radio.setEnabled(enabled)

        # [核心修正] 將主操作按鈕也納入控制
        self.add_update_button.setEnabled(enabled)
        
        # 根據啟用狀態，給予視覺提示
        style_sheet = ""
        if not enabled:
            style_sheet = "background-color: #2E2E2E;"
        
        self.label_input.setStyleSheet(style_sheet)
        self.icon_input.setStyleSheet(style_sheet)
        self.manual_cmd_input.setStyleSheet(style_sheet)


    def get_attributes_from_fields(self) -> MenuItemData:
        """
        從右側編輯器面板的所有輸入框中收集當前的值，並打包成一個新的
        MenuItemData 物件。

        Returns:
            MenuItemData: 一個包含了右側面板所有當前設定的新資料物件。
        """
        function_string = self.manual_cmd_input.toPlainText()
        
        # --- [修改] 獲取指令類型 ---
        command_type = "mel" if self.mel_radio.isChecked() else "python"

        # 創建 DTO 物件並填充資料
        item_data = MenuItemData(
            menu_label=self.label_input.text(),
            sub_menu_path=self.path_input.currentText(),
            icon_path=self.icon_input.text(),
            function_str=function_string,
            command_type=command_type # <-- [修改] 傳入指令類型
        )
        return item_data
        
    def get_expansion_state(self) -> set:
        """[優化後] 遍歷樹並返回所有已展開項目的路徑集合。"""
        expanded_paths = set()
        iterator = QtWidgets.QTreeWidgetItemIterator(self.menu_tree_view)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                path = self.get_path_for_item(item)
                expanded_paths.add(path)
            iterator += 1
        return expanded_paths
        
    def get_ordered_data_from_tree(self) -> List[MenuItemData]:
        """
        遞迴掃描整個UI樹，返回一個完全按照當前視覺順序和結構排序的資料列表。

        這是實現「所見即所得」排序的核心。它不僅保證了順序，還會在過程中
        自動修正被拖放過的項目的 `sub_menu_path` 屬性，確保資料的準確性。

        Returns:
            List[MenuItemData]: 一個與UI視覺呈現完全同步的、有序的資料列表。
        """
        log.info("從UI樹狀視圖掃描並生成有序的資料列表...")
        ordered_list = []
        self._recursive_tree_walk(self.menu_tree_view.invisibleRootItem(), "", ordered_list)
        log.info(f"掃描完成，共獲取 {len(ordered_list)} 個項目。")
        return ordered_list

    def _recursive_tree_walk(self, parent_item: QtWidgets.QTreeWidgetItem, parent_path: str, ordered_list: List[MenuItemData]):
        """
        私有輔助方法：遞迴地遍歷一個父節點下的所有子節點。
        
        Args:
            parent_item: 當前遍歷的父級QTreeWidgetItem。
            parent_path: 父級的菜單路徑 (e.g., "Tools/Modeling")。
            ordered_list: 用於收集結果的列表。
        """
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            item_data = child_item.data(0, QtCore.Qt.UserRole)
            current_item_text = child_item.text(0)
            current_path = f"{parent_path}/{current_item_text}" if parent_path else current_item_text
            
            if item_data:
                item_data.sub_menu_path = parent_path
                ordered_list.append(item_data)

            if child_item.childCount() > 0:
                self._recursive_tree_walk(child_item, current_path, ordered_list)
                
    def set_expansion_state(self, expanded_paths: set):
        """根據提供的路徑集合，展開對應的項目。"""
        if not expanded_paths:
            return
        
        for path, item in self.item_map.items():
            if path in expanded_paths:
                item.setExpanded(True)        

    def set_attributes_to_fields(self, data: MenuItemData):
        """
        接收一個 MenuItemData 物件，並將其內容更新到右側的編輯器UI上。

        Args:
            data (MenuItemData): 要顯示在編輯器中的資料物件。
        """
        if not data:
            log.warning("傳入的 item_data 為空，無法填入欄位。")
            return

        self.label_input.setText(data.menu_label)
        self.path_input.setCurrentText(data.sub_menu_path)
        self.icon_input.setText(data.icon_path)
        
        # --- [修改] 根據資料設定指令類型 ---
        if data.command_type == "mel":
            self.mel_radio.setChecked(True)
        else:
            self.python_radio.setChecked(True)
        
        # 即使是MEL，也切換到手動輸入頁面，因為那是指令的唯一來源
        self.input_tabs.setCurrentIndex(1)
        self.manual_cmd_input.setText(data.function_str)

    def get_path_for_item(self, item: QtWidgets.QTreeWidgetItem) -> str:
        """輔助函式：獲取一個QTreeWidgetItem的完整層級路徑。"""
        path = []
        while item is not None:
            path.insert(0, item.text(0))
            item = item.parent()
        return "/".join(path)

    def on_tree_context_menu(self, point: QtCore.QPoint):
        """
        右鍵選項邏輯。
        """
        menu = QtWidgets.QMenu(self)
        item = self.menu_tree_view.itemAt(point)

        if item:
            item_data = item.data(0, QtCore.Qt.UserRole)
            
            is_parent_item = False
            if item_data and not item_data.is_option_box:
                item_below = self.menu_tree_view.itemBelow(item)
                if item_below and item.parent() == item_below.parent():
                    data_below = item_below.data(0, QtCore.Qt.UserRole)
                    if data_below and data_below.is_option_box:
                        is_parent_item = True
            
            path_for_actions = item_data.sub_menu_path if item_data else self.get_path_for_item(item)
            
            # --- 結構群組 ---
            if item_data and not item_data.is_divider:
                action_toggle_option_box = QtWidgets.QAction()
                if item_data.is_option_box:
                    action_toggle_option_box.setText(tr('context_unset_option_box'))
                    action_toggle_option_box.setEnabled(True)
                else:
                    action_toggle_option_box.setText(tr('context_set_option_box'))
                    is_valid = True
                    if is_parent_item: is_valid = False
                    else:
                        item_above = self.menu_tree_view.itemAbove(item)
                        if not item_above or item.parent() != item_above.parent(): is_valid = False
                        else:
                            data_above = item_above.data(0, QtCore.Qt.UserRole)
                            if not data_above or data_above.is_option_box: is_valid = False
                    action_toggle_option_box.setEnabled(is_valid)
                action_toggle_option_box.triggered.connect(functools.partial(self.controller.tree_handler.on_context_toggle_option_box, item))
                menu.addAction(action_toggle_option_box)

            action_add_under = menu.addAction(tr('context_add_item'))
            #action_add_under.triggered.connect(functools.partial(self.controller.tree_handler.on_context_add_under, path_for_actions))
            action_add_under.triggered.connect(functools.partial(self.controller.tree_handler.on_context_add_under, item))

            is_folder = not item_data

            # --- [核心修正] ---
            # 只有在當前項目不是分隔線的情況下，才加入“新增分隔線”的選項
            if not (item_data and item_data.is_divider):
                action_add_separator = menu.addAction(tr('context_add_separator'))
                action_add_separator.triggered.connect(functools.partial(self.controller.tree_handler.on_context_add_separator, item))
                # 如果是父物件或資料夾，則將其設為禁用 (因為選項已出現)
                if is_parent_item or is_folder:
                    action_add_separator.setEnabled(False)
            # --- 修正結束 ---

            # 父物件下方不能插入任何東西
            if is_parent_item:
                action_add_under.setEnabled(False)

            menu.addSeparator()

            # --- 輔助與破壞性群組 ---
            if not (item_data and item_data.is_divider):
                menu.addAction(tr('context_send_path', path=path_for_actions),
                               functools.partial(self.controller.tree_handler.on_context_send_path, path_for_actions))
                menu.addSeparator()
            
            action_delete = menu.addAction(tr('context_delete'))
            if is_parent_item:
                action_delete.setText(tr('context_delete_parent_with_option_box'))
            action_delete.triggered.connect(functools.partial(self.controller.tree_handler.on_context_delete, item))
        else:
            # --- 情況三：點擊空白處 ---
            pass

        menu.exec_(self.menu_tree_view.mapToGlobal(point))

    def update_tree_view_title(self, filename: str):
        """更新左側樹狀視圖的標題以顯示當前檔名和'髒'狀態。"""
        dirty_indicator = "*" if self.controller.is_dirty else ""
        #    圓點字元是 ● (U+25CF)，顏色可以選一個醒目的紅色系
        label_dirty_indicator = " <span style='color: #F44336;'>●</span>" if self.controller.is_dirty else ""

        if filename:
            title = tr('menu_config_title_with_file', filename=f"{filename}.json")
            self.left_label.setText(f"{title}{label_dirty_indicator}")
            # 更新主視窗標題
            self.setWindowTitle(f"{tr('window_title')} v{__version__} - {filename}.json{dirty_indicator}")
        else:
            title = tr('menu_config_title')
            self.left_label.setText(f"{title}{label_dirty_indicator}")
            self.setWindowTitle(f"{tr('window_title')} v{__version__}")

    def update_icon_preview(self, path: str):
        """
        當圖示路徑輸入框的文字改變時，即時更新預覽區域的圖片。

        Args:
            path (str): 輸入框中當前的文字（圖示路徑）。
        """
        if not path:
            self.icon_preview.clear()
            self.icon_preview.setText(tr('preview_none'))
            return

        icon = QtGui.QIcon(path)
        if icon.isNull():
            self.icon_preview.clear()
            self.icon_preview.setText(tr('preview_invalid'))
        else:
            pixmap = icon.pixmap(32, 32)
            self.icon_preview.setPixmap(pixmap)

    def set_item_highlight(self, item_to_highlight: QtWidgets.QTreeWidgetItem, bold: bool = True):
        """設定指定UI項目的高亮（粗體）狀態。"""
        if not item_to_highlight:
            return
        font = item_to_highlight.font(0)
        font.setBold(bold)
        item_to_highlight.setFont(0, font)

        """ 編輯鎖定後，背景顏色就不重要了
        if bold:
            highlight_color = QtGui.QColor("#34532D")
            item_to_highlight.setBackground(0, QtGui.QBrush(highlight_color))
        else:
            item_to_highlight.setBackground(0, QtGui.QBrush())
        """
    
    def clear_all_highlights(self):
        """清除樹狀視圖中所有項目的高亮狀態，使其恢復正常字體。"""
        iterator = QtWidgets.QTreeWidgetItemIterator(self.menu_tree_view)
        while iterator.value():
            item = iterator.value()
            font = item.font(0)
            if font.bold():
                font.setBold(False)
                item.setFont(0, font)

            """ 編輯鎖定後，背景顏色就不重要了
            if item.background(0).style() != QtCore.Qt.NoBrush:
                 item.setBackground(0, QtGui.QBrush())
            """
            iterator += 1

    def auto_expand_single_root(self):
        """
        檢查樹狀視圖的頂層項目。如果只有一個，就自動將其展開。
        """
        if self.menu_tree_view.topLevelItemCount() == 1:
            log.debug("檢測到單一根目錄，自動展開。")
            root_item = self.menu_tree_view.topLevelItem(0)
            root_item.setExpanded(True)

    def eventFilter(self, watched_object, event):
        """
        覆寫 Qt 內建的事件過濾器。
        這個函式會攔截應用程式中的所有事件。
        """
        # 我們只關心鍵盤按下的事件
        if event.type() == QtCore.QEvent.KeyPress:
            # 並且只關心被按下的鍵是否為 ESC
            if event.key() == QtCore.Qt.Key_Escape:
                # 如果是，就呼叫 Controller 的取消函式
                log.debug("事件過濾器偵測到 ESC 鍵，嘗試取消編輯。")
                self.controller.editor_handler.on_cancel_edit()
                # 返回 True，代表我們已經處理了這個事件，它不需要再繼續傳遞
                return True
        
        # 對於所有其他不關心的事件，把它們交還給 Qt 繼續進行預設的處理
        return super(MenuBuilderUI, self).eventFilter(watched_object, event)
    def clean_up(self):
        """
        在視窗關閉前執行必要的清理工作，尤其是移除全域事件過濾器。
        """
        log.info("正在清理 UI，移除全域事件過濾器...")
        QtWidgets.QApplication.instance().removeEventFilter(self)
        log.info("事件過濾器已成功移除。")


    def closeEvent(self, event: QtGui.QCloseEvent):
        """
        [新增] 覆寫 Qt 的關閉事件。
        在視窗關閉前，檢查是否有未儲存的變更。
        """
        if self.controller.is_dirty:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Unsaved Changes", # 建議為這些文字也加入 language.py
                "You have unsaved changes. Do you want to save them before exiting?",
                QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel # 預設按鈕
            )

            if reply == QtWidgets.QMessageBox.Save:
                # 使用者選擇儲存
                log.debug("使用者選擇儲存並離開。")
                self.controller.file_io_handler.on_save_config_clicked()
                event.accept() # 同意關閉
            elif reply == QtWidgets.QMessageBox.Discard:
                # 使用者選擇不儲存
                log.debug("使用者選擇放棄變更並離開。")
                event.accept() # 同意關閉
            else: # reply == QtWidgets.QMessageBox.Cancel
                # 使用者選擇取消
                log.debug("使用者取消離開操作。")
                event.ignore() # 忽略關閉事件，視窗將保持開啟
        else:
            # 如果沒有未儲存的變更，則正常關閉
            event.accept()

        
class IconBrowserDialog(QtWidgets.QDialog):
    """
    一個用於瀏覽和選擇Maya內建圖示的獨立對話框。

    這個類別使用 QListWidget 的 IconMode 來預覽所有從 Maya ResourceManager
    中獲取的圖示，並提供了搜尋篩選功能。當使用者選擇一個圖示後，它會
    發出一個自訂信號 `icon_selected` 將結果傳回給主控制器。
    """
    icon_selected = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(IconBrowserDialog, self).__init__(parent)
        self.setWindowTitle(tr('icon_browser_title'))
        self.setGeometry(400, 400, 500, 600)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText(tr('icon_search_placeholder'))
        self.search_input.textChanged.connect(self.filter_icons)
        
        self.icon_list_widget = QtWidgets.QListWidget()
        self.icon_list_widget.setViewMode(QtWidgets.QListWidget.IconMode)
        self.icon_list_widget.setIconSize(QtCore.QSize(32, 32))
        self.icon_list_widget.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.icon_list_widget.itemDoubleClicked.connect(self.accept_selection)

        main_layout.addWidget(self.search_input)
        main_layout.addWidget(self.icon_list_widget)

        self.load_all_icons()

    def load_all_icons(self):
        """使用 cmds.resourceManager 獲取所有圖示並填充到列表中。"""
        log.info("正在載入Maya內建圖示...")
        all_icons = cmds.resourceManager(nameFilter="*.png")
        
        MAX_TEXT_LENGTH = 5

        for icon_name in sorted(all_icons):
            resource_path = f":/{icon_name}"
            
            display_text = icon_name
            if len(icon_name) > MAX_TEXT_LENGTH:
                display_text = icon_name[:MAX_TEXT_LENGTH] + "..."

            list_item = QtWidgets.QListWidgetItem(display_text)
            list_item.setIcon(QtGui.QIcon(resource_path))
            
            list_item.setData(QtCore.Qt.UserRole, icon_name)
            
            list_item.setToolTip(icon_name)
            
            self.icon_list_widget.addItem(list_item)
            
        log.info(f"圖示載入完成，共 {len(all_icons)} 個。")

    def filter_icons(self, text):
        """根據搜尋框的文字篩選顯示的圖示。"""
        for i in range(self.icon_list_widget.count()):
            item = self.icon_list_widget.item(i)
            full_item_name = item.data(QtCore.Qt.UserRole)
            is_match = text.lower() in full_item_name.lower()
            item.setHidden(not is_match)

    def accept_selection(self, item):
        """當使用者雙擊一個圖示時觸發。"""
        selected_icon_name = item.data(QtCore.Qt.UserRole)
        log.info(f"使用者選擇了圖示: {selected_icon_name}")
        self.icon_selected.emit(f":/{selected_icon_name}")
        self.accept()

class DraggableTreeWidget(QtWidgets.QTreeWidget):
    """
    一個繼承自 QTreeWidget 的自訂元件，增加了對複雜拖放邏輯的支援。
    它會分析拖放的具體位置，判斷使用者的意圖（排序、重新父級、設為選項框），
    然後發出自訂信號 `items_dropped` 通知 Controller 進行資料處理。
    """
    drop_event_completed = QtCore.Signal(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem, QtWidgets.QAbstractItemView.DropIndicatorPosition)
    empty_space_clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(DraggableTreeWidget, self).__init__(parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    # 覆寫 mousePressEvent 方法
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """
        覆寫滑鼠點擊事件，以精準偵測是否點擊在空白區域。
        """
        # 檢查滑鼠點擊的座標位置下，是否有一個 item
        item = self.itemAt(event.pos())
        
        # 如果 item 為 None，代表使用者點擊的是樹狀圖的空白處
        if not item:
            log.debug("DraggableTreeWidget: Detected click on empty space.")
            # 發射我們自訂的「點擊空白處」信號
            self.empty_space_clicked.emit()
            # 清除選取，確保視覺上的一致性
            self.clearSelection()
        
        # 最後，務必呼叫父類別的原始方法，確保點擊、選取等預設功能依然正常運作
        super(DraggableTreeWidget, self).mousePressEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent):
        """
        [新規則版] 在放下事件發生時，嚴格驗證操作是否符合所有結構原則。
        """
        target_item = self.itemAt(event.pos())
        indicator = self.dropIndicatorPosition()
        source_item = self.currentItem()
        if not source_item:
            event.ignore(); return

        # --- 驗證區 ---

        # [規則 4] 驗證：功能項目不能成為功能項目的子級
        if indicator == QtWidgets.QAbstractItemView.OnItem and target_item:
            if target_item.data(0, QtCore.Qt.UserRole): # 如果目標是功能項
                log.warning("操作被阻止：不能將項目拖曳為另一個功能項目的子級。")
                event.ignore(); return

        # [規則 5] 驗證：不能在父物件與其選項框之間插入任何項目
        # 情況 A：嘗試拖到一個父物件的「下方」
        if indicator == QtWidgets.QAbstractItemView.BelowItem and target_item:
            item_below = self.itemBelow(target_item)
            if item_below and item_below.parent() == target_item.parent():
                data_below = item_below.data(0, QtCore.Qt.UserRole)
                if data_below and data_below.is_option_box:
                    log.warning("操作被阻止：不能在父物件與其選項框之間插入項目。")
                    event.ignore(); return
        
        # 情況 B：嘗試拖到一個選項框的「上方」
        if indicator == QtWidgets.QAbstractItemView.AboveItem and target_item:
            target_data = target_item.data(0, QtCore.Qt.UserRole)
            if target_data and target_data.is_option_box:
                log.warning("操作被阻止：不能在父物件與其選項框之間插入項目。")
                event.ignore(); return

        # --- 驗證通過 ---
        super(DraggableTreeWidget, self).dropEvent(event)
        self.drop_event_completed.emit(source_item, target_item, indicator)
        event.accept()