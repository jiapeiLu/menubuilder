[Read in English](./README.md)
# Menu Builder for Maya

**一個為 3D 美術師與專案 TA 設計的、視覺化的 Maya 菜單編輯與管理工具。**

## 專案目標

`menubuilder` 旨在解決 Maya 使用者（特別是在專案團隊中）管理日益增長的外部腳本和工具的難題。傳統的 Shelf 工具架在工具數量增多時會變得混亂不堪，而手動編寫菜單腳本對美術師來說門檻過高。

本工具提供了一個直觀的圖形介面，讓使用者可以輕鬆地將零散的 Python/MEL 腳本整合到 Maya 的主菜單欄中，並能方便地為整個團隊建立、分享和部署標準化的工具集。

## 主要功能

* **視覺化編輯:** 提供完整的圖形介面，菜單結構一目了然。
* **拖放排序:** 直接在樹狀視圖中拖放項目，實現「所見即所得」的排序。
* **腳本解析:** 自動解析 `.py` 檔案，列出所有可用函式，簡化指令的添加。
* **檔案管理:** 支援開啟、合併、另存為不同的菜單設定檔 (`.json`)，方便管理。
* **快捷操作:** 透過雙擊編輯、右鍵選單、直接重命名等方式快速修改和組織菜單結構。
* **圖示選擇器:** 內建 Maya 圖示瀏覽器和本地檔案瀏覽功能，輕鬆為您的工具添加圖示和即時預覽。
* **進階菜單:** 支援創建 Maya 原生的「選項框 (Option Box)」，讓工具集更專業。
* **團隊部署:** 提供輕量級的啟動腳本，讓團隊成員無需開啟編輯器即可在 Maya 啟動時自動生成菜單。

## 檔案結構

```
menubuilder/
├── __init__.py           # 主入口點 (包含 reload, show)
├── setup_maya_menu.py    # 團隊部署用的啟動腳本
├── README.md             # 本說明文件
├── settings.json         # 工具的全域設定
│
├── core/                   # 核心功能模組
│   ├── controller.py     # 控制器 (核心邏輯)
│   ├── ui.py             # UI 介面定義
│   ├── data_handler.py   # 資料處理 (讀寫 .json)
│   ├── menu_generator.py # Maya 菜單生成器
│   ├── script_parser.py  # 腳本解析器
│   ├── dto.py            # 資料傳輸物件 (MenuItemData)
│   └── logger.py         # 日誌系統
│
└── menuitems/              # 存放所有菜單設定檔 (.json)
    └── personal_menubar.json # 預設的個人菜單設定
```

## 安裝與使用

### **A) 供「菜單開發者 / TA」使用 (開啟編輯器)**

這個流程用於創建和編輯菜單設定檔。

1.  **放置專案:** 將 `menubuilder` 整個專案資料夾放置到一個固定的、純英文的路徑下（例如 `D:/maya-tools/menubuilder`）。

2.  **告知 Maya 路徑:** 為了讓 Maya 能 `import menubuilder`，您需要將專案的路徑加入到 Maya 的 `PYTHONPATH` 環境變數中。最簡單的方法是編輯 `Maya.env` 檔案。
    * **找到 `Maya.env`:** 它通常位於 `C:/Users/<使用者名稱>/Documents/maya/<版本號>/`
    * **編輯檔案:** 在檔案末尾加上一行（如果 PYTHONPATH 已存在，則在後面追加），路徑是 `menubuilder` 資料夾的**上一層目錄**：
        ```
        PYTHONPATH = D:/maya-tools
        ```
    * 修改後需要**重啟 Maya**。

3.  **啟動與開發:** 重啟 Maya 後，在 Python Script Editor 中執行以下指令：
    ```python
    import menubuilder
    
    # 首次啟動或正常使用
    menubuilder.show()
    
    # --- 開發流程 ---
    # 當您修改了 menubuilder 的原始碼後，
    # 無需重啟 Maya，只需執行以下指令來重載所有模組
    menubuilder.reload_all()
    menubuilder.show()
    ```

### **B) 供「菜單使用者 / 美術師」使用 (部署)**

這個流程用於將您配置好的菜單部署給團隊成員，他們在啟動 Maya 時會自動生成菜單。

1.  **TA/開發者準備:**
    * 使用 `menubuilder` 編輯器，將團隊所需的菜單配置儲存為一個 `.json` 檔案（例如 `project_menu.json`）。
    * 打開 `settings.json`，確保 `"menuitems"` 的值是您希望團隊預設載入的檔名（例如 `"menuitems": "project_menu"`）。
    * 將整個 `menubuilder` 專案資料夾提供給使用者。

2.  **使用者操作:**
    * 將 `menubuilder` 資料夾放置在一個固定的路徑下（例如網路硬碟 `P:/tools/menubuilder` 或本地 `D:/maya-tools/menubuilder`）。
    * 找到或創建 `userSetup.py` 檔案，它位於：
        `C:/Users/<使用者名稱>/Documents/maya/scripts/userSetup.py`
    * 在 `userSetup.py` 中加入以下程式碼，並**確保 `project_folder_path` 指向正確的路徑**：

    ```python
    # userSetup.py
    import maya.cmds as cmds
    import sys
    import os

    try:
        # --- Menubuilder Auto-Load ---
        # 
        # [重要] 請將此路徑修改為您 menubuilder 專案所在的資料夾路徑
        #
        project_folder_path = r"D:\maya-tools\menubuilder" # <-- 這是唯一需要修改的地方
        
        # 檢查路徑是否存在，並將其加入到Maya的Python搜尋路徑中
        if os.path.isdir(project_folder_path) and project_folder_path not in sys.path:
            sys.path.append(project_folder_path)
            
            # 使用 evalDeferred 確保在 Maya 完全啟動後才執行菜單生成
            # 這是創建UI（包括菜單）的標準且安全的作法
            cmds.evalDeferred("from menubuilder import setup_maya_menu; setup_maya_menu.build_menus_on_startup()")
            
    except Exception as e:
        cmds.warning(f"[Menubuilder Startup] Failed to load menus: {e}")
    # --- End Menubuilder ---
    ```

3.  **完成:** 使用者下次啟動 Maya 時，就會自動生成您為他們配置好的菜單。

## Menubuilder 框架指南

### 如何創建「選項框 (Option Box)」

`menubuilder` 支援創建 Maya 原生的「選項框」（即菜單項右側的 `□` 方塊）。

**規則：**
1.  一個項目要成為「選項框」，它在 `menubuilder` 的樹狀視圖中，必須緊跟在一個**有效的「父」功能項**下方。
2.  「父」功能項本身不能是另一個選項框或分隔符。
3.  在 `menubuilder` 的編輯器中，雙擊要設為選項框的項目，然後勾選 **`作為選項框 (IsOptionBox)`** 核取方塊。
4.  如果位置合法，`menubuilder` 會在UI中用 `(□)` 前綴和斜體來標識它。如果位置不合法，則會彈出提示。

---
*文檔由 Menubuilder AI Assistant 生成, 2025年8月*