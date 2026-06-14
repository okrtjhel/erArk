import json


def load_json(file_path: str) -> dict:
    """
    載入 JSON 檔案
    輸入：
        file_path (str)：JSON 檔案路徑
    回傳：
        dict | list：解析後的 JSON 資料；讀取失敗時回傳空列表
    功能：
        以單次 I/O 讀取 JSON 檔案，自動識別 UTF-8 BOM（utf-8-sig）與一般 UTF-8。
        原實作需開啟兩次檔案（先偵測 BOM、再讀取），此版本合併為一次 open，
        並以 json.load(f) 直接從檔案物件解析，避免額外 str 轉換。
        功能與原實作完全等價。
    """
    # 以二進位模式讀取前 3 個位元組，判斷是否有 UTF-8 BOM
    with open(file_path, "rb") as fb:
        header = fb.read(3)
    ec = "utf-8-sig" if header == b"\xef\xbb\xbf" else "utf-8"
    # 單次開啟，使用 json.load(f) 直接從 file object 解析，等價於原本的 json.loads(f.read())
    with open(file_path, "r", encoding=ec) as f:
        try:
            json_data = json.load(f)
        except json.decoder.JSONDecodeError:
            print(file_path + "  无法读取，文件可能不符合json格式")
            json_data = []
    return json_data
