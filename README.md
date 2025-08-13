<p align="center">
  <strong>English</strong> | <a href="./docs/README-zh-TW.md">繁體中文</a> | <a href="./docs/README-ja-JP.md">日本語</a>
</p>
# Menu Builder for Maya

**A visual Maya menu editing and management tool designed for 3D artists and project TAs.**

## Project Goal

`menubuilder` aims to solve the challenge Maya users face (especially in a project team) of managing a growing collection of external scripts and tools. The traditional Shelf becomes cluttered as the number of tools increases, and manually scripting menus presents a high barrier for artists.

This tool provides an intuitive graphical interface that allows users to easily integrate scattered Python/MEL scripts into Maya's main menu bar. It also facilitates the creation, sharing, and deployment of a standardized toolset for the entire team.

## Main Features

* **Visual Editing:** Intuitively preview and adjust the menu hierarchy and order through a tree view.
* **Drag-and-Drop Sorting:** Achieve "what you see is what you get" sorting by directly dragging and dropping items in the tree view.
* **Quick Operations:** Quickly modify and organize the menu structure through double-clicking to edit, using right-click context menus, and direct renaming.
* **Option Boxes:** Easily create and manage standard Maya option boxes via the right-click menu.
* **Separators:** Easily create and manage standard Maya separators via the right-click menu.
* **Script Parsing:** Automatically parses `.py` files to list all available functions, simplifying the process of adding commands.
* **Command Integration:** Supports both Python and MEL languages and provides a test execution feature.
* **Icon Selector:** Includes a built-in Maya icon browser and a local file browser to easily add icons to your tools with a live preview.
* **File Management:** Supports opening, merging, and saving different menu configuration files (`.json`) for convenient management.
* **Team Deployment:** Provides a lightweight startup script that allows team members to automatically generate menus upon Maya's launch without needing to open the editor.

## Installation and Usage

### **A) For "Menu Developers / TAs" (Using the Editor)**

This workflow is for creating and editing menu configuration files.

1.  **Place the Project:** Place the entire `menubuilder` project folder in a fixed, English-only path (e.g., `D:/maya-tools/menubuilder`).

2.  **Inform Maya of the Path:** To allow Maya to `import menubuilder`, you need to add the project's path to Maya's `PYTHONPATH` environment variable. The easiest way is to edit the `Maya.env` file.
    * **Find `Maya.env`:** It is typically located at `C:/Users/<Username>/Documents/maya/<Version>/`
    * **Edit the File:** Add the following line at the end of the file (or append it if PYTHONPATH already exists). The path should be the directory **containing** the `menubuilder` folder:
        ```
        PYTHONPATH = D:/maya-tools
        ```
    * You must **restart Maya** after modifying the file.

3.  **Launch and Develop:** After restarting Maya, execute the following commands in the Python Script Editor:
    ```python
    import menubuilder
    
    # First-time launch or normal usage
    menubuilder.show()
    
    # --- Development Workflow ---
    # After modifying the source code of menubuilder,
    # you don't need to restart Maya. Just run the following
    # commands to reload all modules.
    menubuilder.reload
    menubuilder.show()
    ```

### **B) For "Menu Users / Artists" (Deployment)**

This workflow is for deploying your configured menu to team members, who will have the menu generated automatically when they start Maya.

1.  **Preparation by TA/Developer:**
    * Use the `menubuilder` editor to save the team's menu configuration as a `.json` file (e.g., `project_menu.json`).
    * Open `settings.json` and ensure the value of `"menuitems"` is the filename you want the team to load by default (e.g., `"menuitems": "project_menu"`).
    * Provide the entire `menubuilder` project folder to the users.

2.  **User's Steps:**
    * Place the `menubuilder` folder in a fixed path (e.g., a network drive `P:/tools/menubuilder` or a local drive `D:/maya-tools/menubuilder`).
    * Find or create the `userSetup.py` file, located at:
        `C:/Users/<Username>/Documents/maya/scripts/userSetup.py`
    * Add the following code to `userSetup.py`, and **make sure `project_folder_path` points to the correct directory**:

    ```python
    # userSetup.py
    import maya.cmds as cmds
    import sys
    import os

    try:
        # --- Menubuilder Auto-Load ---
        # 
        # [IMPORTANT] Please change this path to the directory where
        # your menubuilder project is located.
        #
        project_folder_path = r"D:\maya-tools\menubuilder" # <-- This is the only line you need to modify
        
        # Check if the path exists and add it to Maya's Python search path
        if os.path.isdir(project_folder_path) and project_folder_path not in sys.path:
            sys.path.append(project_folder_path)
            
            # Use evalDeferred to ensure menu generation occurs after Maya has fully started.
            # This is the standard and safe practice for creating UI elements, including menus.
            cmds.evalDeferred("from menubuilder import setup_maya_menu; setup_maya_menu.build_menus_on_startup()")
            
    except Exception as e:
        cmds.warning(f"[Menubuilder Startup] Failed to load menus: {e}")
    # --- End Menubuilder ---
    ```

