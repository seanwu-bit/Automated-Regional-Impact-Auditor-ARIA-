##🌀 ARIA v2.0: 全自動區域受災衝擊評估系統 (地形整合版)##
本專案為 ARIA 系統的 2.0 升級版，針對特定縣市（預設為宜蘭縣）的避難收容所，整合向量資料（河川、行政區界）與網格資料（內政部 20m DEM），進行極端降雨情境下的「複合地形風險」評估。

🛠️ 技術工作流 (Workflow)
本分析流程主要分為六個核心步驟：

環境建置與參數設定 (Environment Setup)

讀取 .env 設定檔，動態載入風險門檻參數（如 SLOPE_THRESHOLD=30, ELEVATION_LOW=50, BUFFER_HIGH=500）與目標評估縣市。

自動下載內政部 20m DEM 網格資料、水利署河川圖資與消防署避難所向量資料。

向量資料預處理 (Vector Preprocessing)

將避難所與河川資料統一投影至 EPSG:3826 (TWD97)，確保後續空間計算單位為公尺。

裁切目標縣市範圍，並計算每個避難所距離最近河川的直線距離 (river_distance_m)。

網格資料處理與坡度計算 (Raster Processing & Slope Calculation)

使用 rioxarray 載入 DEM，並依據目標縣市的幾何邊界進行精確裁切 (Clip)，大幅降低記憶體消耗。

運用 numpy.gradient 搭配 DEM 的像素解析度 (Resolution)，計算每個網格單元的坡度，並轉換為「度數 (Degrees)」。

空間分析與分區統計 (Zonal Statistics)

以各避難所為中心，建立 500 公尺半徑的環域 (Buffer)。

透過 rasterstats.zonal_stats 提取每個環域內的 DEM 與坡度網格資訊，計算出各避難所周遭的「平均高程 (mean_elevation)」與「最大坡度 (max_slope)」。

複合風險邏輯判定 (Composite Risk Logic)

結合向量與網格分析結果，依據複合條件矩陣進行風險分級：

極高風險 (Critical)：距離河川 < 500m 且 高程 < 50m，或周邊最大坡度 > 30度。

高風險 (High)：距離河川 < 500m 且 高程 >= 50m，或周邊最大坡度 20~30度。

中度風險 (Moderate)：距離河川 500m~1000m，或周邊最大坡度 10~20度。

低風險 (Low)：距離河川 > 1000m 且 坡度 < 10度。

視覺化與資料匯出 (Visualization & Export)

產生帶有光影立體感的地形陰影圖 (Hillshade) 作為底圖，疊加依風險等級分色的避難所點位，輸出 terrain_risk_map.png。

彙整最終分析結果，匯出 terrain_risk_audit.csv 供後續決策與 GIS 軟體使用。

📝 AI 診斷日誌 (AI Diagnostic Log)
在開發與處理異質空間資料（Vector + Raster）的過程中，系統實作了以下除錯與預處理機制：

1. 空間參考系統 (CRS) 不匹配防護
診斷情境：原始避難所資料為 EPSG:4326，河川資料為 EPSG:3826，而 DEM 雖標示為 EPSG:3826 但若未嚴格對齊，會導致 Spatial Join 或環域計算發生嚴重位移與報錯。

預處理方案：在所有空間運算（Buffer, Zonal Stats, Clip）發生前，強制執行 .to_crs(epsg=3826)，並在讀取 DEM 時透過 rio.write_crs(3826, inplace=True) 確保網格資料的座標系統正確註冊。

2. 巨量網格資料 (Large Raster) 記憶體溢出
診斷情境：全台 20m DEM 檔案龐大，若直接在全台範圍進行矩陣的坡度計算 (np.gradient)，極易造成執行環境記憶體不足 (OOM) 而崩潰。

預處理方案：改變運算順序。先利用向量的縣市邊界對 DEM 執行 rio.clip 裁切，僅針對目標縣市範圍產生小範圍子網格 (Sub-raster) 後，再進行矩陣運算，有效將記憶體消耗與運算時間降至最低。

3. Zonal Statistics 的仿射轉換 (Affine Transform) 精度丟失
診斷情境：將 GeoDataFrame 的 Polygon 傳入 rasterstats 時，若未正確給予裁切後 DEM 的 Transform 屬性，會抓取到錯誤的網格數值或產生大量 Null 值。

預處理方案：明確提取裁切後 DEM 的 affine 矩陣與 nodata 值，確保 zonal_stats 函式能精確對齊網格與向量邊界，並妥善排除無效網格值的干擾。

4. 坡度計算的單位轉換異常
診斷情境：直接使用 NumPy 梯度計算出來的數值為比值 (Rise over Run)，而非直觀的角度，會導致後續 SLOPE_THRESHOLD 的邏輯判斷完全失效。

預處理方案：在梯度計算中精確除以 DEM 的實際空間解析度 (Resolution, dx/dy)，並透過 np.arctan 與 np.degrees 將弧度轉為角度，確保坡度數值精準落在 0~90 度的合理物理範圍內。
