# core/controller.py
from .logger import log  # 從我們建立的logger模組導入已經配置好的log實例

class MenuBuilderController:
    def __init__(self):
        log.info("MenuBuilderController 初始化開始...")
        # ... 其他初始化程式碼 ...
        log.info("MenuBuilderController 初始化完成。")

    def show_ui(self):
        log.info("顯示 Menubuilder UI。")
        try:
            # 顯示UI的程式碼
            # self.ui.show()
            pass
        except Exception as e:
            log.error(f"顯示UI時發生錯誤: {e}", exc_info=True) # exc_info=True 會記錄完整的錯誤堆疊