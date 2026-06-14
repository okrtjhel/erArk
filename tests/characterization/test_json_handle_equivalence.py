# -*- coding: UTF-8 -*-
"""
L2 特性測試：json_handle.load_json 新舊等價驗證（Round A1）。

驗證重構後的 load_json 與「原始讀法等價邏輯」對同一批 JSON 檔
回傳完全相同的資料，確認改動不改變行為。

涵蓋：
  - 一般 UTF-8 JSON 檔（至少一個）
  - 若環境中有 UTF-8 BOM 檔，亦進行驗證
"""
import sys
import os
import json
import pytest

# 確保 repo 根目錄在 sys.path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ── 舊版 load_json 邏輯（等價參考實作） ────────────────────────────────────

def _old_is_utf8bom(file_path: str) -> bool:
    """
    輸入：file_path (str)：檔案路徑
    回傳：bool：前 3 個位元組是否為 UTF-8 BOM
    功能：原始 is_utf8bom 的等價重現，供測試用。
    """
    return b"\xef\xbb\xbf" == open(file_path, mode="rb").read(3)


def _old_load_json(file_path: str) -> dict:
    """
    輸入：file_path (str)：JSON 檔案路徑
    回傳：dict | list：解析後的 JSON 資料；解析失敗回傳空列表
    功能：原始 load_json 邏輯的等價重現，供測試比對。
          開兩次檔案（BOM 偵測 + 讀取），以 json.loads(f.read()) 解析。
    """
    if _old_is_utf8bom(file_path):
        ec = "utf-8-sig"
    else:
        ec = "utf-8"
    with open(file_path, "r", encoding=ec) as f:
        try:
            json_data = json.loads(f.read())
            f.close()
        except json.decoder.JSONDecodeError:
            json_data = []
    return json_data


# ── 測試案例 ────────────────────────────────────────────────────────────────

class TestLoadJsonEquivalence:
    """驗證新版 load_json 與舊版完全等價。"""

    def test_data_json_equivalence(self):
        """
        輸入：data/data.json（主要遊戲配置，一般 UTF-8 無 BOM）
        回傳：無
        功能：比對新舊 load_json 對 data.json 回傳值完全相同。
        """
        from Script.Core import json_handle

        path = os.path.join(_REPO_ROOT, "data", "data.json")
        assert os.path.exists(path), f"測試依賴的 data.json 不存在：{path}（請先跑 buildconfig.py）"

        old_result = _old_load_json(path)
        new_result = json_handle.load_json(path)

        assert type(old_result) == type(new_result), (
            f"回傳型別不同：舊={type(old_result).__name__}，新={type(new_result).__name__}"
        )
        assert old_result == new_result, "新版 load_json 對 data.json 的回傳值與舊版不一致"

    def test_character_json_equivalence(self):
        """
        輸入：data/Character.json（角色設定檔，一般 UTF-8 無 BOM）
        回傳：無
        功能：比對新舊 load_json 對 Character.json 回傳值完全相同。
        """
        from Script.Core import json_handle

        path = os.path.join(_REPO_ROOT, "data", "Character.json")
        assert os.path.exists(path), f"測試依賴的 Character.json 不存在：{path}"

        old_result = _old_load_json(path)
        new_result = json_handle.load_json(path)

        assert old_result == new_result, "新版 load_json 對 Character.json 的回傳值與舊版不一致"

    def test_ui_text_json_equivalence(self):
        """
        輸入：data/ui_text.json（UI 文字資料，一般 UTF-8 無 BOM）
        回傳：無
        功能：比對新舊 load_json 對 ui_text.json 回傳值完全相同。
        """
        from Script.Core import json_handle

        path = os.path.join(_REPO_ROOT, "data", "ui_text.json")
        assert os.path.exists(path), f"測試依賴的 ui_text.json 不存在：{path}"

        old_result = _old_load_json(path)
        new_result = json_handle.load_json(path)

        assert old_result == new_result, "新版 load_json 對 ui_text.json 的回傳值與舊版不一致"

    def test_bom_file_equivalence(self, tmp_path):
        """
        輸入：臨時 UTF-8 BOM JSON 檔（由測試動態建立）
        回傳：無
        功能：建立一個帶有 UTF-8 BOM 的 JSON 檔，比對新舊 load_json 回傳值相同。
              確認 BOM 偵測邏輯等價。
        """
        from Script.Core import json_handle

        # 建立帶有 UTF-8 BOM 的測試 JSON 檔
        bom_file = tmp_path / "test_bom.json"
        test_data = {"key": "value_with_chinese_中文測試", "number": 42, "list": [1, 2, 3]}
        bom_content = b"\xef\xbb\xbf" + json.dumps(test_data, ensure_ascii=False).encode("utf-8")
        bom_file.write_bytes(bom_content)

        bom_path = str(bom_file)
        old_result = _old_load_json(bom_path)
        new_result = json_handle.load_json(bom_path)

        assert old_result == new_result, "新版 load_json 對 UTF-8 BOM 檔的回傳值與舊版不一致"
        assert old_result == test_data, f"解析結果應等於原始資料，實際得到：{old_result}"

    def test_invalid_json_returns_empty_list(self, tmp_path):
        """
        輸入：損壞的 JSON 檔（由測試動態建立）
        回傳：無
        功能：確認新版 load_json 對無效 JSON 檔回傳空列表，與舊版行為一致。
        """
        from Script.Core import json_handle

        bad_file = tmp_path / "bad.json"
        bad_file.write_bytes(b"this is not valid json {{{{")

        bad_path = str(bad_file)
        old_result = _old_load_json(bad_path)
        new_result = json_handle.load_json(bad_path)

        assert old_result == [], f"舊版應回傳空列表，實際：{old_result}"
        assert new_result == [], f"新版應回傳空列表，實際：{new_result}"
        assert old_result == new_result, "新舊版對無效 JSON 的處理行為不一致"
