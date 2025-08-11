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

class MenuBuilderUI(QtWidgets.QMainWindow):
    """
    Menubuilder 的主 UI 視窗，扮演 MVC 架構中的視圖(View)角色。
    
    這個類別負責創建和佈局所有的UI元件，例如按鈕、列表、輸入框等。
    它接收來自 Controller 的指令來更新顯示，並在使用者操作時發出信號(signals)
    通知 Controller。它本身不包含任何業務邏輯。
    """
    def __init__(self, controller):
        """
        初始化 MenuBuilderUI 主視窗。

        Args:
            controller (MenuBuilderController): 控制器物件的實例，用於信號連接。
        """
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
        self.left_label = QtWidgets.QLabel("現有菜單結構 (Menu Configuration)")
        self.menu_tree_view = DraggableTreeWidget()
        self.menu_tree_view.setHeaderLabels(["菜單項 (Menu Item)", "路徑 (Path)"])
        self.menu_tree_view.setColumnWidth(0, 200)

        # 啟用自訂右鍵選單
        self.menu_tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        left_layout.addWidget(self.left_label)
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
        # [新增] 用於顯示當前腳本路徑的資訊列
        self.current_script_path_label = QtWidgets.QLineEdit()
        self.current_script_path_label.setReadOnly(True) # 設為唯讀，僅供顯示
        self.current_script_path_label.setStyleSheet("background-color: #2E2E2E; border: none;") # 美化一下外觀

        self.function_list = QtWidgets.QListWidget()
        file_parse_layout.addWidget(self.browse_button)
        file_parse_layout.addWidget(self.current_script_path_label) # [新增] 將資訊列加入佈局
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
        # [核心修改] 替換舊的 icon_layout
        # -----------------------------------------------------------------
        # -- Icon Group --
        icon_path_layout = QtWidgets.QHBoxLayout()
        self.icon_input = QtWidgets.QLineEdit()
        self.icon_input.setPlaceholderText("輸入路徑或點擊右側按鈕瀏覽...")
        
        # 新增兩個按鈕
        self.icon_browse_btn = QtWidgets.QPushButton("自訂...")
        self.icon_browse_btn.setToolTip("瀏覽本機的圖示檔案 (e.g., C:/icon.png)")
        self.icon_buildin_btn = QtWidgets.QPushButton("內建...")
        self.icon_buildin_btn.setToolTip("瀏覽Maya內建圖示 (e.g., :polyCube.png)")

        icon_path_layout.addWidget(self.icon_input)
        icon_path_layout.addWidget(self.icon_browse_btn)
        icon_path_layout.addWidget(self.icon_buildin_btn)
        
        # 預覽標籤
        self.icon_preview = QtWidgets.QLabel()
        self.icon_preview.setFixedSize(32, 32)
        self.icon_preview.setStyleSheet("border: 1px solid #555; background-color: #333; border-radius: 4px;")
        self.icon_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_preview.setText("無")
        
        # 預覽更新 訊息
        self.icon_input.textChanged.connect(self.update_icon_preview)
        # -----------------------------------------------------------------
        
        self.option_box_checkbox = QtWidgets.QCheckBox("作為選項框 (IsOptionBox)")
        self.option_box_checkbox.setEnabled(False)

        form_layout.addRow("菜單標籤 (Label):", self.label_input)
        form_layout.addRow("菜單路徑 (Path):", self.path_input)
        form_layout.addRow("排序順位 (Order):", self.order_input)
        # 將UI元件加入 Form Layout
        form_layout.addRow("圖示路徑 (Icon):", icon_path_layout)
        form_layout.addRow("預覽 (Preview):", self.icon_preview)
        
        form_layout.addRow(self.option_box_checkbox)

        self.attribute_box.setLayout(form_layout)
       

        # -- 操作按鈕 --
        self.add_update_button = QtWidgets.QPushButton("新增至結構")
        #self.delete_button = QtWidgets.QPushButton("從結構中刪除")
        self.save_button = QtWidgets.QPushButton("儲存設定檔")
        self.build_menus_button = QtWidgets.QPushButton("✨ 在Maya中產生/刷新菜單 (Build Menus)")

        # -- 組合右側所有元件 --
        right_layout.addWidget(self.input_tabs)
        right_layout.addWidget(self.attribute_box)
        right_layout.addWidget(self.add_update_button)
        #right_layout.addWidget(self.delete_button)
        right_layout.addStretch() # 將按鈕往上推
        right_layout.addWidget(self.save_button)
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
        """
        根據提供的資料列表，完整地重建左側的樹狀視圖。

        這個函式不依賴傳入列表的順序。它會動態地解析每個項目的
        `sub_menu_path` 來創建或查找父級節點，確保層級結構的正確性。
        同時，它會為特殊項目（如選項框）應用自訂的視覺樣式，並將
        `MenuItemData` 物件本身附加到對應的UI項目上以便後續使用。

        Args:
            items (List[MenuItemData]): 用於渲染UI樹的菜單項資料列表。
        """
        # 在重建前，阻擋信號，防止觸發不必要的 itemChanged 事件
        self.menu_tree_view.blockSignals(True)
        self.menu_tree_view.clear()
        self.item_map.clear()
        
        for item_data in items:
            # 對每一個項目，都從根節點開始，確保其父級路徑存在
            parent_ui_item = self.menu_tree_view.invisibleRootItem()
            
            if item_data.sub_menu_path:
                path_parts = item_data.sub_menu_path.split('/')
                full_path_key = ""
                for part in path_parts:
                    full_path_key = f"{full_path_key}/{part}" if full_path_key else part
                    
                    if full_path_key in self.item_map:
                        parent_ui_item = self.item_map[full_path_key]
                    else:
                        # 創建新的父級(文件夾)節點
                        new_parent = QtWidgets.QTreeWidgetItem(parent_ui_item, [part])
                        new_parent.setFlags(new_parent.flags() | QtCore.Qt.ItemIsEditable)
                        self.item_map[full_path_key] = new_parent
                        parent_ui_item = new_parent

            # --- [核心修改] 根據 is_option_box 決定顯示樣式 ---
            display_label = item_data.menu_label
            
            # 檢查當前項目是否為 Option Box
            if item_data.is_option_box:
                # 為標籤加上前綴，提供視覺提示
                display_label = f"(□) {item_data.menu_label}"
                
                # 找到它邏輯上的父項目 (列表中的上一個)
                # 這部分邏輯在Controller中處理，UI只負責顯示
                # 我們可以在這裡嘗試找到它在UI中的父級並進行縮排
                # 但更簡單的方式是讓Controller處理好順序和父子關係
                # 目前我們先只做視覺提示

            # 創建並附加真正的功能節點
            menu_qitem = QtWidgets.QTreeWidgetItem(parent_ui_item, [display_label])
            # 注意：功能節點本身不可直接在樹上編輯名稱
            menu_qitem.setData(0, QtCore.Qt.UserRole, item_data)
            
            # --- [核心修改] is_option_box ---
            if item_data.is_option_box:
                menu_qitem.setToolTip(0, f"此項目是一個選項框(Option Box)，\n隸屬於它上方的菜單項。")
                # 可以考慮改變顏色以示區分
                font = menu_qitem.font(0)
                font.setItalic(True)
                menu_qitem.setFont(0, font)
                menu_qitem.setForeground(0, QtGui.QColor("#A0A0A0"))
            
            # 將功能節點本身也加入 item_map，以便查找
            final_path = f"{item_data.sub_menu_path}/{item_data.menu_label}" if item_data.sub_menu_path else item_data.menu_label
            self.item_map[final_path] = menu_qitem

        # 重建完成後，解除信號阻擋
        self.menu_tree_view.blockSignals(False)
    
    def get_attributes_from_fields(self) -> MenuItemData:
        """
        從右側編輯器面板的所有輸入框中收集當前的值，並打包成一個新的
        MenuItemData 物件。

        Returns:
            MenuItemData: 一個包含了右側面板所有當前設定的新資料物件。
        """
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
            #is_dockable=self.dockable_checkbox.isChecked(),
            is_option_box=self.option_box_checkbox.isChecked(),
            function_str=function_string
            # module_path 可以考慮在選擇檔案時就存起來
        )
        return item_data
        
    def get_expansion_state(self) -> set:
        """[優化後] 遍歷樹並返回所有已展開項目的路徑集合。"""
        expanded_paths = set()
        iterator = QtWidgets.QTreeWidgetItemIterator(self.menu_tree_view)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                # 直接使用我們已有的輔助函式來獲取路徑，更高效、更準確
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
        """
        接收一個 MenuItemData 物件，並將其內容更新到右側的編輯器UI上。

        Args:
            data (MenuItemData): 要顯示在編輯器中的資料物件。
        """
        if not data:
            # 可以選擇清空所有欄位
            log.warning("傳入的 item_data 為空，無法填入欄位。")
            return

        # 填入所有對應的欄位
        self.label_input.setText(data.menu_label)
        self.path_input.setText(data.sub_menu_path)
        self.order_input.setValue(data.order)
        self.icon_input.setText(data.icon_path)
        #self.dockable_checkbox.setChecked(data.is_dockable)
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
        """
        當接收到 `customContextMenuRequested` 信號時，創建並顯示右鍵選單。

        選單的內容會根據使用者點擊的位置（是在項目上還是空白處）動態生成。

        Args:
            point (QtCore.QPoint): 使用者右鍵點擊的視窗座標。
        """
        menu = QtWidgets.QMenu(self)
        item = self.menu_tree_view.itemAt(point)

        if item:
            # --- 如果點擊在一個項目上 ---
            item_data = item.data(0, QtCore.Qt.UserRole)
            
            # [新增] 為所有項目（包括文件夾）增加重命名選項
            action_rename = menu.addAction("重新命名 (Rename)")
            # 連接到QTreeWidget的內建editItem方法，非常方便
            action_rename.triggered.connect(lambda: self.menu_tree_view.editItem(item))

            if item_data: # 這是個菜單項
                action_edit = menu.addAction("編輯此項目屬性 (Edit Properties)")
                action_edit.triggered.connect(
                    functools.partial(self.controller.on_tree_item_double_clicked, item, 0)
                )
            
            menu.addSeparator()

            path_for_actions = item_data.sub_menu_path if item_data else self.get_path_for_item(item)
            action_add_under = menu.addAction("在此路徑下新增項目...")
            action_add_under.triggered.connect(
                functools.partial(self.controller.on_context_add_under, path_for_actions)
            )

            # [核心修改] 刪除以下兩行
            # action_add_dockable = menu.addAction("在此路徑下新增可停靠項目...")
            # action_add_dockable.triggered.connect(...)

            menu.addSeparator()

            action_send_path = menu.addAction(f"傳送路徑 '{path_for_actions}' 至編輯器")
            action_send_path.triggered.connect(
                functools.partial(self.controller.on_context_send_path, path_for_actions)
            )
            
            action_delete = menu.addAction("刪除...")
            action_delete.triggered.connect(
                functools.partial(self.controller.on_context_delete, item)
            )

        else:
            # --- 如果點擊在空白處 ---
            action_add_root = menu.addAction("新增根級項目...")
            action_add_root.triggered.connect(
                functools.partial(self.controller.on_context_add_under, "")
            )

            # [核心修改] 刪除以下兩行
            # action_add_dockable_root = menu.addAction("新增根級可停靠項目...")
            # action_add_dockable_root.triggered.connect(...)

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
            # 如果路徑無效，QIcon會是null
            self.icon_preview.clear()
            self.icon_preview.setText("無效")
        else:
            # 從QIcon創建一個QPixmap並顯示在QLabel中
            pixmap = icon.pixmap(32, 32)
            self.icon_preview.setPixmap(pixmap)

    def set_item_highlight(self, item_to_highlight: QtWidgets.QTreeWidgetItem, bold: bool = True):
        """設定指定UI項目的高亮（粗體）狀態。"""
        if not item_to_highlight:
            return
        # --- 設定字體為粗體 (不變) ---
        font = item_to_highlight.font(0)
        font.setBold(bold)
        item_to_highlight.setFont(0, font)

        # --- [新增] 設定背景顏色 ---
        if bold:
            # 設定一個高亮的顏色 (這是一個中性偏藍的灰色，適合暗色主題)
            # 您可以隨意更換成您喜歡的任何顏色代碼
            highlight_color = QtGui.QColor("#34532D")
            item_to_highlight.setBackground(0, QtGui.QBrush(highlight_color))
        else:
            # 如果是取消高亮，則恢復預設背景 (透明)
            item_to_highlight.setBackground(0, QtGui.QBrush())

    def clear_all_highlights(self):
        """清除樹狀視圖中所有項目的高亮狀態，使其恢復正常字體。"""
        iterator = QtWidgets.QTreeWidgetItemIterator(self.menu_tree_view)
        while iterator.value():
            item = iterator.value()
            
            # 檢查並恢復字體
            font = item.font(0)
            if font.bold():
                font.setBold(False)
                item.setFont(0, font)

            # [新增] 檢查並恢復背景色
            # 獲取當前背景筆刷，如果它不是預設的透明樣式，就清除它
            if item.background(0).style() != QtCore.Qt.NoBrush:
                 item.setBackground(0, QtGui.QBrush())

            iterator += 1


