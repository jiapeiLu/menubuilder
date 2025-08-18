"""
Menubuilder - Script Parser Utility Module

這個模組提供了一系列靜態方法，用於解析和分析 Python 腳本檔案。

它的主要職責包括：
- 從 .py 檔案中寬容地解析出所有函式名稱。
- 根據約定的規則，從函式名或指令字串中智慧生成易讀的標籤。
- 檢查腳本是否符合特定的框架契約 (例如，是否包含 'for_dockable_layout' 函式)。
"""
import ast
import re
from .logger import log

class ScriptParser:
    """
    一個無狀態的工具類 (Utility Class)，提供一系列靜態方法來解析和分析腳本。

    這個類別不儲存任何實例狀態。它的所有方法都是獨立的，接收輸入並返回
    結果，主要用於從檔案字串中提取函式名稱、生成標籤等與腳本內容相關的
    操作。
    """

    @staticmethod
    def parse_py_file(file_path: str) -> list:
        """
        從指定的 Python 腳本檔案中，解析出所有頂層的函式名稱。

        這個方法採用了寬容度較高的正則表達式進行解析，因此即使腳本中
        包含部分語法錯誤（例如 Python 2 的 print 語法），它依然能成功
        提取出函式定義的名稱，這使得工具能更好地相容各種舊腳本。

        Args:
            file_path (str): 要解析的 .py 檔案的完整路徑。

        Returns:
            list: 一個包含所有找到的函式名稱（字串）的列表。
                  如果解析失敗，則返回一個空列表。
        """
        functions = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 正則表達式: 尋找以 'def' 開頭，後接函式名稱和括號的行
            # ^\s* - 行首可能有空格
            # def\s+     - 'def'關鍵字和至少一個空格
            # ([a-zA-Z_]\w*) - 捕獲函式名稱 (必須以字母或底線開頭)
            # \s*\(      - 函式名稱後可能有空格，然後是左括號
            pattern = re.compile(r'^\s*def\s+([a-zA-Z_]\w*)\s*\(', re.MULTILINE)
            functions = pattern.findall(content)
            return functions

        except Exception as e:
            log.error(f"使用正則表達式解析檔案時出錯: {e}", exc_info=True)
            return []
    
    # (可以保留舊的 ast 方法作為備用)
    @staticmethod
    def parse_py_file_strict(file_path: str) -> list:
        """使用AST解析Python檔案，找出所有頂層函式定義。"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            return functions
        except Exception as e:
            # 在真實的應用中，應該讓log系統來記錄這個錯誤
            log.error(f"解析檔案時出錯: {e}")
            return []

    @staticmethod
    def generate_label_from_string(command: str) -> str:
        """
        根據一系列預設規則，將一個技術性的指令字串轉換為人類易讀的菜單標籤。

        轉換規則包括：
        - 移除常見的前綴 (如 'cmds.') 和後綴 (如 '.main()')。
        - 將蛇形命名 (snake_case) 和駝峰式命名 (CamelCase) 轉換為帶空格的單字。
        - 將每個單字的首字母轉為大寫。

        Args:
            command (str): 原始的函式名或指令字串。
                           例如："my_awesome_tool" 或 "cmds.polySphere"。

        Returns:
            str: 一個格式化後的標籤字串。例如："My Awesome Tool" 或 "Poly Sphere"。
        """
        # 1. 移除常見的前綴和後綴
        core_cmd = re.sub(r'^cmds\.', '', command)
        core_cmd = re.sub(r'\.(main|run|execute)\s*\(\)\s*$', '', core_cmd)
        
        # 嘗試從 import a; a.run() 格式中提取 'a'
        match = re.search(r'import\s+(\w+);\s*\1', core_cmd)
        if match:
            core_cmd = match.group(1)

        # 2. 處理 snake_case 和 CamelCase
        # snake_case to spaces
        spaced_cmd = core_cmd.replace('_', ' ')
        # CamelCase to spaces (e.g., myTool -> my Tool)
        spaced_cmd = re.sub(r'([a-z])([A-Z])', r'\1 \2', spaced_cmd)
        
        # 3. 首字母大寫並清理
        return ' '.join(word.capitalize() for word in spaced_cmd.split()).strip()
    '''disable dockable
    @staticmethod
    def has_dockable_interface(file_path: str) -> bool:
        """
        檢查指定的Python腳本檔案是否符合 Menubuilder 的「可停靠UI框架契約」。

        這個契約的具體內容是：腳本中必須包含一個確切名為 `for_dockable_layout`
        的函式。這個方法用於在使用者勾選 `IsDockableUI` 時，驗證目標腳本的
        相容性。

        Args:
            file_path (str): 要檢查的 .py 檔案的完整路徑。

        Returns:
            bool: 如果腳本符合契約返回 `True`，否則返回 `False`。
        """
        if not file_path:
            return False
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用正則表達式快速、寬容地進行檢查
            pattern = re.compile(r'^\s*def\s+for_dockable_layout\s*\(\s*\):', re.MULTILINE)
            if pattern.search(content):
                log.debug(f"在 '{file_path}' 中找到 'for_dockable_layout' 介面。")
                return True
            else:
                log.debug(f"在 '{file_path}' 中未找到 'for_dockable_layout' 介面。")
                return False
        except Exception as e:
            log.error(f"檢查 dockable 介面時出錯: {e}")
            return False'''
        

