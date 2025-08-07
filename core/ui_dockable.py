# core/ui_dockable.py
import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide2 import QtWidgets, QtCore
from shiboken2 import wrapInstance
import inspect
from .logger import log

class DockableUIBase:
    """
    [重構後] 一個提供「可停靠 UI」功能的、普通的基底類別。
    """
    def show(self):
        if self.restore_workspace_control():
            return
        
        source = self.UI_SOURCE
        if isinstance(source, str):
            self.show_ui_from_command(source)
        elif inspect.isclass(source):
            self.show_ui_from_class(source)
        else:
            raise TypeError(f"'UI_SOURCE' in '{self.__class__.__name__}' must be a class or a string, but got {type(source)}.")

    def show_ui_from_class(self, widget_class: type):
        control_widget = self.create_workspace_control()
        if not control_widget: return
        self.ui_instance = widget_class()
        control_widget.layout().addWidget(self.ui_instance)

    def show_ui_from_command(self, script_command: str):
        control_widget = self.create_workspace_control()
        if not control_widget: return
        cmds.setParent(self.UI_NAME)
        exec(script_command)

    def restore_workspace_control(self) -> bool:
        if cmds.workspaceControl(self.UI_NAME, exists=True):
            cmds.workspaceControl(self.UI_NAME, edit=True, restore=True)
            return True
        return False
        
    def create_workspace_control(self) -> QtWidgets.QWidget | None:
        main_control = cmds.workspaceControl(
            self.UI_NAME, 
            label=self.UI_LABEL, 
            retain=False, 
            floating=True, 
            initialWidth=350, 
            initialHeight=200
        )
        try:
            control_ptr = omui.MQtUtil.findControl(main_control)
            control_widget = wrapInstance(int(control_ptr), QtWidgets.QWidget)
            control_widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            return control_widget
        except (RuntimeError, TypeError):
            return None

class DockableUILauncher(DockableUIBase):
    """
    [新增] 一個通用的啟動器類別，繼承了 DockableUIBase 的所有功能。
    """
    def __init__(self, UI_NAME: str, UI_LABEL: str, UI_SOURCE: str):
        self.UI_NAME = UI_NAME
        self.UI_LABEL = UI_LABEL
        self.UI_SOURCE = UI_SOURCE