class IconBrowserDialog(QtWidgets.QDialog):
    """
    一個用於瀏覽和選擇Maya內建圖示的獨立對話框。

    這個類別使用 QListWidget 的 IconMode 來預覽所有從 Maya ResourceManager
    中獲取的圖示，並提供了搜尋篩選功能。當使用者選擇一個圖示後，它會
    發出一個自訂信號 `icon_selected` 將結果傳回給主控制器。
    """
    
    icon_selected = QtCore.Signal(str) # 自訂信號，當使用者選擇圖示後發出

    def __init__(self, parent=None):
        super(IconBrowserDialog, self).__init__(parent)
        self.setWindowTitle("Maya Icon Browser")
        self.setGeometry(400, 400, 500, 600)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        
        # 搜尋框
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("搜尋圖示名稱 (例如: sphere)...")
        self.search_input.textChanged.connect(self.filter_icons)
        
        # 圖示列表
        self.icon_list_widget = QtWidgets.QListWidget()
        self.icon_list_widget.setViewMode(QtWidgets.QListWidget.IconMode) # 以圖示模式顯示
        self.icon_list_widget.setIconSize(QtCore.QSize(32, 32))
        self.icon_list_widget.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.icon_list_widget.itemDoubleClicked.connect(self.accept_selection)

        main_layout.addWidget(self.search_input)
        main_layout.addWidget(self.icon_list_widget)

        # 載入所有圖示
        self.load_all_icons()

    def load_all_icons(self):
        """使用 cmds.resourceManager 獲取所有圖示並填充到列表中。"""
        log.info("正在載入Maya內建圖示...")
        all_icons = cmds.resourceManager(nameFilter="*.png")
        
        # 定義顯示文字的最大長度
        MAX_TEXT_LENGTH = 5

        for icon_name in sorted(all_icons):
            resource_path = f":/{icon_name}"
            
            # [核心修改] 決定要顯示的文字
            display_text = icon_name
            if len(icon_name) > MAX_TEXT_LENGTH:
                display_text = icon_name[:MAX_TEXT_LENGTH] + "..."

            # 創建列表項，並設置顯示文字
            list_item = QtWidgets.QListWidgetItem(display_text)
            list_item.setIcon(QtGui.QIcon(resource_path))
            
            # 將完整的、未截斷的名稱儲存在 UserRole 中
            list_item.setData(QtCore.Qt.UserRole, icon_name)
            
            # Tooltip 依然顯示完整名稱，方便使用者查看
            list_item.setToolTip(icon_name)
            
            self.icon_list_widget.addItem(list_item)
            
        log.info(f"圖示載入完成，共 {len(all_icons)} 個。")

    def filter_icons(self, text):
        """根據搜尋框的文字篩選顯示的圖示。"""
        for i in range(self.icon_list_widget.count()):
            item = self.icon_list_widget.item(i)

            # [Bug修正] 從 UserRole 獲取完整的名稱來進行比對
            full_item_name = item.data(QtCore.Qt.UserRole)
            
            # 如果圖示名稱包含搜尋文字 (不分大小寫)，則顯示，否則隱藏
            is_match = text.lower() in full_item_name.lower()
            item.setHidden(not is_match)

    def accept_selection(self, item):
        """當使用者雙擊一個圖示時觸發。"""
        selected_icon_name = item.data(QtCore.Qt.UserRole)
        log.info(f"使用者選擇了圖示: {selected_icon_name}")
        # 發出自訂信號，將選擇的圖示名稱傳遞出去
        self.icon_selected.emit(f":/{selected_icon_name}")
        self.accept() # 關閉對話框


