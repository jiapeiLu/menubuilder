# ui.py

"""
Menubuilder - User Interface Module (View)

這個模組是 MVC 架構中的「視圖(View)」層。

它包含了所有使用者介面的定義，使用 PySide2 框架編寫。
主要包含 `MenuBuilderUI` (主視窗) 和 `IconBrowserDialog` (圖示瀏覽器)
等類別。它的職責是呈現資料和佈局，並在使用者操作時發出信號(signals)
給 Controller。它本身不包含任何業務邏輯。
"""
from PySide2 import QtWidgets, QtCore, QtGui
from typing import List
from .dto import MenuItemData
from .logger import log
import maya.cmds as cmds
import functools

from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui

from menubuilder import __version__

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
        if parent is None:
            parent = get_maya_main_window()
        super(MenuBuilderUI, self).__init__(parent)

        self.controller = controller
        self.setWindowTitle(f"Menu Builder v{__version__}")
        self.setGeometry(300, 300, 800, 700)
        QtWidgets.QApplication.instance().installEventFilter(self)
        # 儲存 QTreeWidgetItems 以便查找
        self.item_map = {}

        self._init_ui()

    def _init_ui(self):
        """初始化UI元件和佈局。"""
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        
        top_level_layout = QtWidgets.QVBoxLayout(main_widget)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        top_level_layout.addWidget(splitter)

        left_container_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_container_widget)

        self.left_label = QtWidgets.QLabel("現有菜單結構 (Menu Configuration)")
        self.menu_tree_view = DraggableTreeWidget()
        self.menu_tree_view.setHeaderLabels(["菜單結構 (Menu Structure)"])
        self.menu_tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        left_layout.addWidget(self.left_label)
        left_layout.addWidget(self.menu_tree_view)

        right_container_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_container_widget)

        self.input_tabs = QtWidgets.QTabWidget()
        file_parse_widget = QtWidgets.QWidget()
        manual_input_widget = QtWidgets.QWidget()

        self.input_tabs.addTab(file_parse_widget, "從檔案解析")
        self.input_tabs.addTab(manual_input_widget, "手動輸入指令")

        file_parse_layout = QtWidgets.QVBoxLayout(file_parse_widget)
        self.browse_button = QtWidgets.QPushButton("瀏覽腳本檔案...")
        self.current_script_path_label = QtWidgets.QLineEdit()
        self.current_script_path_label.setReadOnly(True)
        self.current_script_path_label.setStyleSheet("background-color: #2E2E2E; border: none;")

        self.function_list = QtWidgets.QListWidget()
        file_parse_layout.addWidget(self.browse_button)
        file_parse_layout.addWidget(self.current_script_path_label)
        file_parse_layout.addWidget(self.function_list)

        # -- Tab 2: Manual Input Layout --
        manual_input_layout = QtWidgets.QVBoxLayout(manual_input_widget)
        
        # --- [新增] 指令類型選擇 ---
        # -----------------------------------------------------------------
        self.python_radio = QtWidgets.QRadioButton("Python")
        self.mel_radio = QtWidgets.QRadioButton("MEL")
        self.python_radio.setChecked(True) # 預設選中 Python
        
        # 使用 QButtonGroup 確保互斥
        self.command_type_group = QtWidgets.QButtonGroup()
        self.command_type_group.addButton(self.python_radio)
        self.command_type_group.addButton(self.mel_radio)

        command_type_layout = QtWidgets.QHBoxLayout()
        command_type_layout.addWidget(QtWidgets.QLabel("指令類型 (Type):"))
        command_type_layout.addWidget(self.python_radio)
        command_type_layout.addWidget(self.mel_radio)
        command_type_layout.addStretch()
        # -----------------------------------------------------------------

        self.manual_cmd_input = QtWidgets.QTextEdit()
        self.manual_cmd_input.setPlaceholderText("請在此輸入指令，並選取對應Python或mel語言...")
        self.test_run_button = QtWidgets.QPushButton("測試執行") 

        manual_input_layout.addLayout(command_type_layout) 
        manual_input_layout.addWidget(self.manual_cmd_input)
        manual_input_layout.addWidget(self.test_run_button) 

        self.attribute_box = QtWidgets.QGroupBox("屬性編輯器")
        form_layout = QtWidgets.QFormLayout()

        self.label_input = QtWidgets.QLineEdit()
        self.path_input = QtWidgets.QLineEdit()
        self.path_input.setPlaceholderText("例如: Tools/Modeling")
        
        icon_path_layout = QtWidgets.QHBoxLayout()
        self.icon_input = QtWidgets.QLineEdit()
        self.icon_input.setPlaceholderText("輸入路徑或點擊右側按鈕瀏覽...")
        
        self.icon_browse_btn = QtWidgets.QPushButton("自訂...")
        self.icon_browse_btn.setToolTip("瀏覽本機的圖示檔案 (e.g., C:/icon.png)")
        self.icon_buildin_btn = QtWidgets.QPushButton("內建...")
        self.icon_buildin_btn.setToolTip("瀏覽Maya內建圖示 (e.g., :polyCube.png)")

        icon_path_layout.addWidget(self.icon_input)
        icon_path_layout.addWidget(self.icon_browse_btn)
        icon_path_layout.addWidget(self.icon_buildin_btn)
        
        self.icon_preview = QtWidgets.QLabel()
        self.icon_preview.setFixedSize(32, 32)
        self.icon_preview.setStyleSheet("border: 1px solid #555; background-color: #333; border-radius: 4px;")
        self.icon_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_preview.setText("無")
        
        self.icon_input.textChanged.connect(self.update_icon_preview)

        form_layout.addRow("菜單標籤 (Label):", self.label_input)
        form_layout.addRow("菜單路徑 (Path):", self.path_input)
        form_layout.addRow("圖示路徑 (Icon):", icon_path_layout)
        form_layout.addRow("預覽 (Preview):", self.icon_preview)

        self.attribute_box.setLayout(form_layout)
       
        self.add_update_button = QtWidgets.QPushButton("新增至結構")
        self.save_button = QtWidgets.QPushButton("儲存設定檔")
        self.build_menus_button = QtWidgets.QPushButton("✨ 在Maya中產生/刷新菜單 (Build Menus)")

        right_layout.addWidget(self.input_tabs)
        right_layout.addWidget(self.attribute_box)
        right_layout.addWidget(self.add_update_button)
        right_layout.addStretch()
        right_layout.addWidget(self.save_button)
        right_layout.addWidget(self.build_menus_button)

        splitter.addWidget(left_container_widget)
        splitter.addWidget(right_container_widget)
        
        splitter.setSizes([350, 450]) 

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("檔案(File)")

        self.open_action = file_menu.addAction("開啟設定檔 (Open)...")
        self.merge_action = file_menu.addAction("合併設定檔 (Merge)...")
        self.save_action = file_menu.addAction("存檔 (Save )...")
        self.save_as_action = file_menu.addAction("另存新檔 (Save As)...")
        
        file_menu.addSeparator()
        
        self.exit_action = file_menu.addAction("離開 (Exit)")

        help_menu = menu_bar.addMenu("幫助(Help)")
        
        self.about_action = help_menu.addAction("關於 (About)")
        self.github_action = help_menu.addAction("在 GitHub 上查看...")
        
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
                display_label = "──────────"
            elif item_data.is_option_box:
                display_label = f"(□) {item_data.menu_label}"

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
                menu_qitem.setToolTip(0, f"此項目是一個選項框(Option Box)，\n隸屬於它上方的菜單項。")
                font = menu_qitem.font(0)
                font.setItalic(True)
                menu_qitem.setFont(0, font)
                menu_qitem.setForeground(0, QtGui.QColor("#BF6969"))

            final_path = f"{item_data.sub_menu_path}/{item_data.menu_label}" if item_data.sub_menu_path else item_data.menu_label
            self.item_map[final_path] = menu_qitem

        #self.set_item_highlight(self.controller.current_edit_item, bold=True)

        self.menu_tree_view.blockSignals(False)
    
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
            sub_menu_path=self.path_input.text(),
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
        self.path_input.setText(data.sub_menu_path)
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
        [微調版] 允許在分隔線上新增項目。
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
            if item_data and not item_data.is_divider: # 只有功能項可以被操作為選項框
                action_toggle_option_box = QtWidgets.QAction()
                if item_data.is_option_box:
                    action_toggle_option_box.setText("取消選項框 (Unset as Option Box)")
                    action_toggle_option_box.setEnabled(True)
                else:
                    action_toggle_option_box.setText("設為選項框 (Set as Option Box)")
                    is_valid = True
                    if is_parent_item: is_valid = False
                    else:
                        item_above = self.menu_tree_view.itemAbove(item)
                        if not item_above or item.parent() != item_above.parent(): is_valid = False
                        else:
                            data_above = item_above.data(0, QtCore.Qt.UserRole)
                            if not data_above or data_above.is_option_box: is_valid = False
                    action_toggle_option_box.setEnabled(is_valid)
                action_toggle_option_box.triggered.connect(functools.partial(self.controller.on_context_toggle_option_box, item))
                menu.addAction(action_toggle_option_box)

            action_add_under = menu.addAction("新增項目...")
            action_add_separator = menu.addAction("新增分隔線")

            # 父物件下方不能插入任何東西
            if is_parent_item:
                action_add_under.setEnabled(False)
                action_add_separator.setEnabled(False)
            
            is_folder = not item_data
            # 資料夾內部不能插入分隔線
            if is_folder:
                action_add_separator.setEnabled(False)

            # 將路徑資訊傳遞給新增操作
            action_add_under.triggered.connect(functools.partial(self.controller.on_context_add_under, path_for_actions))
            action_add_separator.triggered.connect(functools.partial(self.controller.on_context_add_separator, item))
            menu.addSeparator()

            # --- 輔助與破壞性群組 ---
            if not (item_data and item_data.is_divider): # 分隔線沒有路徑可傳送
                menu.addAction(f"傳送路徑 '{path_for_actions}' 至編輯器",
                               functools.partial(self.controller.on_context_send_path, path_for_actions))
                menu.addSeparator()
            
            action_delete = menu.addAction("刪除...")
            if is_parent_item:
                action_delete.setText("刪除主項與選項框...")
            action_delete.triggered.connect(functools.partial(self.controller.on_context_delete, item))
        else:
            # --- 情況三：點擊空白處 ---
            menu.addAction("新增根級項目...", functools.partial(self.controller.on_context_add_under, ""))

        menu.exec_(self.menu_tree_view.mapToGlobal(point))

    def update_tree_view_title(self, filename: str):
        """更新左側樹狀視圖的標題以顯示當前檔名。"""
        if filename:
            self.left_label.setText(f"現有菜單結構 - {filename}.json")
        else:
            self.left_label.setText("現有菜單結構 (Menu Configuration)")

    def update_icon_preview(self, path: str):
        """
        當圖示路徑輸入框的文字改變時，即時更新預覽區域的圖片。

        Args:
            path (str): 輸入框中當前的文字（圖示路徑）。
        """
        if not path:
            self.icon_preview.clear()
            self.icon_preview.setText("無")
            return

        icon = QtGui.QIcon(path)
        if icon.isNull():
            self.icon_preview.clear()
            self.icon_preview.setText("無效")
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

        if bold:
            highlight_color = QtGui.QColor("#34532D")
            item_to_highlight.setBackground(0, QtGui.QBrush(highlight_color))
        else:
            item_to_highlight.setBackground(0, QtGui.QBrush())

    def clear_all_highlights(self):
        """清除樹狀視圖中所有項目的高亮狀態，使其恢復正常字體。"""
        iterator = QtWidgets.QTreeWidgetItemIterator(self.menu_tree_view)
        while iterator.value():
            item = iterator.value()
            font = item.font(0)
            if font.bold():
                font.setBold(False)
                item.setFont(0, font)
            if item.background(0).style() != QtCore.Qt.NoBrush:
                 item.setBackground(0, QtGui.QBrush())
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
                self.controller.on_cancel_edit()
                # 返回 True，代表我們已經處理了這個事件，它不需要再繼續傳遞
                return True
        
        # 對於所有其他不關心的事件，把它們交還給 Qt 繼續進行預設的處理
        return super(MenuBuilderUI, self).eventFilter(watched_object, event)

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
        self.setWindowTitle("Maya Icon Browser")
        self.setGeometry(400, 400, 500, 600)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("搜尋圖示名稱 (例如: sphere)...")
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

    def __init__(self, parent=None):
        super(DraggableTreeWidget, self).__init__(parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

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