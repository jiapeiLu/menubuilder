from PySide2 import QtWidgets
from typing import List
from .translator import tr
from .logger import log
from maya import cmds, mel

class ShelfImportDialog(QtWidgets.QDialog):
    """
    一個用於選擇要匯入的 Maya Shelves 的獨立對話框。
    """
    def __init__(self, parent=None):
        super(ShelfImportDialog, self).__init__(parent)
        self.setWindowTitle(tr('shelf_import_dialog_title'))
        self.setMinimumWidth(350)
        self.setModal(True) 

        # --- UI 元件 ---
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(tr('shelf_import_dialog_label'))
        
        self.shelf_list_widget = QtWidgets.QListWidget()
        self.shelf_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.button_layout = QtWidgets.QHBoxLayout()
        self.import_button = QtWidgets.QPushButton(tr('shelf_import_dialog_import_button'))
        self.cancel_button = QtWidgets.QPushButton(tr('shelf_import_dialog_cancel_button'))
        
        # --- 佈局 ---
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.import_button)
        self.button_layout.addWidget(self.cancel_button)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.shelf_list_widget)
        self.main_layout.addLayout(self.button_layout)

        # --- 信號連接 ---
        self.import_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # [核心修改] 在初始化時，自動載入所有 Shelf 名稱
        self.populate_shelves()

    def populate_shelves(self):
        """
        [新增] 查詢 Maya 環境中所有的 Shelf 並填充到列表中。
        """
        # Maya 的頂層 Shelf UI 元件有一個全域 MEL 變數 $gShelfTopLevel
        # 這是目前最可靠的獲取所有 Shelf 標籤頁的方式
        try:
            shelf_toplevel = mel.eval("global string $gShelfTopLevel; $temp = $gShelfTopLevel;")
            if shelf_toplevel:
                # 查詢該 UI 元件下的所有子元件 (也就是每個 Shelf 標籤頁)
                all_shelves = cmds.shelfTabLayout(shelf_toplevel, query=True, tabLabel=True)
                if all_shelves:
                    self.shelf_list_widget.addItems(all_shelves)
        except Exception as e:
            # 如果出錯，在列表中顯示錯誤訊息
            self.shelf_list_widget.addItem("Error loading shelves.")
            log.error(f"查詢 Maya Shelves 時出錯: {e}", exc_info=True)

    def get_selected_shelves(self) -> List[str]:
        """
        獲取使用者在列表中選擇的所有 Shelf 的名稱。
        """
        selected_items = self.shelf_list_widget.selectedItems()
        return [item.text() for item in selected_items]