3.  **Done:** The next time the user starts Maya, the menu you configured for them will be generated automatically.

## Menubuilder Framework Guide

### File Structure

```
menubuilder/
├── init.py           # Main entry point (contains reload, show)
├── setup_maya_menu.py    # Startup script for team deployment
├── README.md             # Documentation
├── settings.json         # Global settings for the tool
│
├── core/                   # Core function modules
│   ├── controller.py     # Controller (core logic)
│   ├── ui.py             # UI definition
│   ├── data_handler.py   # Data handling (read/write .json)
│   ├── menu_generator.py # Maya menu generator
│   ├── script_parser.py  # Script parser
│   ├── dto.py            # Data Transfer Object (MenuItemData)
│   └── logger.py         # Logging system
│
├── doc/                  # Documentations
│
└── menuitems/              # Stores all menu configuration files (.json)
    └── personal_menubar.json # Default personal menu configuration
```

## UI Layout

### Left Panel: Menu Structure Panel

**Tree View (Menu Structure): This area displays the complete hierarchy of the current menu configuration. Here you can:**

* Drag and drop items to sort them or change their hierarchy.
* Right-click on items to perform structural operations like adding or deleting.
* Double-click an item to load its properties in the right panel for editing.

### Right Panel: Attribute Editing Panel

**Command Source (Input Tabs):**

* **Parse from File:** Allows you to browse and read a `.py` script. The tool will automatically list all functions within it for quick selection.
* **Manual Command Input:** For directly pasting or writing Python or MEL scripts.

**Command Editing Area:**

* **Command Language:** Choose whether the command you entered is Python or MEL.
* **Command Input Box:** Write or paste the code you want the menu item to execute.
* **Test Execute Button:** Immediately executes the command in the input box without generating the menu, allowing you to see the results or error messages in Maya's Script Editor for easy debugging.

**Attribute Editor:**

* **Label:** Defines the name of the menu item as it appears in Maya.
* **Path:** Defines the hierarchical path of the menu item, separated by `/` (e.g., `Tools/Rigging`). If left blank, it becomes a top-level menu.
* **Icon:** Assigns an icon to the menu item. Click "Custom..." to browse for local images or "Built-in..." to browse Maya's internal icon library.

## Core Workflow
### A. Adding a New Item

* **Locate:** In the left tree view, find where you want to add the new item.
* **Add Root Item:** Right-click in an empty area of the tree view and select "Add Root Item...".
* **Add Child Item:** Right-click on a folder and select "Add Item...".
* **Add Sibling Item:** Right-click on a menu item or a separator and select "Add Item...".
* **Fill in Attributes:** The right-side editing panel will be cleared (the menu path will be pre-filled). Fill in the "Label," "Command," and other information.
* **Test Command:** Click the "Test Execute" button to confirm your script works correctly.
* **Complete Addition:** Click the "Add to Structure" button, and the new item will appear in the tree view on the left.

### B. Editing an Existing Item

* **Enter Edit Mode:** In the left tree view, double-click the item you want to edit.
* **Observe Changes:**
    * The left tree view will be disabled (grayed out) to prevent conflicting operations like dragging.
    * The right panel will load all the properties of the item.
    * The "Add to Structure" button will change to an "Update | Finish Editing Item" button, possibly changing color as a visual cue.
* **Modify Attributes:** Modify any attributes you need in the right panel.
* **Finish Editing:**
    * Click the "Update | Finish Editing Item" button to save your changes.
    * Alternatively, press the `ESC` key to discard changes.
* **Exit Edit Mode:** After the operation is complete, the left tree view will automatically become enabled again.

### C. Managing Option Boxes

**Creating an Option Box:**
* Ensure that the item you want to set as an option box is directly below a valid "parent" menu item.
* Right-click on the item and select "Set as Option Box".

**Removing an Option Box:**
* Right-click on an item that is already an option box and select "Remove Option Box Status".

### D. Organizing and Sorting

When not in edit mode (i.e., the left tree view is clickable), you can freely drag any menu item, parent item, or folder to change its order or its parent folder.
The tool has built-in logic to prevent invalid drag-and-drop operations (e.g., dropping an item into another functional item, or inserting an item between a parent and its option box).

### E. Saving and Generating

* **Save Configuration File:** When you are satisfied with the layout, click the "Save Config File" button in the bottom right corner. All changes will be written to the `.json` file.
* **Preview in Maya:** Click the "✨ Generate/Refresh Menu in Maya" button at the very bottom. Menubuilder will automatically clear the old custom menu and generate a new one at the top of the Maya main window based on your current settings. You can click this button at any time to preview your changes.

---
*Document generated by Menubuilder AI Assistant, August 2025*