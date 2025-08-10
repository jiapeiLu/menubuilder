# -*- coding: utf-8 -*-
#
# FILE: ui_framework_v2.py (Instantiation-based Framework)
#

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide2 import QtWidgets, QtCore
from shiboken2 import wrapInstance
import inspect
from .logger import log

class DockableUIBase:
    """
    一個提供「可停靠 UI」功能的實用類別 (Python 3+)。
    透過在 __init__ 中傳入配置參數來驅動。
    """
    def __init__(self, ui_name: str, ui_label: str, ui_source, ui_module: str = None):
        """
        Args:
            ui_name: workspaceControl 的唯一名稱。
            ui_label: 顯示在頁籤上的標題。
            ui_source: UI 的來源 (可以是 Widget 類別或命令字串)。
            ui_module: 當 ui_source 是類別時，其所在的模組名稱 (檔名)。
        """
        self.UI_NAME = ui_name
        self.UI_LABEL = ui_label
        self.UI_SOURCE = ui_source
        self.UI_MODULE = ui_module # 新增的屬性
        self.ui_instance = None

    def show(self):
        """統一的 UI 顯示入口點。"""
        if self._restore_workspace_control():
            return
        
        source = self.UI_SOURCE
        # source = for_dockable_layout

        if inspect.isclass(exec(source)):
            self._show_ui_from_class(source)
        elif isinstance(source, str):
            self._show_ui_from_command(source)
        else:
            raise TypeError(f"'UI_SOURCE' must be a class or a string, but got {type(source)}.")

    def _show_ui_from_class(self, widget_class: type):
        control_widget = self._create_workspace_control()
        if not control_widget: return
        self.ui_instance = widget_class()
        control_widget.layout().addWidget(self.ui_instance)

    def _show_ui_from_command(self, script_command: str):
        control_widget = self._create_workspace_control()
        if not control_widget: return
        cmds.setParent(self.UI_NAME)
        exec(script_command)

    def _get_rebuild_script(self) -> str:
        """
        取得重建腳本。現在的邏輯更加複雜，但可行。
        """
        source = self.UI_SOURCE
        
        # 模式 B: 如果來源是字串，重建腳本就是字串本身
        if isinstance(source, str):
            # 為了安全，我們還是把它包在一個 launcher 實例化裡面
            return (f"from {self.__class__.__module__} import {self.__class__.__name__}; "
                    f"instance = {self.UI_MODULE}.{self.UI_SOURCE}();"
                    f"instance.show();")

        # 模式 A: 如果來源是類別，利用新的 ui_module 屬性來生成腳本
        elif inspect.isclass(source):
            if not self.UI_MODULE:
                raise ValueError("ui_module must be provided when ui_source is a class.")

            widget_class_name = source.__name__
            
            # 生成一個包含所有必要 import 和參數的完整重建腳本
            rebuild_script = (
                f"from {self.__class__.__module__} import {self.__class__.__name__}; "
                f"from {self.UI_MODULE} import {widget_class_name}; "
                f"instance = {self.__class__.__name__}("
                f"ui_name='{self.UI_NAME}', "
                f"ui_label='{self.UI_LABEL}', "
                f"ui_module='{self.UI_MODULE}', "
                f"ui_source={widget_class_name}"
                f"); instance.show();"
            )
            return rebuild_script
            
        return "" # 不應該執行到這裡

    # ... (_restore_workspace_control, _create_workspace_control 維持不變) ...
    def _restore_workspace_control(self) -> bool:
        if cmds.workspaceControl(self.UI_NAME, exists=True):
            cmds.workspaceControl(self.UI_NAME, edit=True, restore=True)
            return True
        return False
    def _create_workspace_control(self) -> QtWidgets.QWidget :
        main_control = cmds.workspaceControl(
            self.UI_NAME, label=self.UI_LABEL, uiScript=self._get_rebuild_script(),
            retain=False, floating=True, initialWidth=350, initialHeight=200
        )
        try:
            control_ptr = omui.MQtUtil.findControl(main_control)
            control_widget = wrapInstance(int(control_ptr), QtWidgets.QWidget)
            control_widget.setAttribute(QtCore.Qt.WA_DeleteOnClose)
            return control_widget
        except (RuntimeError, TypeError):
            return None

def launch_dockable_from_data(ui_name: str, ui_label: str, module_name: str, func_name: str):
    """公開的輔助函式，接收解析好的資料來啟動UI。"""
    try:
        log.debug(f"透過輔助函式啟動 Dockable UI: {ui_name}")
        launcher = DockableUIBase(
            ui_name=ui_name,
            ui_label=ui_label,
            ui_module=module_name,
            ui_source=func_name
        )
        launcher.show()
    except Exception as e:
        log.error(f"啟動 Dockable UI '{ui_label}' 時發生錯誤: {e}", exc_info=True)