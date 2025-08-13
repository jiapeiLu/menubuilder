# languagelib/language.py

"""
Menubuilder - Language Data Module

這個模組儲存了所有用於多國語言的靜態文字。
金鑰 (key) 通常是英文原文或一個具代表性的識別字。
值 (value) 則是一個字典，對應到各種語言代碼 (如 'en_us', 'zh_tw', 'ja_jp') 的翻譯。


"""

LANG = {
    # ======================================================================
    # UI - Main Window (ui.py)
    # ======================================================================
    'app_title': {
        'en_us': 'Menu Builder',
        'zh_tw': '菜單建立工具',
        'ja_jp': 'メニュービルダー'
    },
    'menu_config_title': {
        'en_us': 'Menu Configuration',
        'zh_tw': '現有菜單結構',
        'ja_jp': 'メニュー構成'
    },
    'menu_config_title_with_file': {
        'en_us': 'Menu Configuration - {filename}',
        'zh_tw': '現有菜單結構 - {filename}',
        'ja_jp': 'メニュー構成 - {filename}'
    },
    'menu_structure_header': {
        'en_us': 'Menu Structure',
        'zh_tw': '菜單結構',
        'ja_jp': 'メニュー構造'
    },
    'tab_parse_from_file': {
        'en_us': 'Parse from File',
        'zh_tw': '從檔案解析',
        'ja_jp': 'ファイルから解析'
    },
    'tab_manual_input': {
        'en_us': 'Manual Input',
        'zh_tw': '手動輸入指令',
        'ja_jp': '手動入力'
    },
    'browse_script_button': {
        'en_us': 'Browse Script File...',
        'zh_tw': '瀏覽腳本檔案...',
        'ja_jp': 'スクリプトファイルを参照...'
    },
    'command_type_label': {
        'en_us': 'Type:',
        'zh_tw': '指令類型：',
        'ja_jp': 'タイプ：'
    },
    'python_radio': {
        'en_us': 'Python',
        'zh_tw': 'Python',
        'ja_jp': 'Python'
    },
    'mel_radio': {
        'en_us': 'MEL',
        'zh_tw': 'MEL',
        'ja_jp': 'MEL'
    },
    'command_input_placeholder': {
        'en_us': 'Please enter the command here, then select the corresponding Python or MEL language...',
        'zh_tw': '請在此輸入指令，並選取對應Python或mel語言...',
        'ja_jp': 'ここにコマンドを入力し、対応するPythonまたはMEL言語を選択してください...'
    },
    'test_run_button': {
        'en_us': 'Test Run',
        'zh_tw': '測試執行',
        'ja_jp': 'テスト実行'
    },
    'attribute_editor_group': {
        'en_us': 'Attribute Editor',
        'zh_tw': '屬性編輯器',
        'ja_jp': 'アトリビュートエディタ'
    },
    'label_form': {
        'en_us': 'Label:',
        'zh_tw': '菜單標籤：',
        'ja_jp': 'ラベル：'
    },
    'path_form': {
        'en_us': 'Path:',
        'zh_tw': '菜單路徑：',
        'ja_jp': 'パス：'
    },
    'path_placeholder': {
        'en_us': 'e.g., Tools/Modeling',
        'zh_tw': '例如: Tools/Modeling',
        'ja_jp': '例: Tools/Modeling'
    },
    'icon_form': {
        'en_us': 'Icon:',
        'zh_tw': '圖示路徑：',
        'ja_jp': 'アイコン：'
    },
    'icon_placeholder': {
        'en_us': 'Enter path or click buttons on the right to browse...',
        'zh_tw': '輸入路徑或點擊右側按鈕瀏覽...',
        'ja_jp': 'パスを入力するか、右側のボタンをクリックして参照...'
    },
    'custom_button': {
        'en_us': 'Custom...',
        'zh_tw': '自訂...',
        'ja_jp': 'カスタム...'
    },
    'custom_icon_tooltip': {
        'en_us': 'Browse for local icon files (e.g., C:/icon.png)',
        'zh_tw': '瀏覽本機的圖示檔案 (e.g., C:/icon.png)',
        'ja_jp': 'ローカルアイコンファイルを検索 (例: C:/icon.png)'
    },
    'builtin_button': {
        'en_us': 'Built-in...',
        'zh_tw': '內建...',
        'ja_jp': '組み込み...'
    },
    'builtin_icon_tooltip': {
        'en_us': "Browse for Maya's built-in icons (e.g., :polyCube.png)",
        'zh_tw': "瀏覽Maya內建圖示 (e.g., :polyCube.png)",
        'ja_jp': 'Maya組み込みアイコンを検索 (例: :polyCube.png)'
    },
    'preview_form': {
        'en_us': 'Preview:',
        'zh_tw': '預覽：',
        'ja_jp': 'プレビュー：'
    },
    'preview_none': {
        'en_us': 'None',
        'zh_tw': '無',
        'ja_jp': 'なし'
    },
    'preview_invalid': {
        'en_us': 'Invalid',
        'zh_tw': '無效',
        'ja_jp': '無効'
    },
    'add_to_structure_button': {
        'en_us': 'Add to Structure',
        'zh_tw': '新增至結構',
        'ja_jp': '構造に追加'
    },
    'save_config_button': {
        'en_us': 'Save Configuration',
        'zh_tw': '儲存設定檔',
        'ja_jp': '設定を保存'
    },
    'build_menus_button': {
        'en_us': '✨ Build/Refresh Menus in Maya',
        'zh_tw': '✨ 在Maya中產生/刷新菜單 (Build Menus)',
        'ja_jp': '✨ Mayaでメニューを構築/更新'
    },

    # ======================================================================
    # UI - Menu Bar (ui.py)
    # ======================================================================
    'file_menu': {
        'en_us': '&File',
        'zh_tw': '檔案(&F)',
        'ja_jp': 'ファイル(&F)'
    },
    'open_action': {
        'en_us': '&Open...',
        'zh_tw': '開啟設定檔(&O)...',
        'ja_jp': '開く(&O)...'
    },
    'merge_action': {
        'en_us': '&Merge...',
        'zh_tw': '合併設定檔(&M)...',
        'ja_jp': 'マージ(&M)...'
    },
    'save_action': {
        'en_us': '&Save',
        'zh_tw': '存檔(&S)',
        'ja_jp': '保存(&S)'
    },
    'save_as_action': {
        'en_us': 'Save &As...',
        'zh_tw': '另存新檔(&A)...',
        'ja_jp': '名前を付けて保存(&A)...'
    },
    'exit_action': {
        'en_us': 'E&xit',
        'zh_tw': '離開(&X)',
        'ja_jp': '終了(&X)'
    },
    'help_menu': {
        'en_us': '&Help',
        'zh_tw': '幫助(&H)',
        'ja_jp': 'ヘルプ(&H)'
    },
    'about_action': {
        'en_us': '&About',
        'zh_tw': '關於(&A)',
        'ja_jp': 'バージョン情報(&A)'
    },
    'github_action': {
        'en_us': 'View on &GitHub...',
        'zh_tw': '在 GitHub 上查看(&G)...',
        'ja_jp': 'GitHubで表示(&G)...'
    },

    # ======================================================================
    # UI - TreeView & Context Menu (ui.py)
    # ======================================================================
    'divider_text': {
        'en_us': '──────────',
        'zh_tw': '──────────',
        'ja_jp': '──────────'
    },
    'option_box_prefix': {
        'en_us': '(□) {label}',
        'zh_tw': '(□) {label}',
        'ja_jp': '(□) {label}'
    },
    'option_box_tooltip': {
        'en_us': 'This item is an Option Box,\nattached to the menu item above it.',
        'zh_tw': '此項目是一個選項框(Option Box)，\n隸屬於它上方的菜單項。',
        'ja_jp': 'この項目はオプションボックスで、\n上のメニュー項目に属します。'
    },
    'context_unset_option_box': {
        'en_us': 'Unset as Option Box',
        'zh_tw': '取消選項框',
        'ja_jp': 'オプションボックスを解除'
    },
    'context_set_option_box': {
        'en_us': 'Set as Option Box',
        'zh_tw': '設為選項框',
        'ja_jp': 'オプションボックスに設定'
    },
    'context_add_item': {
        'en_us': 'Add Item...',
        'zh_tw': '新增項目...',
        'ja_jp': '項目を追加...'
    },
    'context_add_separator': {
        'en_us': 'Add Separator',
        'zh_tw': '新增分隔線',
        'ja_jp': '区切り線を追加'
    },
    'context_send_path': {
        'en_us': "Send Path '{path}' to Editor",
        'zh_tw': "傳送路徑 '{path}' 至編輯器",
        'ja_jp': "パス '{path}' をエディタに送信"
    },
    'context_delete': {
        'en_us': 'Delete...',
        'zh_tw': '刪除...',
        'ja_jp': '削除...'
    },
    'context_delete_parent_with_option_box': {
        'en_us': 'Delete Item and Option Box...',
        'zh_tw': '刪除主項與選項框...',
        'ja_jp': '項目とオプションボックスを削除...'
    },
    'context_add_root': {
        'en_us': 'Add Root Item...',
        'zh_tw': '新增根級項目...',
        'ja_jp': 'ルート項目を追加...'
    },

    # ======================================================================
    # UI - Icon Browser (ui.py)
    # ======================================================================
    'icon_browser_title': {
        'en_us': 'Maya Icon Browser',
        'zh_tw': 'Maya 內建圖示瀏覽器',
        'ja_jp': 'Maya アイコンブラウザ'
    },
    'icon_search_placeholder': {
        'en_us': 'Search icon name (e.g., sphere)...',
        'zh_tw': '搜尋圖示名稱 (例如: sphere)...',
        'ja_jp': 'アイコン名を検索 (例: sphere)...'
    },

    # ======================================================================
    # Controller - Dialogs & Messages (controller.py)
    # ======================================================================
    'controller_select_script_title': {
        'en_us': 'Select Python Script',
        'zh_tw': '選擇 Python 腳本',
        'ja_jp': 'Pythonスクリプトを選択'
    },
    'controller_warn_select_to_delete': {
        'en_us': 'Please select an item in the list to delete.',
        'zh_tw': '請先在左側列表中選擇要刪除的項目。',
        'ja_jp': '削除する項目をリストから選択してください。'
    },
    'controller_warn_folder_delete': {
        'en_us': 'Cannot delete. The selected item is a folder or has no associated data. Please use the context menu to delete folders.',
        'zh_tw': '無法刪除，所選項目是一個文件夾或沒有關聯資料。請使用右鍵選單刪除文件夾。',
        'ja_jp': '削除できません。選択された項目はフォルダか、関連データがありません。フォルダを削除するには、コンテキストメニューを使用してください。'
    },
    'controller_warn_name_conflict_title': {
        'en_us': 'Name Conflict',
        'zh_tw': '命名衝突',
        'ja_jp': '名前の競合'
    },
    'controller_warn_name_conflict_body': {
        'en_us': "An item or folder with the name '{label}' already exists at the path '{path}'.",
        'zh_tw': "在路徑 '{path}' 下，已經存在一個同名的項目或子資料夾 '{label}'。",
        'ja_jp': "パス '{path}' には、'{label}' という名前の項目またはフォルダが既に存在します。"
    },
    'controller_info_build_success': {
        'en_us': 'Menus built/refreshed successfully!',
        'zh_tw': '菜單已成功生成/刷新！',
        'ja_jp': 'メニューは正常に構築/更新されました！'
    },
    'controller_open_config_title': {
        'en_us': 'Open Menu Configuration',
        'zh_tw': '開啟菜單設定檔',
        'ja_jp': 'メニュー構成を開く'
    },
    'controller_merge_config_title': {
        'en_us': 'Select Configuration to Merge',
        'zh_tw': '選擇要合併的設定檔',
        'ja_jp': 'マージする設定を選択'
    },
    'controller_save_as_config_title': {
        'en_us': 'Save Menu Configuration As',
        'zh_tw': '另存為菜單設定檔',
        'ja_jp': 'メニュー構成に名前を付けて保存'
    },
    'controller_warn_label_empty': {
        'en_us': "Please ensure the 'Label' field is not empty.",
        'zh_tw': "請確保'菜單標籤'欄位不為空。",
        'ja_jp': '「ラベル」フィールドが空でないことを確認してください。'
    },
    'update_finish_editing_button': {
        'en_us': 'Update | Finish Editing',
        'zh_tw': '更新 | 結束編輯',
        'ja_jp': '更新 | 編集を終了'
    },
    'controller_confirm_delete_title': {
        'en_us': 'Confirm Deletion',
        'zh_tw': '確認刪除',
        'ja_jp': '削除の確認'
    },
    'controller_confirm_delete_folder': {
        'en_us': "Are you sure you want to delete the folder '{path}' and all its contents?\nThis action cannot be undone.",
        'zh_tw': "您確定要刪除資料夾 '{path}' 及其下的所有內容嗎？\n此操作無法復原。",
        'ja_jp': "フォルダ '{path}' とそのすべての内容を削除してもよろしいですか？\nこの操作は元に戻せません。"
    },
    'controller_confirm_delete_parent_with_option_box': {
        'en_us': "Are you sure you want to delete '{name}' and its option box?\nThis action cannot be undone.",
        'zh_tw': "您確定要刪除 '{name}' 及其下方的選項框嗎？\n此操作無法復原。",
        'ja_jp': "'{name}' とそのオプションボックスを削除してもよろしいですか？\nこの操作は元に戻せません。"
    },
    'controller_confirm_delete_item': {
        'en_us': "Are you sure you want to delete '{name}'?",
        'zh_tw': "您確定要刪除 '{name}' 嗎？",
        'ja_jp': "'{name}' を削除してもよろしいですか？"
    },
    'controller_select_custom_icon_title': {
        'en_us': 'Select Custom Icon File',
        'zh_tw': '選擇自訂圖示檔案',
        'ja_jp': 'カスタムアイコンファイルを選択'
    },
    'about_dialog_title': {
        'en_us': 'About Menubuilder',
        'zh_tw': '關於 Menubuilder',
        'ja_jp': 'Menubuilder について'
    },
    'about_dialog_main_header': {
        'en_us': 'Menubuilder for Maya',
        'zh_tw': 'Menubuilder for Maya',
        'ja_jp': 'Menubuilder for Maya'
    },
    'about_dialog_version': {
        'en_us': 'Version',
        'zh_tw': '版本',
        'ja_jp': 'バージョン'
    },
    'about_dialog_description': {
        'en_us': 'A visual tool to edit and manage Maya menus.',
        'zh_tw': '一個視覺化的 Maya 菜單編輯與管理工具。',
        'ja_jp': 'Mayaのメニューを視覚的に編集・管理するツールです。'
    },
    'about_dialog_author': {
        'en_us': 'Author:',
        'zh_tw': '開發者：',
        'ja_jp': '開発者：'
    },
    'about_dialog_credits': {
        'en_us': 'Developed in collaboration with an AI Assistant.',
        'zh_tw': '此工具在 AI Assistant 的協作下完成開發。',
        'ja_jp': 'このツールはAIアシスタントとの協力のもとで開発されました。'
    },
    'controller_warn_test_run_empty': {
        'en_us': 'Command is empty. Nothing to test.',
        'zh_tw': '指令為空，沒有可測試的內容。',
        'ja_jp': 'コマンドが空です。テストする内容がありません。'
    },
    'controller_info_test_run_success': {
        'en_us': 'Test run successful!',
        'zh_tw': '測試執行成功！',
        'ja_jp': 'テスト実行に成功しました！'
    },
    'controller_warn_test_run_failed': {
        'en_us': 'Test run failed:',
        'zh_tw': '測試執行失敗：',
        'ja_jp': 'テスト実行に失敗しました：'
    },
}