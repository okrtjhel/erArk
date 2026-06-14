# -*- coding: UTF-8 -*-
"""
L1 冒煙測試：驗證核心模組可 import、設定可載入、基本結構正常。

重要：
  - game.py 會開 Tkinter GUI 視窗並阻塞，不在此測試中啟動 GUI。
  - 改為行程內（in-process）驗證：import 核心模組 + 完成設定載入。
  - 需要執行 buildconfig.py 的重量級測試標記為 @pytest.mark.slow，
    預設的 `python -m pytest tests/` 不執行它們。
"""
import sys
import os
import pytest

# ── 確保 repo 根目錄在 sys.path（conftest.py 已處理，此處僅備份） ─────────
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


class TestCoreImports:
    """驗證核心模組可正常 import，不依賴任何遊戲狀態。"""

    def test_import_game_type(self):
        """
        輸入：無
        回傳：無
        功能：確認 game_type 模組可 import，Cache 類別存在。
        """
        from Script.Core import game_type
        assert hasattr(game_type, "Cache"), "game_type 應包含 Cache 類別"

    def test_import_cache_control(self):
        """
        輸入：無
        回傳：無
        功能：確認 cache_control 模組可 import。
        """
        from Script.Core import cache_control
        assert hasattr(cache_control, "cache"), "cache_control 應包含 cache 屬性"

    def test_import_json_handle(self):
        """
        輸入：無
        回傳：無
        功能：確認 json_handle 模組可 import，load_json 函式存在。
        """
        from Script.Core import json_handle
        assert hasattr(json_handle, "load_json"), "json_handle 應包含 load_json 函式"
        assert callable(json_handle.load_json), "load_json 應為可呼叫物件"

    def test_import_game_config(self):
        """
        輸入：無
        回傳：無
        功能：確認 game_config 模組可 import，init 函式存在。
        """
        from Script.Config import game_config
        assert hasattr(game_config, "init"), "game_config 應包含 init 函式"

    def test_import_normal_config(self):
        """
        輸入：無
        回傳：無
        功能：確認 normal_config 模組可 import。
        """
        from Script.Config import normal_config
        assert hasattr(normal_config, "init_normal_config"), "normal_config 應包含 init_normal_config 函式"

    def test_import_constant(self):
        """
        輸入：無
        回傳：無
        功能：確認常數模組可 import。
        """
        from Script.Core import constant
        assert hasattr(constant, "CharacterStatus"), "constant 應包含 CharacterStatus"


class TestConfigLoading:
    """驗證設定資料可正常載入（依賴 data/ 下的 JSON 建置產物）。"""

    def test_normal_config_init(self):
        """
        輸入：無
        回傳：無
        功能：確認 normal_config 初始化不崩潰，並可讀取 config.ini。
        """
        from Script.Config import normal_config
        # 確保工作目錄正確（切換到 repo 根目錄）
        original_cwd = os.getcwd()
        try:
            os.chdir(_REPO_ROOT)
            normal_config.init_normal_config()
            # 確認基本設定存在
            assert hasattr(normal_config.config_normal, "verson"), "config_normal 應有版本資訊"
        finally:
            os.chdir(original_cwd)

    def test_game_config_init(self, game_config_loaded):
        """
        輸入：game_config_loaded fixture
        回傳：無
        功能：確認 game_config.init() 執行完成後，關鍵設定字典不為空。
        """
        from Script.Config import game_config
        # 驗證幾個核心設定字典確實被載入
        assert len(game_config.config_behavior) > 0, "config_behavior 應有資料"
        assert len(game_config.config_character_state) > 0, "config_character_state 應有資料"

    def test_cache_instantiation(self, minimal_cache):
        """
        輸入：minimal_cache fixture
        回傳：無
        功能：確認 Cache 可正常實例化，基本屬性存在。
        """
        from Script.Core import game_type
        assert isinstance(minimal_cache, game_type.Cache), "minimal_cache 應為 Cache 實例"
        assert hasattr(minimal_cache, "character_data"), "Cache 應有 character_data 屬性"


@pytest.mark.slow
class TestBuildScripts:
    """
    慢速測試：以 subprocess 驗證建置腳本可正常執行。
    預設 `python -m pytest tests/` 不執行，需加 `-m slow` 才會跑。
    """

    def test_buildconfig_runs_successfully(self, tmp_path):
        """
        輸入：tmp_path（pytest 提供的暫存目錄）
        回傳：無
        功能：以 subprocess 執行 buildconfig.py，確認返回碼為 0（成功）。
              注意：此測試會修改 data/ 下的產物，但 git 衛生由執行者自行維護。
        """
        import subprocess
        result = subprocess.run(
            [sys.executable, "buildconfig.py"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        assert result.returncode == 0, (
            f"buildconfig.py 執行失敗（returncode={result.returncode}）\n"
            f"stdout: {result.stdout[-2000:]}\n"
            f"stderr: {result.stderr[-2000:]}"
        )
