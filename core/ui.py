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
        right_layout = QtWidgets.QVBoxLayout()
        right_label = QtWidgets.QLabel("腳本檢視器 & 編輯器 (Inspector & Editor)")
        
        # ... 這裡將會是右側的所有輸入框和按鈕 ...
        # ... 在 Phase 1，我們可以先放一個佔位的 Label ...
        placeholder_editor = QtWidgets.QLabel("編輯器區域將在後續階段完成")
        placeholder_editor.setAlignment(QtCore.Qt.AlignCenter)
        placeholder_editor.setStyleSheet("border: 1px solid gray;")

        right_layout.addWidget(right_label)
        right_layout.addWidget(placeholder_editor)


        # --- 組合左右佈局 ---
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=1)
        
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