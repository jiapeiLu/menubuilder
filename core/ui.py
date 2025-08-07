# core/ui.py
from PySide2 import QtWidgets, QtCore, QtGui
from typing import List
from .dto import MenuItemData
from .logger import log

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
        # 啟用Qt內建拖放功能
        self.menu_tree_view.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.menu_tree_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.menu_tree_view.setDragEnabled(True)
        self.menu_tree_view.setAcceptDrops(True)
        self.menu_tree_view.setDropIndicatorShown(True)
        # 啟用自訂右鍵選單
        self.menu_tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

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
        #self.save_button = QtWidgets.QPushButton("儲存設定檔")
        self.build_menus_button = QtWidgets.QPushButton("✨ 在Maya中產生/刷新菜單 (Build Menus)")

        # -- 組合右側所有元件 --
        right_layout.addWidget(self.input_tabs)
        right_layout.addWidget(self.attribute_box)
        right_layout.addWidget(self.add_update_button)
        right_layout.addWidget(self.delete_button)
        right_layout.addStretch() # 將按鈕往上推
        #right_layout.addWidget(self.save_button)
        right_layout.addWidget(self.build_menus_button)


        # --- 組合左右佈局 ---
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addWidget(right_widget, stretch=1)
        
        # [新增] 創建頂部菜單欄
        # =================================================
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("檔案(File)")

        # 創建菜單中的動作 (Action)
        self.open_action = file_menu.addAction("開啟設定檔 (Open)...")
        self.merge_action = file_menu.addAction("合併設定檔 (Merge)...")
        self.save_action = file_menu.addAction("存檔 (Save )...")
        self.save_as_action = file_menu.addAction("另存新檔 (Save As)...")
        
        file_menu.addSeparator() # 加入分隔線
        
        self.exit_action = file_menu.addAction("離開 (Exit)")
        # =================================================
        
        
    def populate_menu_tree(self, items: List[MenuItemData]):
        self.menu_tree_view.clear()
        self.item_map.clear() # item_map 仍然用來快速查找父節點 (key: path, value: QTreeWidgetItem)
        
        # [核心修正] 移除這行 -> items.sort(key=lambda x: x.sub_menu_path)
        
        for item_data in items: # 直接遍歷原始順序的列表
            parent_ui_item = self.menu_tree_view.invisibleRootItem()
            
            # 建立父級路徑
            if item_data.sub_menu_path:
                path_parts = item_data.sub_menu_path.split('/')
                full_path_key = ""
                for part in path_parts:
                    full_path_key = f"{full_path_key}/{part}" if full_path_key else part
                    # 查找或創建父級UI節點
                    if full_path_key in self.item_map:
                        parent_ui_item = self.item_map[full_path_key]
                    else:
                        new_parent = QtWidgets.QTreeWidgetItem(parent_ui_item, [part])
                        new_parent.setFlags(new_parent.flags() | QtCore.Qt.ItemIsEditable) # <-- [新增] 讓文件夾可編輯
                        self.item_map[full_path_key] = new_parent
                        parent_ui_item = new_parent

            # 創建並附加真正的功能節點
            menu_qitem = QtWidgets.QTreeWidgetItem(parent_ui_item, [item_data.menu_label])
            # 將 MenuItemData 物件附加到 UI 項目上，以便後續掃描
            menu_qitem.setData(0, QtCore.Qt.UserRole, item_data)
    
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
        
    def get_ordered_data_from_tree(self) -> List[MenuItemData]:
        """
        公開方法：從樹狀視圖的根開始，遞迴掃描所有項目，
        並返回一個完全按照UI顯示順序排序、且路徑已更新的 MenuItemData 列表。
        """
        log.info("從UI樹狀視圖掃描並生成有序的資料列表...")
        ordered_list = []
        # 從看不見的根節點開始，初始路徑為空字串 ""
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
        # childCount() 和 child(i) 會自然地按照從上到下的視覺順序遍歷
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            
            # 從UI項目中取回我們之前用 setData 儲存的 MenuItemData 物件
            item_data = child_item.data(0, QtCore.Qt.UserRole)
            
            # 取得當前項目的顯示名稱 (它可能是菜單項的標籤，也可能是文件夾的名稱)
            current_item_text = child_item.text(0)
            
            # 組合出當前這個UI項目的完整路徑
            # 如果父路徑為空，則當前路徑就是它自己的名字；否則進行拼接
            current_path = f"{parent_path}/{current_item_text}" if parent_path else current_item_text
            
            if item_data:
                # [核心] 如果這個UI項目是一個真正的菜單項 (存有我們的data)
                
                # 1. 更新它的 sub_menu_path，以反映它在UI中被拖放後的新位置
                item_data.sub_menu_path = parent_path
                
                # 2. 將更新後的資料物件加入到結果列表中
                ordered_list.append(item_data)

            # 繼續遞迴深入下一層，不論當前節點是文件夾還是菜單項，
            # 只要它有子節點，就繼續遍歷。
            if child_item.childCount() > 0:
                # 當遞迴進入下一層時，當前項目的路徑就變成了子項目的父路徑
                # 注意：這裡我們傳遞的是 current_path，這是純粹由UI結構決定的路徑
                # 這一步是為了處理那些純粹作為文件夾，自身不帶 MenuItemData 的節點
                # 但我們的邏輯中，文件夾和菜單項的路徑更新方式是一樣的，所以可以簡化
                # 我們需要找到代表這個文件夾的 path
                
                # 修正：子項目的父路徑就是當前項目的路徑
                # 如果當前是個菜單項，其子項目的父路徑應為其自身的sub_menu_path + label
                # 如果當前是個文件夾，其子項目的父路徑應為其自身的路徑
                # 最簡單的方式是直接使用上面組合好的 current_path
                self._recursive_tree_walk(child_item, current_path, ordered_list)
                
    def set_expansion_state(self, expanded_paths: set):
        """根據提供的路徑集合，展開對應的項目。"""
        if not expanded_paths:
            return
        
        for path, item in self.item_map.items():
            if path in expanded_paths:
                item.setExpanded(True)        

    def set_attributes_to_fields(self, data: MenuItemData):
        """接收一個 MenuItemData 物件，並將其內容更新到右側的編輯器UI上。"""
        if not data:
            # 可以選擇清空所有欄位
            log.warning("傳入的 item_data 為空，無法填入欄位。")
            return

        # 填入所有對應的欄位
        self.label_input.setText(data.menu_label)
        self.path_input.setText(data.sub_menu_path)
        self.order_input.setValue(data.order)
        self.icon_input.setText(data.icon_path)
        self.dockable_checkbox.setChecked(data.is_dockable)
        self.option_box_checkbox.setChecked(data.is_option_box)

        # 將指令填入「手動輸入」框，並切換到該分頁，方便查看和編輯
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
        """當使用者在樹狀視圖上右鍵點擊時，創建並顯示選單。"""
        menu = QtWidgets.QMenu(self)
        
        # 取得滑鼠點擊位置的項目
        item = self.menu_tree_view.itemAt(point)
        
        if item:
            # --- 如果點擊在一個項目上 ---
            item_data = item.data(0, QtCore.Qt.UserRole)
            item_path = self.get_path_for_item(item)

            # 根據點擊的是「文件夾」還是「菜單項」來決定顯示的內容
            if item_data: # 這是個菜單項
                action_edit = menu.addAction("編輯此項目 (Edit)")
                action_edit.triggered.connect(lambda: self.controller.on_tree_item_double_clicked(item, 0))
            
            action_add_under = menu.addAction("在此路徑下新增項目(New)")
            action_send_path = menu.addAction(f"傳送路徑 '{item_data.sub_menu_path if item_data else item_path}' 至編輯器")
            menu.addSeparator()
            action_delete = menu.addAction("刪除...")

            # 連接信號到Controller
            # 使用 lambda 來傳遞當前點擊的項目或路徑
            path_to_send = item_data.sub_menu_path if item_data else item_path
            action_send_path.triggered.connect(lambda: self.controller.on_context_send_path(path_to_send))
            action_add_under.triggered.connect(lambda: self.controller.on_context_add_under(path_to_send))
            action_delete.triggered.connect(lambda: self.controller.on_context_delete(item))

        else:
            # --- 如果點擊在空白處 ---
            action_add_root = menu.addAction("新增根級菜單...")
            action_add_root.triggered.connect(lambda: self.controller.on_context_add_under(""))

        # 在滑鼠的位置顯示選單
        menu.exec_(self.menu_tree_view.mapToGlobal(point))       