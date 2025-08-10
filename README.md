[閱讀繁體中文版本 (Read in Traditional Chinese)](./README_zh-TW.md)
# Menu Builder for Maya

**A visual menu editor and management tool designed for 3D artists and project TAs.**

## Project Goal

`menubuilder` aims to solve the challenge Maya users face, especially within a project team, of managing a growing collection of external scripts and tools. The traditional Shelf becomes cluttered as the number of tools increases, and manually scripting menus presents a high barrier for artists.

This tool provides an intuitive graphical user interface, allowing users to easily integrate scattered Python/MEL scripts into Maya's main menu bar. It also facilitates the creation, sharing, and deployment of a standardized toolset for the entire team.

## Key Features

* **Visual Editor:** A complete GUI where the menu structure is clear at a glance.
* **Drag & Drop Sorting:** Directly drag and drop items in the tree view to achieve "What You See Is What You Get" (WYSIWYG) sorting.
* **Script Parsing:** Automatically parses `.py` files to list all available functions, simplifying the process of adding commands.
* **File Management:** Supports opening, merging, and saving different menu configurations as `.json` files for easy management.
* **Quick Actions:** Efficiently modify and organize the menu structure through double-clicking to edit, a right-click context menu, and direct renaming.
* **Icon Selector:** Includes a built-in Maya icon browser and a local file browser to easily add icons with a live preview for your tools.
* **Advanced Menus:** Supports the creation of Maya's native "Option Box" for a more professional toolset.
* **Team Deployment:** Provides a lightweight startup script that allows team members to automatically generate menus on Maya launch without needing the editor UI.

## File Structure

```
menubuilder/
├── __init__.py           # Main entry point (includes reload_all, show)
├── setup_maya_menu.py    # Startup script for team deployment
├── README.md             # This documentation
├── README_zh-TW.md       # Documentation in Traditional Chinese
├── settings.json         # Global settings for the tool
│
├── core/                   # Core functional modules
│   ├── controller.py     # Controller (core logic)
│   ├── ui.py             # UI definition
│   ├── data_handler.py   # Data handling (read/write .json)
│   ├── menu_generator.py # Maya menu generator
│   ├── script_parser.py  # Script parser
│   ├── dto.py            # Data Transfer Object (MenuItemData)
│   └── logger.py         # Logging system
│
├── icons/                  # Icons used by the UI
│
└── menuitems/              # Stores all menu configuration files (.json)
    └── personal_menubar.json # Default personal menu configuration
```

## Installation and Usage

### A) For Tool Developers / TAs (Using the Editor)

This workflow is for creating and editing menu configuration files.

1.  **Place the Project:** Place the entire `menubuilder` project folder in a fixed, English-only path (e.g., `D:/maya-tools/menubuilder`).

2.  **Inform Maya of the Path:** To allow Maya to `import menubuilder`, you need to add the project's path to Maya's `PYTHONPATH` environment variable. The easiest way is to edit the `Maya.env` file.
    * **Find `Maya.env`:** It is typically located at `C:/Users/<YourUsername>/Documents/maya/<Version>/`
    * **Edit the File:** Add a line at the end of the file (or append to an existing PYTHONPATH), pointing to the directory **containing** the `menubuilder` folder:
        ```
        PYTHONPATH = D:/maya-tools
        ```
    * A **Maya restart** is required after modifying the file.

3.  **Launch and Develop:** After restarting Maya, execute the following commands in the Python Script Editor:
    ```python
    import menubuilder
    
    # First launch or normal use
    menubuilder.show()
    
    # --- Development Workflow ---
    # After you modify any of the menubuilder source code,
    # you can reload all modules without restarting Maya by running:
    menubuilder.reload_all()
    menubuilder.show()
    ```

### B) For End-Users / Artists (Deployment)

This workflow is for deploying a pre-configured menu to team members, which will be generated automatically when they launch Maya.

1.  **Preparation by TA/Developer:**
    * Use the `menubuilder` editor to create and save the desired menu configuration into a `.json` file (e.g., `project_menu.json`).
    * Open `settings.json` and ensure the `"menuitems"` value points to the correct default filename (e.g., `"menuitems": "project_menu"`).
    * Provide the entire `menubuilder` project folder to the user.

2.  **End-User Setup:**
    * Place the `menubuilder` folder in a fixed location (e.g., a network drive `P:/tools/menubuilder` or a local drive `D:/maya-tools/menubuilder`).
    * Find or create the `userSetup.py` file, located at:
        `C:/Users/<YourUsername>/Documents/maya/scripts/userSetup.py`
    * Add the following code to `userSetup.py`, ensuring the `project_folder_path` points to the correct location:

    ```python
    # userSetup.py
    import maya.cmds as cmds
    import sys
    import os

    try:
        # --- Menubuilder Auto-Load ---
        # 
        # [IMPORTANT] Please change this path to the location of your menubuilder project folder.
        #
        project_folder_path = r"D:\maya-tools\menubuilder" # <-- This is the only line to modify
        
        # Checks if the path exists and adds it to Maya's Python search paths
        if os.path.isdir(project_folder_path) and project_folder_path not in sys.path:
            sys.path.append(project_folder_path)
            
            # Use evalDeferred to ensure the command runs after Maya's UI is fully initialized.
            # This is the standard, safe practice for creating UI elements at startup.
            cmds.evalDeferred("from menubuilder import setup_maya_menu; setup_maya_menu.build_menus_on_startup()")
            
    except Exception as e:
        cmds.warning(f"[Menubuilder Startup] Failed to load menus: {e}")
    # --- End Menubuilder ---
    ```

3.  **Done:** The next time the user launches Maya, the custom menu will be generated automatically.

## Menubuilder Framework Guide

### How to Create an "Option Box"

`menubuilder` supports the creation of Maya's native Option Boxes (the `□` square to the right of a menu item).

**The Rule:**
1.  For an item to become an "Option Box," it must be placed immediately below a valid "parent" functional item in the `menubuilder` tree view.
2.  The "parent" item cannot be another option box or a separator.
3.  In the `menubuilder` editor, double-click the item you want to be an option box, then check the **`IsOptionBox`** checkbox.
4.  If the position is valid, `menubuilder` will visually identify it with a `(□)` prefix and italic text. If the position is invalid, a warning will be displayed.

---
*Documentation generated by Menubuilder AI Assistant, August 2025*