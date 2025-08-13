# menubuilder/core/languagelib/language_manager.py

class LanguageManager:
    def __init__(self, lang='en_us', languages=None):
        self._current_lang = lang
        self._languages = languages if languages else {}

    def set_language(self, lang):
        self._current_lang = lang

    def tr(self, key: str, **kwargs) -> str:
        """
        根據 key 獲取翻譯字串，並可選地格式化。
        如果找不到翻譯，則直接返回 key 本身。
        """
        # 預設值為 key 本身，確保即使翻譯缺失，UI 也能顯示一個有意義的文字
        default_text = key
        
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