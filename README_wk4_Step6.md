# Step 6: 避難所地形風險資料匯出

## 概述
Step 6 是 ARIA_v2 系統的最後一個工作階段，專門用於生成包含完整地形風險分析的避難所 CSV 檔案。

## 功能特色
- **動態檔案命名**：根據 `.env` 中的 `TARGET_COUNTY` 自動生成檔案名稱（如：`宜蘭_shelter_data.csv`）
- **完整風險欄位**：新增 5 個地形風險相關欄位
- **UTF-8 編碼**：支援 Excel 直接開啟中文內容
- **統計摘要**：提供詳細的風險分佈統計

## 新增欄位說明
| 欄位名稱 | 說明 | 單位 |
|---------|------|------|
| `risk_level` | 地形風險等級 | 極高風險/高風險/中風險/低風險 |
| `max_slope` | 最大坡度 | 度 |
| `mean_elevation` | 平均高程 | 公尺 |
| `std_elevation` | 高程標準差（地形起伏度） | 公尺 |
| `river_distance_m` | 到最近河川的距離 | 公尺 |
| `river_distance_category` | 河川距離分類 | <500m/<1000m/>1000m |

## 使用方法

### 方法一：在 Notebook 中執行
在 ARIA_v2.ipynb 的最後一個 cell 中執行：

```python
# 執行 Step 6
%run step6_export_shelter_data.py
```

### 方法二：直接執行 Python 檔案
```bash
python step6_export_shelter_data.py
```

## 輸出檔案
- **檔案位置**：`outputs/{TARGET_COUNTY}_shelter_data.csv`
- **編碼格式**：UTF-8 with BOM
- **相容性**：可直接在 Excel 中開啟，中文顯示正常

## 輸出範例
```
宜蘭_shelter_data.csv
├── 避難收容處所名名稱
├── risk_level (地形風險等級)
├── max_slope (最大坡度)
├── mean_elevation (平均高程)
├── std_elevation (高程標準差)
├── river_distance_m (河川距離)
├── river_distance_category (河川距離分類)
├── 經度, 緯度 (原始座標)
└── 其他原始避難所資訊...
```

## 注意事項
1. 請確保已完成 Step 1-5 的所有計算
2. 需要存在 `target_shelters` 和 `rivers_in_county` 變數
3. `.env` 檔案中的 `TARGET_COUNTY` 必須正確設定

## 統計輸出
執行完成後會顯示：
- 總避難所數量
- 各風險等級的分佈統計
- 前 3 筆資料預覽
- 檔案儲存路徑
