# erArk 測試套件

## 執行方式

從 repo 根目錄執行（需先確保 `data/*.json` 建置產物存在）：

```bash
python -m pytest tests/
```

### 執行所有測試（含慢速測試）

```bash
python -m pytest tests/ -m "slow or not slow"
# 或
python -m pytest tests/ --run-slow
```

### 只執行快速測試（預設）

```bash
python -m pytest tests/
```

### 執行特定測試層級

```bash
# L1 冒煙測試
python -m pytest tests/smoke/

# L2 特性測試（等價驗證）
python -m pytest tests/characterization/

# L3 單元測試
python -m pytest tests/unit/
```

## 目錄結構

```
tests/
  conftest.py              # sys.path 設定、最小 cache fixture
  smoke/
    test_build_and_boot.py # L1：模組 import、設定載入冒煙測試
  characterization/        # L2：重構前後等價驗證測試
  unit/                    # L3：各輪改動的專屬單元測試
  README.md                # 本說明文件
```

## 前置條件

1. 已安裝 pytest：`pip install pytest`
2. 已執行 `python buildconfig.py` 生成 `data/*.json` 建置產物
3. `config.ini` 存在於 repo 根目錄

## 測試標記

- `@pytest.mark.slow`：慢速測試（以 subprocess 跑建置腳本），預設跳過

## 注意事項

- 測試**只讀不寫**真實存檔，不會污染使用者遊戲資料
- `game.py` 會開 Tkinter GUI 並阻塞，故不在測試中直接呼叫
- 需從 repo 根目錄執行 pytest，確保工作目錄正確
