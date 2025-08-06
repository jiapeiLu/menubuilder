# core/script_parser.py
import ast
import re

class ScriptParser:
    """一個無狀態的工具類，提供解析功能。"""

    @staticmethod
    def parse_py_file(file_path: str) -> list:
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