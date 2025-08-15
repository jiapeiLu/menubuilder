"""
Menubuilder - Main Package Entry Point

這是 menubuilder 套件的主入口點。

它提供了兩個供外部呼叫的核心函式：
- show(): 用於顯示工具的主UI介面，並使用單例模式確保視窗唯一。
- reload_all(): 一個智慧的重載函式，用於在開發過程中安全地重載
  所有相關的模組，避免重啟Maya。
"""
import importlib
import sys
import logging

__version__ = "1.1.0"
__author__ = "Jiapei Lu"

# 獲取一個logger實例，即使core.logger未載入也能安全使用
log = logging.getLogger('menubuilder_launcher')

# --- 全域實例管理 ---
# 用於儲存 MenuBuilderController 的單一實例
instance = None

def reload_all():
    """
    一個智慧的重載函式，會找到並重載所有 menubuilder 相關的模組。
    """
    global instance
    
    # 1. 在重載前，先安全地清理掉舊的UI和實例
    if instance:
        try:
            log.info("正在清理舊的 Menubuilder UI 實例...")
            instance.ui.clean_up() 
            instance.ui.close()
            instance.ui.deleteLater()
        except Exception as e:
            log.error(f"清理舊UI時發生錯誤: {e}")
        finally:
            instance = None
            log.info("舊實例已清除。")

    # 2. 定義模組的重載順序
    reload_order = [
        "core.languagelib.language",
        "core.languagelib.language_manager",
        "core.translator",
        "core.dto",
        "core.setting_reader",
        "core.logger",
        "core.script_parser",
        "core.decorators",
        "core.handlers.data_handler",
        "core.menu_generator",
        "core.ui",
        "core.handlers.settings_handler",
        "core.handlers.file_io_handler",
        "core.handlers.tree_interaction_handler",
        "core.handlers.editor_panel_handler",
        "core.controller"
    ]

    # 3. 尋找所有需要重載的模組
    modules_to_reload = [m for m in sys.modules if m.startswith("menubuilder")]
    
    # 4. 按照順序重載模組
    log.info("--- 開始重載 Menubuilder 模組 ---")
    reloaded_modules = set()
    for key in reload_order:
        full_module_name = f"menubuilder.{key}"
        if full_module_name in sys.modules:
            try:
                importlib.reload(sys.modules[full_module_name])
                log.info(f"  - 已重載: {full_module_name}")
                reloaded_modules.add(full_module_name)
            except Exception as e:
                log.error(f"重載 {full_module_name} 時失敗: {e}")
    
    # 重載其他未在順序列表中的模組
    for module_name in modules_to_reload:
        if module_name not in reloaded_modules:
            try:
                importlib.reload(sys.modules[module_name])
                log.info(f"  - 已重載 (其他): {module_name}")
            except Exception as e:
                log.error(f"重載 {module_name} 時失敗: {e}")
    
    # 5. 在所有模組都重載完畢後，直接手動更新語言資料
    log.info("正在手動更新語言實例的資料...")
    try:
        from .core.translator import tr_instance
        from .core.languagelib import language

        # 直接更新 LanguageManager 實例的內部屬性
        tr_instance._languages = language.LANG
        log.info("語言實例的資料已成功更新。")

    except Exception as e:
        log.error(f"手動更新語言資料時失敗: {e}", exc_info=True)
        
    log.info("--- Menubuilder 模組重載完畢 ---")


def show():
    """
    顯示 Menubuilder 工具UI，並使用單例模式確保視窗唯一。
    """
    global instance
    
    # 為了能呼叫 MenuBuilderController，我們需要先導入它
    # 將導入放在函式內部，確保在 reload_all 之後能獲取到最新的版本
    from .core import controller
    
    if instance is None:
        log.info("創建新的 MenubuilderController 實例...")
        instance = controller.MenuBuilderController()
    
    instance.show_ui()

# 為了方便，可以保留一個簡單的 reload 函式，讓它直接指向新的 reload_all
reload = reload_all