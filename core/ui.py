# core/ui.py
from PySide2 import QtWidgets, QtCore, QtGui
from typing import List
from .dto import MenuItemData

class MenuBuilderUI(QtWidgets.QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Menu Builder v1.0")
        self.setGeometry(300, 300, 1000, 700)
        
        # 儲存 QTreeWidgetItems 以便查找
        self.item_map = {}

        self._init_ui()

    def _init_ui(self):
        """初始化UI元件和佈局。"""
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        
        # --- 主水平佈局 (左側 vs 右側) ---
        main_layout = QtWidgets.QHBoxLayout(main_widget)

        # --- 左側: 現有菜單結構 ---
        left_layout = QtWidgets.QVBoxLayout()
        left_label = QtWidgets.QLabel("現有菜單結構 (Menu Configuration)")
        self.menu_tree_view = QtWidgets.QTreeWidget()
        self.menu_tree_view.setHeaderLabels(["菜單項 (Menu Item)", "路徑 (Path)"])
        self.menu_tree_view.setColumnWidth(0, 200)
        
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.menu_tree_view)
        # (按鈕暫時先不加，或先禁用)

        # --- 右側: 編輯器 ---
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)

        # -- Tab Widget for input method --
        self.input_tabs = QtWidgets.QTabWidget()
        file_parse_widget = QtWidgets.QWidget()
        manual_input_widget = QtWidgets.QWidget()

        self.input_tabs.addTab(file_parse_widget, "從檔案解析")
        self.input_tabs.addTab(manual_input_widget, "手動輸入指令")

        # -- Tab 1: Parse from File Layout --
        file_parse_layout = QtWidgets.QVBoxLayout(file_parse_widget)
        # ... (Add browse button and function list here)
        self.browse_button = QtWidgets.QPushButton("瀏覽腳本檔案...")
        self.function_list = QtWidgets.QListWidget()
        file_parse_layout.addWidget(self.browse_button)
        file_parse_layout.addWidget(self.function_list)

        # -- Tab 2: Manual Input Layout --
        manual_input_layout = QtWidgets.QVBoxLayout(manual_input_widget)
        self.manual_cmd_input = QtWidgets.QTextEdit()
        self.manual_cmd_input.setPlaceholderText("請在此輸入完整的Python或MEL指令...")
        manual_input_layout.addWidget(self.manual_cmd_input)

        # -- Attribute Editor Layout (使用 QFormLayout 更整齊) --
        self.attribute_box = QtWidgets.QGroupBox("屬性編輯器")
        form_layout = QtWidgets.QFormLayout()

        self.label_input = QtWidgets.QLineEdit()
        self.path_input = QtWidgets.QLineEdit()
        self.path_input.setPlaceholderText("例如: Tools/Modeling")
        self.order_input = QtWidgets.QSpinBox()
        self.order_input.setRange(0, 999)
        self.icon_input = QtWidgets.QLineEdit() # 之後會加上瀏覽按鈕
        self.dockable_checkbox = QtWidgets.QCheckBox("可停靠介面 (IsDockableUI)")
        self.option_box_checkbox = QtWidgets.QCheckBox("作為選項框 (IsOptionBox)")

        form_layout.addRow("菜單標籤 (Label):", self.label_input)
        form_layout.addRow("菜單路徑 (Path):", self.path_input)
        form_layout.addRow("排序順位 (Order):", self.order_input)
        form_layout.addRow("圖示 (Icon):", self.icon_input)
        form_layout.addRow(self.dockable_checkbox)
        form_layout.addRow(self.option_box_checkbox)

        self.attribute_box.setLayout(form_layout)

        # -- 操作按鈕 --
        self.add_update_button = QtWidgets.QPushButton("新增至結構")
        self.delete_button = QtWidgets.QPushButton("從結構中刪除")
        self.save_button = QtWidgets.QPushButton("儲存設定檔")

        # -- 組合右側所有元件 --
        right_layout.addWidget(self.input_tabs)
        right_layout.addWidget(self.attribute_box)
        right_layout.addWidget(self.add_update_button)
        right_layout.addWidget(self.delete_button)
        right_layout.addStretch() # 將按鈕往上推
        right_layout.addWidget(self.save_button)


        # --- 組合左右佈局 ---
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addWidget(right_widget, stretch=1)
        
    def populate_menu_tree(self, items: List[MenuItemData]):
        """用載入的資料填充左側的樹狀視圖。"""
        self.menu_tree_view.clear()
        self.item_map.clear()
        
        # 為了能建立層級，先按路徑排序
        items.sort(key=lambda x: x.sub_menu_path)
        
        for item in items:
            path_parts = item.sub_menu_path.split('/')
            parent_item = self.menu_tree_view.invisibleRootItem()

            # 遞迴查找或創建父節點
            current_path = ""
            for part in path_parts:
                if not part: continue
                current_path = f"{current_path}/{part}" if current_path else part
                
                found_item = self.item_map.get(current_path)
                if found_item:
                    parent_item = found_item
                else:
                    new_parent_item = QtWidgets.QTreeWidgetItem(parent_item, [part])
                    self.item_map[current_path] = new_parent_item
                    parent_item = new_parent_item
            
            # 創建最終的菜單項
            menu_qitem = QtWidgets.QTreeWidgetItem(parent_item, [item.menu_label, item.sub_menu_path])
            if item.icon_path:
                menu_qitem.setIcon(0, QtGui.QIcon(item.icon_path))
    
    def get_attributes_from_fields(self) -> MenuItemData:
        """從右側面板的所有輸入框中收集資料，並返回一個 MenuItemData 物件。"""
        
        # 判斷指令來源：是從函式列表選擇，還是手動輸入
        # Tab 0: 從檔案解析, Tab 1: 手動輸入
        function_string = ""
        if self.input_tabs.currentIndex() == 0:
            selected_func_item = self.function_list.currentItem()
            if selected_func_item:
                # 這裡可以設計得更完善，比如把完整的導入和呼叫語法也組合進去
                function_string = selected_func_item.text()
        else: # 手動輸入
            function_string = self.manual_cmd_input.toPlainText()

        # 創建 DTO 物件並填充資料
        item_data = MenuItemData(
            menu_label=self.label_input.text(),
            sub_menu_path=self.path_input.text(),
            order=self.order_input.value(),
            icon_path=self.icon_input.text(),
            is_dockable=self.dockable_checkbox.isChecked(),
            is_option_box=self.option_box_checkbox.isChecked(),
            function_str=function_string
            # module_path 可以考慮在選擇檔案時就存起來
        )
        return item_data
        
    def get_expansion_state(self) -> set:
        """遍歷樹並返回所有已展開項目的路徑集合。"""
        expanded_paths = set()
        iterator = QtWidgets.QTreeWidgetItemIterator(self.menu_tree_view)
        while iterator.value():
            item = iterator.value()
            # 我們用 item_map 中的 key (路徑) 作為唯一識別碼
            # 檢查 item 是否在 self.item_map 的值中
            for path, mapped_item in self.item_map.items():
                if item == mapped_item and item.isExpanded():
                    expanded_paths.add(path)
                    break
            iterator += 1
        return expanded_paths

    def set_expansion_state(self, expanded_paths: set):
        """根據提供的路徑集合，展開對應的項目。"""
        if not expanded_paths:
            return
        
        for path, item in self.item_map.items():
            if path in expanded_paths:
                item.setExpanded(True)        