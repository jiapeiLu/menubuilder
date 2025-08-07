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

    instance.show_ui() 