# [新增] 創建一個自訂的 QTreeWidget 子類別
class DraggableTreeWidget(QtWidgets.QTreeWidget):
    """
    一個繼承自 QTreeWidget 的自訂元件，增加了對複雜拖放邏輯的支援。
    它會分析拖放的具體位置，判斷使用者的意圖（排序、重新父級、設為選項框），
    然後發出自訂信號 `items_dropped` 通知 Controller 進行資料處理。
    """
    # 信號: source_item, target_item, drop_indicator_position
    drop_event_completed = QtCore.Signal(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem, QtWidgets.QAbstractItemView.DropIndicatorPosition)

    def __init__(self, parent=None):
        super(DraggableTreeWidget, self).__init__(parent)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event: QtGui.QDropEvent):
        """[最終版] 先執行預設的視覺移動，然後再發出包含完整上下文的信號。"""
        # 記錄拖放前的資訊
        source_item = self.currentItem()
        target_item = self.itemAt(event.pos())
        indicator = self.dropIndicatorPosition()

        if not source_item:
            event.ignore(); return

        # --- [核心修正] 新增對目標的驗證邏輯 ---
        if target_item:
            target_data = target_item.data(0, QtCore.Qt.UserRole)
            # 規則：如果目標是一個選項框，並且使用者試圖將項目拖放到它“之上”(OnItem)
            # 那麼這次操作是無效的。
            if (target_data and target_data.is_option_box and 
                indicator == QtWidgets.QAbstractItemView.OnItem):
                
                log.warning("非法操作：不能將項目拖放到一個已存在的選項框之上。")
                event.ignore() # 忽略並取消這次拖放
                return
        # --- 驗證結束 ---

        # 1. 讓Qt先完成所有視覺上的移動
        super(DraggableTreeWidget, self).dropEvent(event)
        
        # 2. 發出信號，將所有必要的上下文資訊傳遞給Controller
        self.drop_event_completed.emit(source_item, target_item, indicator)
        
        event.accept()