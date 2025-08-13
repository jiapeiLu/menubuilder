<p align="center">
  <a href="../README.md">English</a> | <strong>繁體中文</strong> | <a href="./README-ja-JP.md">日本語</a>
</p>

# Menu Builder for Maya

**一個為 3D 美術師與專案 TA 設計的、視覺化的 Maya 菜單編輯與管理工具。**

## 專案目標

`menubuilder` 旨在解決 Maya 使用者（特別是在專案團隊中）管理日益增長的外部腳本和工具的難題。傳統的 Shelf 工具架在工具數量增多時會變得混亂不堪，而手動編寫菜單腳本對美術師來說門檻過高。

本工具提供了一個直觀的圖形介面，讓使用者可以輕鬆地將零散的 Python/MEL 腳本整合到 Maya 的主菜單欄中，並能方便地為整個團隊建立、分享和部署標準化的工具集。

## 主要功能

* **視覺化編輯:** 透過樹狀圖直觀地預覽和調整菜單的層級與順序。
* **拖放排序:** 直接在樹狀視圖中拖放項目，實現「所見即所得」的排序。
* **快捷操作:** 透過雙擊編輯、右鍵選單、直接重命名等方式快速修改和組織菜單結構。
* **選項框:** 透過右鍵選單、輕鬆創建和管理 Maya 標準的選項框功能。
* **分格線:** 透過右鍵選單、輕鬆創建和管理 Maya 標準的分隔線功能。
* **腳本解析:** 自動解析 `.py` 檔案，列出所有可用函式，簡化指令的添加。
* **指令整合:** 支援 Python 和 MEL 兩種語言，並提供測試執行功能。
* **圖示選擇器:** 內建 Maya 圖示瀏覽器和本地檔案瀏覽功能，輕鬆為您的工具添加圖示和即時預覽。
* **檔案管理:** 支援開啟、合併、另存為不同的菜單設定檔 (`.json`)，方便管理。
* **團隊部署:** 提供輕量級的啟動腳本，讓團隊成員無需開啟編輯器即可在 Maya 啟動時自動生成菜單。

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
    menubuilder.reload
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

### 檔案結構

```
menubuilder/
├── __init__.py           # 主入口點 (包含 reload, show)
├── setup_maya_menu.py    # 團隊部署用的啟動腳本
├── README.md             # 說明文件
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
├── docs/                  # 非英文本說明文件
│
└── menuitems/              # 存放所有菜單設定檔 (.json)
    └── personal_menubar.json # 預設的個人菜單設定
```

## 介面佈局

### 左側：菜單結構面板

**樹狀圖 (Menu Structure)：此區域顯示當前菜單設定檔的完整層級結構。您可以在此處：**

* 拖曳項目來進行排序或變更層級。

* 右鍵點擊項目以進行新增、刪除等結構性操作。

* 雙擊項目以在右側面板中載入其屬性進行編輯。

### 右側：屬性編輯面板

**指令來源 (Input Tabs)：**

* 從檔案解析：讓您可以瀏覽並讀取一個 .py 腳本，工具會自動列出其中所有的函式，方便您快速選用。

* 手動輸入指令：用於直接貼上或編寫 Python 或 MEL 指令碼。

**指令編輯區：**

* 指令類型：選擇您輸入的指令是 Python 還是 MEL。

* 指令輸入框：編寫或貼上您希望菜單執行的具體程式碼。

* 測試執行按鈕：在不生成菜單的情況下，立即執行輸入框中的指令，並在 Maya 的 Script Editor 中查看結果或錯誤訊息，方便除錯。

**屬性編輯器 (Attribute Editor)：**

* 菜單標籤 (Label)：定義菜單項在 Maya 中顯示的名稱。

* 菜單路徑 (Path)：定義菜單項所在的層級，用 / 分隔（例如 Tools/Rigging）。如果留空，則為頂級菜單。

* 圖示路徑 (Icon)：為菜單項指定一個圖示。可以點擊「自訂...」來瀏覽本機圖片，或點擊「內建...」來瀏覽 Maya 內建的圖示庫。

## 核心工作流程
### A. 新增一個功能項目

* **定位：**在左側樹狀圖中，找到您想新增項目的位置。

* **新增根級項目：**在樹狀圖的空白處按右鍵，選擇「新增根級項目...」。

* **新增子級項目：**在一個資料夾上按右鍵，選擇「新增項目...」。

* **新增同級項目：**在一個功能項或分隔線上按右鍵，選擇「新增項目...」。

* **填寫屬性：**此時，右側的編輯面板會被清空（菜單路徑會自動填入）。請依次填寫「菜單標籤」、「指令」等資訊。

* **測試指令：**點擊「測試執行」按鈕，確認您的指令碼可以正常運作。

* **完成新增：**點擊「新增至結構」按鈕，新的項目將會出現在左側的樹狀圖中。

### B. 編輯一個現有項目

* **進入編輯模式：**在左側樹狀圖中，雙擊您想編輯的項目。

**觀察變化：**

* 左側樹狀圖會變為灰色禁用狀態，防止此時進行拖曳等衝突操作。

* 右側面板會載入該項目的所有屬性。

* 「新增至結構」按鈕會變為「更新 | 結束編輯 項目」按鈕，並可能改變顏色以作提示。

* **修改屬性：**在右側面板修改您需要的任何屬性。

**完成編輯：**

* 點擊「更新 | 結束編輯 項目」按鈕來儲存您的修改。

* 或按下 ESC 鍵來放棄修改。

* 退出編輯模式：操作完成後，左側樹狀圖會自動恢復可用狀態。

### C. 管理選項框 (Option Box)

**創建選項框：**

確保您想設為選項框的項目，其正上方是一個有效的「父物件」功能項。

在該項目上按右鍵，選擇「設為選項框」。

**取消選項框：**

在一個已是選項框的項目上按右鍵，選擇「取消選項框狀態」。

### D. 整理與排序

在非編輯模式下（左側樹狀圖可被點擊時），您可以自由地拖曳任何功能項目、父物件或資料夾，來改變它們的順序或所屬的資料夾。

工具內建了完善的防呆邏輯，會阻止您進行不合邏輯的拖曳操作（例如，將項目拖入功能項之下，或在父物件與選項框之間插入項目）。

### E. 保存與生成

保存設定檔：當您對佈局感到滿意時，點擊右下角的「儲存設定檔」按鈕，所有修改將被寫入 .json 檔案中。

在 Maya 中預覽：點擊最下方的「✨ 在Maya中產生/刷新菜單」按鈕。Menubuilder 會自動清除舊的自訂菜單，並根據您當前的設定在 Maya 主視窗頂部生成全新的菜單。您可以隨時點擊此按鈕來預覽您的修改效果。

---
*文檔由 Menubuilder AI Assistant 生成, 2025年8月*