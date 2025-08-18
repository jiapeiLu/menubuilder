# menubuilder/core/languagelib/language_manager.py

from .. import setting_reader
from . import language
import importlib
from ..logger import log

class LanguageManager:
    def __init__(self):
        # 在初始化時，直接從 setting_reader 獲取語言設定
        importlib.reload(setting_reader)
        importlib.reload(language)
        
        self._current_lang = setting_reader.current_setting.get('language', 'en_us')
        self._languages = language.LANG

    def set_language(self, lang):
        self._current_lang = lang


    def tr(self, key: str, **kwargs) -> str:
        """
        根據 key 獲取翻譯字串，並可選地格式化。
        如果找不到翻譯，則直接返回 key 本身。
        """
        
        # 嘗試獲取英文原文作為第二層預設值
        english_text = self._languages.get(key, {}).get('en_us', key)

        translation = self._languages.get(key, {}).get(self._current_lang, english_text)
        
        if kwargs:
            return translation.format(**kwargs)
        return translation

if __name__ == "__main__":
    # Example usage
    languages = {
        'greeting': {'en_us': 'Hello, {name}!', 'fr_fr': 'Bonjour, {name}!'},
        'farewell': {'en_us': 'Goodbye!', 'fr_fr': 'Au revoir!'}
    }
    
    manager = LanguageManager(lang='en_us', languages=languages)
    print(manager.tr('greeting', name='Alice'))  # Output: Hello, Alice!
    
    manager.set_language('fr_fr')
    print(manager.tr('greeting', name='Alice'))  # Output: Bonjour, Alice!
    print(manager.tr('farewell'))  # Output: Au revoir!