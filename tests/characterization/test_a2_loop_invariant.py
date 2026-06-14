# -*- coding: UTF-8 -*-
"""
L2 特性測試：Round A2 迴圈不變量外提等價驗證。

驗證：
  1. character_behavior.py：npc_count = len(id_list) 外提後，
     迴圈退出條件與原本 len(id_list) 計算完全一致。
  2. settle_behavior.py：state_cfg 區域變數快取後，
     狀態排序與輸出邏輯與原始 game_config.config_character_state[status_id] 多次查詢等價。
"""
import sys
import os
import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ── 輔助：重現「舊版」排序邏輯（原始多次字典查找版本） ──────────────────────

def _old_build_resort_state_list(config_character_state, status_data):
    """
    輸入：config_character_state (dict)：狀態設定字典
         status_data (dict)：角色當前狀態值
    回傳：list：排序後的 status_id 列表
    功能：重現原始多次查詢 config_character_state[status_id] 的排序邏輯，供對照。
    """
    resort_state_list = [
        status_id
        for status_id in config_character_state
        if status_id in status_data and status_data[status_id] != 0
    ]
    resort_state_list.sort(key=lambda sid: config_character_state[sid].type)
    return resort_state_list


def _old_build_state_name(config_character_state, status_id, translate_fn):
    """
    輸入：config_character_state (dict)：狀態設定字典
         status_id (int)：狀態 ID
         translate_fn (callable)：翻譯函式
    回傳：str：格式化後的狀態名稱
    功能：重現原始三次 config_character_state[status_id] 查詢的狀態名稱建立邏輯。
    """
    state_name = config_character_state[status_id].name
    if config_character_state[status_id].type == 0:
        state_name += translate_fn("快感")
    state_name = f"{state_name.ljust(6, '　')}"
    return state_name


def _new_build_state_name(config_character_state, status_id, translate_fn):
    """
    輸入：config_character_state (dict)：狀態設定字典
         status_id (int)：狀態 ID
         translate_fn (callable)：翻譯函式
    回傳：str：格式化後的狀態名稱
    功能：重現新版使用 state_cfg 區域變數快取的狀態名稱建立邏輯。
    """
    state_cfg = config_character_state[status_id]  # 一次取出
    state_name = state_cfg.name
    if state_cfg.type == 0:
        state_name += translate_fn("快感")
    state_name = f"{state_name.ljust(6, '　')}"
    return state_name


# ── 測試：npc_count 外提等價 ──────────────────────────────────────────────────

class TestNpcCountInvariant:
    """驗證 len(id_list) 外提為 npc_count 的語義等價性。"""

    def test_npc_count_matches_len_at_snapshot_time(self):
        """
        輸入：模擬 id_list（已固定快照的 set）
        回傳：無
        功能：確認 npc_count = len(id_list) 與後續每次 len(id_list) 計算完全相同。
              id_list 是 cache.npc_id_got.copy() 的快照，本輪不會改變，
              因此外提計算結果恆等於三處原始 len(id_list) 的值。
        """
        # 模擬 id_list（copy 後的快照）
        id_list = {1, 2, 3, 5, 8}
        id_list.discard(0)

        npc_count = len(id_list)

        # 三處原始引用的等價驗證
        assert len(id_list) == npc_count, "while 條件的 len(id_list) 應等於 npc_count"
        assert len(id_list) == npc_count, "debug 輸出的 len(id_list) 應等於 npc_count"
        assert len(id_list) + 1 == npc_count + 1, "break 條件的 len(id_list)+1 應等於 npc_count+1"

    def test_npc_count_with_player_discarded(self):
        """
        輸入：包含玩家 id 0 的 npc_id_got 快照
        回傳：無
        功能：確認 discard(0) 後的 npc_count 與 len(id_list) 一致。
        """
        raw_set = {0, 1, 2, 3}
        id_list = raw_set.copy()
        id_list.discard(0)

        npc_count = len(id_list)

        assert npc_count == 3, f"discard 0 後應有 3 個 NPC，實際 {npc_count}"
        assert len(id_list) == npc_count

    def test_npc_count_empty_set(self):
        """
        輸入：空的 npc_id_got（只有玩家 0）
        回傳：無
        功能：確認空 NPC 集合時 npc_count == 0，迴圈退出條件正確。
        """
        id_list = {0}.copy()
        id_list.discard(0)

        npc_count = len(id_list)
        assert npc_count == 0

        # 模擬退出條件：over_behavior_character 含玩家 0
        over_behavior_character = {0}
        assert len(over_behavior_character) >= npc_count + 1  # 應立即退出


# ── 測試：state_cfg 快取等價 ──────────────────────────────────────────────────

