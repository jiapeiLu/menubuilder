# menubuilder/core/translator.py

import importlib
from .languagelib.language_manager import LanguageManager
from .languagelib import language
from . import setting_reader

def initialize_translator():
    """
    初始化並返回一個配置好的翻譯函式。
    """
    # 為了能在 Maya 中重複執行時載入最新的語言檔案，我們重新載入模組
    importlib.reload(setting_reader)
    importlib.reload(language)
    
    # 從 setting.json 獲取當前設定的語言
    current_lang = setting_reader.current_setting.get('language', 'en_us')
    
    # 創建 LanguageManager 實例
    lang_manager = LanguageManager(lang=current_lang, languages=language.LANG)
    
    # 返回該實例的 tr 方法
    return lang_manager.tr

# 建立一個全域的 tr 函式，讓其他模組可以直接 from .translator import tr 來使用
tr = initialize_translator()