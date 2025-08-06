from .core import controller
import importlib

instance = None

def reload():
    """Reload the menu manager module."""
    global instance
    instance = None
    importlib.reload(controller)
    
def show():
    """Show the Menu Builder Tool UI."""
    global instance
    if instance is None:
        instance = controller.MenuBuilderController()

    # 這裡最終會呼叫 instance.show_ui()
    # 目前的 print 僅為佔位符
    print('Show Menu Builder Tool UI')
    instance.show_ui() # 為下一階段做準備