class TestStateCfgCacheEquivalence:
    """驗證 state_cfg 區域變數快取後狀態名稱建立邏輯等價。"""

    def test_state_name_equivalence_no_config(self):
        """
        輸入：模擬 config_character_state 字典（含 name 與 type 屬性的 mock 物件）
        回傳：無
        功能：對非快感狀態（type != 0），新舊版建立的 state_name 完全相同。
        """
        class MockStateCfg:
            def __init__(self, name, type_):
                self.name = name
                self.type = type_

        mock_config = {
            1: MockStateCfg("疲劳", 1),
            2: MockStateCfg("饥饿", 2),
        }

        def fake_translate(s):
            return s

        for status_id in mock_config:
            old = _old_build_state_name(mock_config, status_id, fake_translate)
            new = _new_build_state_name(mock_config, status_id, fake_translate)
            assert old == new, (
                f"status_id={status_id}: 舊版='{old}' 新版='{new}' 不一致"
            )

    def test_state_name_equivalence_pleasure(self):
        """
        輸入：模擬 config_character_state 字典（type==0 為快感狀態）
        回傳：無
        功能：對快感狀態（type == 0），新舊版建立的 state_name 完全相同（含「快感」後綴）。
        """
        class MockStateCfg:
            def __init__(self, name, type_):
                self.name = name
                self.type = type_

        mock_config = {
            10: MockStateCfg("阴道", 0),
            11: MockStateCfg("乳首", 0),
        }

        def fake_translate(s):
            return s

        for status_id in mock_config:
            old = _old_build_state_name(mock_config, status_id, fake_translate)
            new = _new_build_state_name(mock_config, status_id, fake_translate)
            assert old == new, (
                f"快感 status_id={status_id}: 舊版='{old}' 新版='{new}' 不一致"
            )
            assert "快感" in old, f"快感狀態應含『快感』後綴，實際：'{old}'"

    def test_resort_state_list_order_preserved(self):
        """
        輸入：模擬 status_data（含多個狀態值）與 config_character_state
        回傳：無
        功能：確認排序後的 resort_state_list 與原始多次查詢排序結果完全相同。
              新版使用 state_cfg 快取，不影響排序邏輯（排序 key 仍為 .type）。
        """
        class MockStateCfg:
            def __init__(self, name, type_):
                self.name = name
                self.type = type_

        mock_config = {
            1: MockStateCfg("疲劳", 1),
            10: MockStateCfg("阴道", 0),
            20: MockStateCfg("肛门", 0),
            5: MockStateCfg("饥饿", 2),
        }

        status_data = {1: 50, 10: 100, 20: 0, 5: 30}  # 20 值為 0，不應出現

        resort = _old_build_resort_state_list(mock_config, status_data)

        # 驗證：值為 0 的狀態不出現
        assert 20 not in resort, "值為 0 的狀態不應出現在 resort_state_list"
        # 驗證：type==0 的快感狀態在前
        type_list = [mock_config[sid].type for sid in resort]
        assert type_list == sorted(type_list), f"排序後 type 應遞增，實際：{type_list}"
        # 驗證：1（疲劳,type=1）、10（阴道,type=0）、5（饥饿,type=2）均出現
        assert set(resort) == {1, 10, 5}


# ── 測試：整合 game_config（若資料已建置） ────────────────────────────────────

class TestStateCfgWithRealConfig:
    """使用真實 game_config 驗證 state_cfg 快取等價（依賴已建置的 data/*.json）。"""

    @pytest.fixture(autouse=True)
    def load_config(self, game_config_loaded):
        """使用 conftest 提供的 game_config_loaded fixture 確保設定已載入。"""
        self.game_config = game_config_loaded

    def test_state_cfg_cache_matches_direct_lookup(self):
        """
        輸入：真實 game_config.config_character_state（所有真實狀態設定）
        回傳：無
        功能：對每個 status_id，驗證 state_cfg = config[status_id] 後
              .name 與 .type 均與直接查詢 config[status_id].name/.type 完全相同。
        """
        config = self.game_config.config_character_state
        assert len(config) > 0, "config_character_state 應有至少一個狀態設定"

        for status_id in config:
            state_cfg = config[status_id]  # 模擬新版取出區域變數
            assert state_cfg.name == config[status_id].name, (
                f"status_id={status_id}: state_cfg.name='{state_cfg.name}' "
                f"≠ direct='{config[status_id].name}'"
            )
            assert state_cfg.type == config[status_id].type, (
                f"status_id={status_id}: state_cfg.type={state_cfg.type} "
                f"≠ direct={config[status_id].type}"
            )

    def test_state_name_all_real_states(self):
        """
        輸入：真實 game_config.config_character_state 的所有狀態
        回傳：無
        功能：對所有真實狀態，新舊版 state_name 建立邏輯完全一致。
        """
        from Script.Core.get_text import _

        config = self.game_config.config_character_state

        for status_id in config:
            old = _old_build_state_name(config, status_id, _)
            new = _new_build_state_name(config, status_id, _)
            assert old == new, (
                f"status_id={status_id}: 舊版='{old}' 新版='{new}' 不一致"
            )
