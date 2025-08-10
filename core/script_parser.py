# core/script_parser.py
import ast
import re
from .logger import log

class ScriptParser:
    """一個無狀態的工具類，提供解析功能。"""

    @staticmethod
    def parse_py_file(file_path: str) -> list:
        """
        [推薦使用] 一個更寬容的解析方法，使用正則表達式。
        它能容忍檔案中的語法錯誤 (例如 Python 2 的 print 語法)。
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
            print(f"解析檔案時出錯: {e}")
            return []

    @staticmethod
    def generate_label_from_string(command: str) -> str:
        """根據一系列規則，從指令字串智慧生成顯示標籤。"""
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
        檢查指定的Python腳本檔案是否包含 'for_dockable_layout' 函式。
        這是我們與使用者腳本之間的「契約」。
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
        

