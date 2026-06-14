# -*- coding: UTF-8 -*-
"""
L3 單元測試：Round A5 設施開放掃描索引化等價驗證。

驗證目標：
  以 adv_id 索引取代 save_handle.py 306-312 的設施×NPC 巢狀迴圈後，
  對各種輸入組合的設施開放結果與原始巢狀迴圈完全一致。

測試場景：
  1. 正常情況：有一個 NPC 的 adv 符合設施所需 NPC_id → 設施開放
  2. 無符合 NPC：npc_id_got 中沒有 adv 符合的 NPC → 設施保持關閉
  3. 同一 adv 對應多個 NPC：只要有一個符合就開放（原迴圈語義保留）
  4. 設施本身已開放：不應被任何邏輯關閉（本函式不改已開放的）
  5. NPC_id == 0 的設施：不需要 NPC，不應進入內層迴圈（保持當前狀態）
  6. 邊界：npc_id_got 為空 → 所有需要 NPC 的設施保持關閉

安全原則：純邏輯測試，不讀取真實存檔，不啟動 GUI。
"""
import sys
import os
import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ── 輔助：原始巢狀迴圈邏輯（保存為對照基準） ─────────────────────────────────

def _original_facility_open_logic(facility_open_dict, facility_open_config, npc_id_got, character_data):
    """
    輸入：
      facility_open_dict  -- dict[int, bool]，設施開放狀態（就地修改）
      facility_open_config -- dict[int, FacilityOpenConfig]，設施設定
      npc_id_got          -- set[int]，已獲得的 NPC cid 集合
      character_data      -- dict[int, CharData]，角色資料

    回傳：無（就地修改 facility_open_dict）
    功能：原始 O(設施×NPC) 巢狀掃描邏輯，作為等價測試的對照基準。
    """
    for all_cid in facility_open_config:
        if all_cid not in facility_open_dict:
            facility_open_dict[all_cid] = False
        if facility_open_dict[all_cid] == False:
            if facility_open_config[all_cid].NPC_id != 0:
                for chara_cid in npc_id_got:
                    character_data_item = character_data[chara_cid]
                    if character_data_item.adv == facility_open_config[all_cid].NPC_id:
                        facility_open_dict[all_cid] = True
                        break


def _new_facility_open_logic(facility_open_dict, facility_open_config, npc_id_got, character_data):
    """
    輸入：
      facility_open_dict  -- dict[int, bool]，設施開放狀態（就地修改）
      facility_open_config -- dict[int, FacilityOpenConfig]，設施設定
      npc_id_got          -- set[int]，已獲得的 NPC cid 集合
      character_data      -- dict[int, CharData]，角色資料

    回傳：無（就地修改 facility_open_dict）
    功能：以 adv_id 索引取代巢狀掃描的優化版本，語義與原始完全一致。
          對同一 adv 對應多個 NPC 的情況，只要任意一個存在即視為開放，
          與原始「第一個命中即 break」的語義等價。
    """
    # 預建 adv_id → True 索引（只需存在性，不需要知道是哪個 cid）
    got_adv_set = {character_data[cid].adv for cid in npc_id_got}

    for all_cid in facility_open_config:
        if all_cid not in facility_open_dict:
            facility_open_dict[all_cid] = False
        if facility_open_dict[all_cid] == False:
            if facility_open_config[all_cid].NPC_id != 0:
                if facility_open_config[all_cid].NPC_id in got_adv_set:
                    facility_open_dict[all_cid] = True


# ── 輔助資料類別 ──────────────────────────────────────────────────────────────

class _FacilityOpenConfig:
    """模擬 config_def.Facility_open 的最小結構。"""
    def __init__(self, npc_id: int):
        self.NPC_id = npc_id


class _CharData:
    """模擬 Character 的最小結構（只需 adv 欄位）。"""
    def __init__(self, adv: int):
        self.adv = adv


