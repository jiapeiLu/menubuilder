# menubuilder/core/decorators.py

import functools
from .logger import log

def preserve_ui_state(func):
    """
    一個裝飾器，用於在執行會刷新UI樹的操作前後，自動保存和還原其展開狀態。
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # 裝飾器應用在 Handler 上，所以 self 是 Handler 的實例
        # 我們需要透過 self.controller.ui 來存取 UI
        if not hasattr(self, 'controller') or not hasattr(self.controller, 'ui'):
            return func(self, *args, **kwargs)

        expansion_state = self.controller.ui.get_expansion_state()
        log.debug(f"裝飾器: 狀態已記錄。準備執行 '{func.__name__}'...")

        try:
            result = func(self, *args, **kwargs)
        finally:
            self.controller.ui.set_expansion_state(expansion_state)
            log.debug("裝飾器: UI狀態已還原。")
        
        return result
    return wrapper

def block_ui_signals(widget_name: str):
    """
    一個可傳參的裝飾器工廠，用於在執行函式期間暫時阻斷指定UI元件的信號。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'controller') or not hasattr(self.controller, 'ui'):
                return func(self, *args, **kwargs)

            widget_to_block = getattr(self.controller.ui, widget_name, None)
            
            if not widget_to_block:
                log.warning(f"在 block_ui_signals 中找不到名為 {widget_name} 的 UI 元件。")
                return func(self, *args, **kwargs)

            try:
                widget_to_block.blockSignals(True)
                log.debug(f"裝飾器: 已阻斷 {widget_name} 的信號。")
                result = func(self, *args, **kwargs)
            finally:
                widget_to_block.blockSignals(False)
                log.debug(f"裝飾器: 已恢復 {widget_name} 的信號。")
            
            return result
        return wrapper
    return decorator