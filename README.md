# 🌀 ARIA v2.0: 複合地形風險與衝擊評估系統 (Integrated Impact Auditor)

本專案為 ARIA 系統的 2.0 升級版，主要針對極端降雨情境，整合向量資料（行政區界、河川水系、避難收容所）與網格資料（內政部 20m DEM 數值地形模型），進行「複合地形風險」的自動化評估。

## 🛠️ 技術工作流 (Workflow)

本系統依序執行以下核心步驟，實現從異質資料整合到風險視覺化的自動化流程：

1. **環境建置與參數動態載入 (Environment Setup)**
   * 建立 `.env` 檔案，動態管理風險參數（`SLOPE_THRESHOLD=30`, `ELEVATION_LOW=50`, `BUFFER_HIGH=500`）與目標縣市（預設為宜蘭縣）。
2. **向量資料預處理 (Vector Preprocessing)**
   * 載入消防署避難所與水利署河川圖資。
   * **CRS 統一**：全面將 GeoDataFrame 投影至 **EPSG:3826 (TWD97)**，確保空間距離計算（公尺）精準無誤。
   * 計算每個避難所距離最近河川的直線距離 (`river_distance_m`)。
3. **網格資料處理與坡度計算 (Raster Processing)**
   * 使用 `rioxarray` 載入高解析度 20m DEM。
   * 依據目標縣市的向量邊界進行**精準裁切 (Clip)**。
   * 運用 `numpy.gradient` 搭配空間解析度計算梯度，並轉換為實際地形「坡度 (Degrees)」。
4. **分區統計運算 (Zonal Statistics)**
   * 以避難所為中心建立 500 公尺環域 (Buffer)。
   * 運用 `rasterstats.zonal_stats` 提取環域內的 DEM 與坡度網格資料，得出各避難所周遭的 `mean_elevation` (平均高程) 與 `max_slope` (最大坡度)。
5. **複合風險邏輯判定 (Composite Risk Logic)**
   * 結合向量（距離）與網格（地形）數據進行綜合評估：
     * **極高風險 (CRITICAL)**：距離河川 < 500m 且 高程 < 50m，或周邊最大坡度 > 30度。
     * **高風險 (HIGH)**：距離河川 < 500m 且 高程 >= 50m，或周邊最大坡度 20~30度。
     * **中度風險 (MODERATE)**：距離河川 500~1000m，或周邊最大坡度 10~20度。
     * **低風險 (SAFE)**：距離河川 > 1000m 且 坡度 < 10度。
6. **視覺化與匯出 (Visualization & Export)**
   * 產製具備光影立體感的 Hillshade (地形陰影圖) 底圖。
   * 疊加依風險等級分色的避難所點位，輸出 `terrain_risk_map.png`。
   * 匯出最終分析結果至 `terrain_risk_audit.csv`。

---

## 📝 AI 診斷日誌：技術挑戰與預處理方案

處理龐大的 Raster (網格) 與 Vector (向量) 疊合時，極易發生效能與精度問題。本系統導入 AI 輔助診斷，實作了以下關鍵的防護與預處理機制：

### 1. 巨量網格資料記憶體溢出 (Memory Overflow / OOM)
* **診斷情境**：內政部 20m DEM 全台圖資檔案極大，若直接將整張圖讀入記憶體進行矩陣運算（如算坡度），會導致 Colab 執行環境崩潰。
* **預處理方案**：調整管線順序，採取**「先裁切，後運算」**策略。先利用目標縣市的向量邊界 (Polygon) 對 DEM 執行 `rio.clip`，產生極小範圍的子網格 (Sub-raster) 後，再進行 `np.gradient` 計算，大幅降低記憶體負載與運算時間。

### 2. 空間參考系統 (CRS) 不匹配與偏移
* **診斷情境**：避難所原始資料為 WGS84 (EPSG:4326)，而 DEM 為 TWD97 (EPSG:3826)。若直接進行 Buffer 或 Zonal Stats，會產生嚴重的空間錯位，導致抓取到錯誤的地形數據。
* **預處理方案**：在進入核心分析前，強制將所有 GeoDataFrame 執行 `.to_crs(epsg=3826)`，並利用 `rio.write_crs(3826, inplace=True)` 明確註冊 DEM 的座標系統，確保網格與向量的絕對對齊。

### 3. Zonal Statistics 的仿射轉換 (Affine Transform) 精度遺失
* **診斷情境**：呼叫 `rasterstats.zonal_stats` 時，若僅傳入 NumPy 陣列而未提供正確的空間對齊資訊，會導致統計結果出現大量 Null 值或讀取到錯誤的網格數值。
* **預處理方案**：明確提取裁切後 DEM 的 `affine` 矩陣與 `nodata` 值，並作為參數傳入 `zonal_stats`，確保運算視窗 (Window) 能精確對齊目標網格單元。

### 4. 坡度計算的單位轉換異常
* **診斷情境**：直接使用 `np.gradient` 計算出來的數值為「高程變化比值 (Rise over Run)」，並非作業邏輯門檻（如 30 度）所定義的「角度」，會導致風險分級邏輯全數失效。
* **預處理方案**：在梯度計算中，精確導入 DEM 的實際空間解析度 (Resolution, dx/dy)，並透過 `np.arctan()` 與 `np.degrees()` 函數，將比值正規化轉換為 0~90 度的真實地形坡度。

---

## 📂 產出檔案清單 (Deliverables)
* `ARIA_v2.ipynb`：完整分析原始碼
* `terrain_risk_map.png`：複合地形風險地圖
* `terrain_risk_audit.csv`：地形風險分析結果清單