def _run_both(facility_open_config, npc_id_got, character_data, initial_state=None):
    """
    輸入：
      facility_open_config -- dict[int, _FacilityOpenConfig]
      npc_id_got           -- set[int]
      character_data       -- dict[int, _CharData]
      initial_state        -- dict[int, bool] 或 None（None 表示空字典）

    回傳：(orig_result, new_result) 兩個 dict[int, bool]
    功能：以相同輸入分別執行原始和新邏輯，回傳各自的設施開放字典，供比對。
    """
    orig_state = dict(initial_state) if initial_state else {}
    new_state = dict(initial_state) if initial_state else {}

    _original_facility_open_logic(orig_state, facility_open_config, npc_id_got, character_data)
    _new_facility_open_logic(new_state, facility_open_config, npc_id_got, character_data)

    return orig_state, new_state


# ── 測試案例 ──────────────────────────────────────────────────────────────────

class TestFacilityOpenIndexEquivalence:
    """驗證索引化後設施開放邏輯與原始巢狀掃描完全等價。"""

    def test_single_npc_opens_facility(self):
        """
        輸入：1 個設施需要 adv=101，1 個 NPC adv=101
        回傳：orig 和 new 結果相同，設施 1 = True
        功能：最基本情況，有符合 NPC 應開放設施。
        """
        config = {1: _FacilityOpenConfig(npc_id=101)}
        npcs = {10: _CharData(adv=101)}
        orig, new = _run_both(config, {10}, npcs)
        assert orig == new, f"結果不一致：orig={orig}, new={new}"
        assert orig[1] == True

    def test_no_matching_npc_keeps_closed(self):
        """
        輸入：1 個設施需要 adv=101，NPC adv=202（不符合）
        回傳：orig 和 new 結果相同，設施 1 = False
        功能：無符合 NPC 時設施應保持關閉。
        """
        config = {1: _FacilityOpenConfig(npc_id=101)}
        npcs = {10: _CharData(adv=202)}
        orig, new = _run_both(config, {10}, npcs)
        assert orig == new, f"結果不一致：orig={orig}, new={new}"
        assert orig[1] == False

    def test_same_adv_multiple_npcs_opens_facility(self):
        """
        輸入：1 個設施需要 adv=101；2 個 NPC 都有 adv=101
        回傳：orig 和 new 結果相同，設施 1 = True
        功能：同一 adv 對應多個 NPC 時，只要任一存在就開放（等價語義）。
        """
        config = {1: _FacilityOpenConfig(npc_id=101)}
        npcs = {10: _CharData(adv=101), 11: _CharData(adv=101)}
        orig, new = _run_both(config, {10, 11}, npcs)
        assert orig == new, f"結果不一致：orig={orig}, new={new}"
        assert orig[1] == True

    def test_facility_already_open_not_changed(self):
        """
        輸入：設施 1 初始已開放；NPC adv 完全不符
        回傳：orig 和 new 結果相同，設施 1 仍 = True（已開放不被關閉）
        功能：已開放的設施不應被本邏輯關閉。
        """
        config = {1: _FacilityOpenConfig(npc_id=101)}
        npcs = {10: _CharData(adv=999)}
        initial = {1: True}
        orig, new = _run_both(config, {10}, npcs, initial_state=initial)
        assert orig == new, f"結果不一致：orig={orig}, new={new}"
        assert orig[1] == True

    def test_facility_npc_id_zero_not_affected(self):
        """
        輸入：設施 1 的 NPC_id=0（不需要 NPC 開啟）
        回傳：orig 和 new 結果相同，設施 1 狀態不被本邏輯改變（保持 False）
        功能：NPC_id=0 的設施不進入內層判斷，狀態由其他邏輯管理。
        """
        config = {1: _FacilityOpenConfig(npc_id=0)}
        npcs = {10: _CharData(adv=999)}
        orig, new = _run_both(config, {10}, npcs)
        assert orig == new, f"結果不一致：orig={orig}, new={new}"
        assert orig[1] == False  # NPC_id=0，本邏輯不處理

    def test_empty_npc_id_got_all_closed(self):
        """
        輸入：3 個設施各需不同 NPC；npc_id_got 為空集合
        回傳：orig 和 new 結果相同，所有設施 = False
        功能：邊界條件，無任何 NPC 時所有需要 NPC 的設施保持關閉。
        """
        config = {
            1: _FacilityOpenConfig(npc_id=101),
            2: _FacilityOpenConfig(npc_id=202),
            3: _FacilityOpenConfig(npc_id=303),
        }
        npcs = {}  # 無角色資料（npc_id_got 為空，不會存取）
        orig, new = _run_both(config, set(), npcs)
        assert orig == new, f"結果不一致：orig={orig}, new={new}"
        assert all(v == False for v in orig.values())

    def test_multiple_facilities_partial_open(self):
        """
        輸入：3 個設施：
          - 設施 1 需要 adv=101，NPC 存在 → 應開放
          - 設施 2 需要 adv=202，NPC 不存在 → 保持關閉
          - 設施 3 需要 adv=303，NPC 存在 → 應開放
        回傳：orig 和 new 結果相同
        功能：多設施混合場景的完整等價驗證。
        """
        config = {
            1: _FacilityOpenConfig(npc_id=101),
            2: _FacilityOpenConfig(npc_id=202),
            3: _FacilityOpenConfig(npc_id=303),
        }
        npcs = {
            10: _CharData(adv=101),
            11: _CharData(adv=303),
            12: _CharData(adv=999),  # 不對應任何設施
        }
        orig, new = _run_both(config, {10, 11, 12}, npcs)
        assert orig == new, f"結果不一致：orig={orig}, new={new}"
        assert orig[1] == True
        assert orig[2] == False
        assert orig[3] == True

    def test_new_facility_not_in_initial_state(self):
        """
        輸入：設施 99 不在初始 facility_open_dict 中（跨版本新增設施的場景）
        回傳：orig 和 new 結果相同，設施 99 被初始化為 False，再依 NPC 判斷
        功能：驗證「新設施不存在於存檔」的跨版本更新場景等價。
        """
        config = {99: _FacilityOpenConfig(npc_id=500)}
        npcs = {20: _CharData(adv=500)}
        # 初始 state 不含設施 99
        initial = {1: True}  # 只有舊設施
        orig, new = _run_both(config, {20}, npcs, initial_state=initial)
        assert orig == new, f"結果不一致：orig={orig}, new={new}"
        assert orig[99] == True  # 新設施應被初始化並開放

    def test_large_scale_equivalence(self):
        """
        輸入：20 個設施，50 個 NPC，其中一半 NPC adv 符合設施需求
        回傳：orig 和 new 結果完全相同
        功能：較大規模輸入下的等價驗證，確保索引化在非平凡輸入下也正確。
        """
        # 設施 1..20，其中設施 i 需要 adv = i*100
        config = {i: _FacilityOpenConfig(npc_id=i * 100) for i in range(1, 21)}
        # NPC 1..50：cid=i，adv = i*100（i <= 10 才符合設施 i 的需求）
        npcs = {i: _CharData(adv=i * 100) for i in range(1, 51)}
        npc_id_got = set(range(1, 51))
        orig, new = _run_both(config, npc_id_got, npcs)
        assert orig == new, f"大規模測試結果不一致"
        # 設施 1..20 的 NPC_id 為 100..2000，npcs 中 cid=1..50 的 adv 為 100..5000
        # 設施 i(1..20) 需要 adv=i*100；NPC cid=i 有 adv=i*100，所以全部應開放
        for i in range(1, 21):
            assert orig[i] == True, f"設施 {i} 應開放（adv={i*100} 存在於 NPC 中）"
