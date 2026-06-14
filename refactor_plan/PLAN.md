# erArk 效能重構計畫

> 本計畫由 Opus 模型規劃，後續交由 Sonnet 模型逐輪執行。
> 分支：`refactor/performance`（從最新 `release/dev` 切出）。
> **範圍：純效能重構，不含任何語言（簡轉繁）轉換。**

---

## 0. 約束與原則（必須嚴格遵守）

1. **功能不可變更或失效，也不可新增功能**。所有改動為等價重構。
2. **多輪次變更**：每輪一個 commit，且每個 commit 都必須是「獨立可運作」的狀態。
3. **每輪都要測試 + review** 後才提交。必要時撰寫測試，但測試**一律放在 `tests/` 資料夾**，
   不可混入原始碼層級。
4. Commit 訊息與分支命名遵循 Conventional Commits，且只用繁體中文或英文。
5. 任何一輪若無法通過冒煙或等價測試，**不得提交**，先回報。

### Commit 前綴規範

| 類型 | 前綴 | 範例 |
| --- | --- | --- |
| 效能重構 | `perf:` / `refactor:` | `perf(premise): 為單趟前提評估加入結果快取` |
| 測試基建 | `test:` / `chore:` | `test: 建立 tests/ 與 pytest 基礎設施` |

---

## 1. 關鍵背景（已驗證）

- **無既有測試框架**：專案沒有 `tests/`、`conftest.py` 或 pytest 設定，需從零建立（Round 0）。
- **效能熱點已勘查**，最高價值集中在：前提系統（開發者曾寫 `premise_profiler_patch.py` 量測，
  證實為熱點）、主行為迴圈、周目結算的全量 `deepcopy`、存檔讀寫、啟動期資料載入。
- **全域狀態耦合**：遊戲高度依賴全域 `cache`，測試需以「建構最小 cache 狀態 → 呼叫 → 斷言」進行。

---

## 2. Round 0：測試與驗證基礎建設（前置，先做）

**Commit：** `test: 建立 tests/ 與 pytest 驗證基礎設施`

建立與原始碼分離的測試目錄：

```
tests/
  conftest.py              # 設定 sys.path、提供最小 cache 初始化 fixture
  smoke/
    test_build_and_boot.py # L1 冒煙：buildconfig/init_data 成功、game.py 可啟動不崩潰
  characterization/        # L2 特性測試：純函式 before/after 等價
  unit/                    # L3 各輪改動的專屬單元測試
  README.md                # 說明如何執行：python -m pytest tests/
```

### 三層驗證策略

- **L1 冒煙測試**：以 headless 方式啟動 `game.py`（背景啟動 + 等待數秒確認未崩潰，沿用本專案
  已修正的 UTF-8 編碼），並確認 `buildconfig.py` / `init_data.py` 正常結束。
- **L2 特性測試（characterization）**：對「可獨立呼叫、輸入輸出明確」的純函式建立等價基準，
  例如 `attr_calculation.get_status_level`、`map_handle` 路徑轉換、特定 premise 函式。
  做法：建構最小全域狀態 → 呼叫函式 → 斷言輸出。重構前後必須完全一致。
- **L3 單元測試**：每個效能輪次針對其改動點補對應測試。

> `conftest.py` 需提供可重複建構最小 `cache` 狀態的 fixture。
> 測試**只讀不寫**真實存檔，避免污染使用者資料。

---

## 3. 效能重構輪次（由低風險到高風險，每輪一 commit）

> 每輪皆：寫/更新測試 → 跑 `pytest tests/` → L1 冒煙 → review → 才 commit。

### Round A1 — build/啟動期（極低風險）
**Commit：** `perf: 優化編譯與 JSON 載入的低效 I/O 與列表操作`
- `buildconfig.py:74-79`：在已複製列表上逐一 `.remove()`（O(n²)）→ 改用列表推導重建。
- `Script/Core/json_handle.py:4-22`：同檔被開兩次（BOM 偵測 + 讀取）→ 合併為單次 I/O；
  以 `json.load(f)` 取代 `json.loads(f.read())`。
