# menubuilder/core/translator.py

from .languagelib.language_manager import LanguageManager

# 建立一個全域的、唯一的翻譯器實例
# 所有其他模組都將使用這同一個實例
#tr_instance = LanguageManager()

# 為了方便呼叫，我們可以創建一個指向 tr 方法的別名
#tr = tr_instance.tr

from PySide2 import QtCore
from .languagelib.language_manager import LanguageManager

def get_translator_instance():
    """
    一個穩健的單例工廠函式。
    它確保在整個 Maya Session 中，LanguageManager 的實例只會被創建一次。
    """
    # 獲取 Qt 應用程式的實例
    app = QtCore.QCoreApplication.instance()
    
    # 檢查實例是否已經被附加到 app 上
    # 我們使用一個唯一的屬性名來儲存它
    if not hasattr(app, '_menubuilder_translator_instance'):
        print("INFO: Creating new LanguageManager instance.")
        # 如果不存在，則創建一個新的，並將其附加到 app 上
        instance = LanguageManager()
        setattr(app, '_menubuilder_translator_instance', instance)
    
    # 返回那個唯一的、共享的實例
    return getattr(app, '_menubuilder_translator_instance')

# 建立一個全域的、唯一的翻譯器實例的引用
tr_instance = get_translator_instance()

# 為了方便呼叫，創建一個指向 tr 方法的別名
tr = tr_instance.tr