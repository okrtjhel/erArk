# -*- coding: UTF-8 -*-
"""
pytest 全局設定與 fixture。

職責：
  1. 將 repo 根目錄加入 sys.path，使 `import Script...` 可正常運作。
  2. 強制 stdout/stderr 使用 UTF-8，避免 Windows 控制台（cp950 等）顯示中文時崩潰。
  3. 提供建構最小 `cache` 狀態的 fixture，供後續測試使用。
"""
import sys
import os
import pytest

# ── 1. 確保 repo 根目錄在 sys.path 最前面 ──────────────────────────────────
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ── 2. 強制 UTF-8 輸出（Windows 環境必要） ─────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


@pytest.fixture(scope="session")
def game_config_loaded():
    """
    輸入：無
    回傳：game_config 模組（已初始化）
    功能：Session 級別初始化遊戲設定資料（只跑一次），讓後續測試可使用
          game_config.config_* 系列資料。
          依賴 data/ 下已建置的 JSON 檔，需先跑過 buildconfig.py。
    """
    from Script.Config import normal_config, game_config

    # 初始化一般設定（讀取 config.ini）
    normal_config.init_normal_config()
    # 初始化所有遊戲配置資料
    game_config.init()

    return game_config


@pytest.fixture(scope="session")
def minimal_cache(game_config_loaded):
    """
    輸入：game_config_loaded fixture（確保設定已載入）
    回傳：game_type.Cache 實例（最小初始化狀態）
    功能：建構並回傳一個最小 cache 實例，供需要存取 cache 的測試使用。
          只初始化結構體，不啟動任何遊戲流程或 GUI。
    """
    from Script.Core import game_type, cache_control

    # 建構全新的 Cache 實例
    cache = game_type.Cache()
    # 將其設定到全域 cache_control 供需要的模組存取
    cache_control.cache = cache

    return cache