- **驗證**：比對重構前後 `data/*.json` 編譯產物**位元組級一致**（最強的等價證明）；啟動冒煙。

### Round A2 — 主行為迴圈微優化（低風險）
**Commit：** `perf: 主迴圈與結算的迴圈不變量外提與查找快取`
- `Script/Design/character_behavior.py:64`：迴圈內 `set.copy()` 與每輪 `len(id_list)` → 外提。
- `Script/Design/settle_behavior.py`（186-191/301-306/197-199 等）：迴圈內重複
  `game_config.config_character_state[status_id]` → 一次取出存區域變數；預排序狀態列表於初始化時備好。
- `Script/Design/handle_npc_ai.py:738-777`：`list.remove()` 多次 → 改集合差運算。
- **驗證**：L2 特性測試（結算輸出等價）+ 冒煙。

### Round A3 — 前提結果單趟快取（中風險，效益高）
**Commit：** `perf(premise): 為單趟前提評估加入結果快取`
- 在 `handle_premise/__init__.py` 的 `get_weight_from_premise_dict` 與
  `handle_npc_ai.find_character_target` 的單次評估「趟次」內，對 `(character_id, premise_id)`
  結果做快取，趟次結束即丟棄，避免跨狀態污染。
- 全 NPC 遍歷型前提（`handle_premise_fall.py` 的 `handle_player_have_other_lover/pet` 系列 623-725）
  改為趟次快取或預建索引。
- **風險控管**：快取生命週期**僅限單次評估趟次**；任何可能改變角色狀態的點之後必須失效。
  附等價測試：同一 cache 狀態下，加快取前後所有相關 premise 回傳值一致。

### Round A4 — 前提內部子計算（中風險）
**Commit：** `perf(premise): 快取場景資料查找並優化 CVP 字串解析`
- `handle_premise_place.py:33-50` `common_place_judge_by_SceneTag` 等：單趟內快取位置/場景資料。
- `handle_premise/__init__.py` `handle_comprehensive_value_premise`（265-344）：
  多個 `"X" not in ...` → 改 set 判斷；玩家交互對象（311-314）查詢於趟次入口快取。
- **驗證**：CVP 相關特性測試 + 冒煙。

### Round A5 — 存檔/周目（中高風險，單一最大效益）
**Commit：** `perf: 以索引取代周目/存檔的巢狀掃描與全量深拷貝`
- `Script/Core/save_handle.py:306-312`：設施↔NPC 巢狀迴圈（O(設施×NPC)）→ 預建 `adv_id→cid` 索引。
- `Script/UI/Panel/new_round.py:626/709/757`：周目繼承的 `copy.deepcopy` 全量拷貝 →
  **先用工具精確列出所有讀取欄位**，再改為僅選擇性深拷貝必要欄位（不拷貝不變的設定/場景資料）。
- `save_handle.py` `recursive_update`：評估改用 `__dict__.update`（需先確認語義等價）。
- **驗證**：本輪需**最嚴格**的前後等價測試 —— 同一輸入存檔/周目資料，繼承結果（好感、能力、
  經驗、素質等所有欄位）必須與舊路徑完全一致。保留舊 deepcopy 路徑作為測試對照。

### Round A6 —（可選/提案）存檔序列化拆分
- `save_handle.py` 以 pickle 全量序列化整個 `cache`（含數百 NPC）→ 存檔耗時秒級。
- 提案：分離常變資料 vs 靜態設定，或增量存檔。
- 風險：動存檔架構、牽涉跨版本相容。**預設不做**，待單獨討論後再決定是否納入。

---

## 4. 建議執行順序

1. **Round 0**（測試基建）
2. **A1 → A2 → A3 → A4 → A5**（每輪：測試→冒煙→review→commit）
3. A6 視情況單獨討論。

---

## 5. 風險控管與回滾

- 每輪皆獨立 commit → 出問題可單獨 `git revert`。
- 高風險輪（A5）保留舊路徑作測試對照，前後等價測試通過才提交。
- 任何一輪若無法通過冒煙或等價測試，**不得提交**，先回報。
