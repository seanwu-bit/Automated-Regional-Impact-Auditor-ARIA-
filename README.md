# ARIA v4.0 - Disaster Accessibility Assessment System (Yilan)
**宜蘭市災後交通可達性與孤島效應評估系統**

## 📝 專案概述 (Project Overview)
本專案（ARIA v4.0）旨在透過路網分析技術，評估極端氣象（如鳳凰颱風降雨情境）對宜蘭市交通可達性的衝擊。系統透過計算關鍵節點（Bottlenecks）、動態壅塞路網權重（Dynamic Weights）、以及災前/災後等時線面積縮水率（Isochrone Shrinkage），來找出因淹水或路斷而形成的「交通孤島」，最後結合大型語言模型（Gemini API）自動生成災防戰略報告。

---

## ⚙️ 工作流程 (Workflow)

本系統依據以下步驟自動化執行分析：

1. **Part A: 基礎路網萃取 (Network Extraction & Archiving)**
   - 透過 `.env` 讀取環境變數（設定區域為 `Yilan City, Taiwan`，半徑 `5000m`）。
   - 使用 OSMnx 獲取路網，投影至 `EPSG:3826`，計算基準旅行時間 `travel_time`。
   - 實作 GraphML 快取機制，避免重複下載。
2. **Part B: 瓶頸與風險診斷 (Bottleneck & Risk Diagnosis)**
   - 計算路網中介中心性 (Betweenness Centrality)，找出 Top 5 關鍵樞紐節點。
   - 將地形風險 (Terrain Risk) 與關鍵節點疊圖 (Spatial Join)。
3. **Part C: 動態可達性分析 (Dynamic Accessibility)**
   - 讀取 Kriging 降雨網格資料 (GeoTIFF)，透過空間座標萃取各路段的降雨量。
   - 套用 `rain_to_congestion` 函數，將降雨量轉換為壅塞係數 (cf: 0.0 ~ 0.95)，並據此計算災後旅行時間 `travel_time_adj`。
   - 針對 5 個關鍵設施，分別計算災前與災後 **固定時間門檻 (5分鐘 / 10分鐘)** 的可達範圍面積與縮水率 (Shrinkage %)。
4. **Part D: 視覺化對比 (Visualization)**
   - 產出 5 組（共 10 張）災前災後等時線對比圖，直觀呈現藍色 (10 min) 與紅色 (5 min) 多邊形範圍的變化，並將縮減率標示於圖例中。
5. **Part E & F: AI 戰略報告 (AI Strategy Briefing)**
   - 將可達性衝擊 DataFrame 轉化為 Prompt。
   - 透過 Colab Secrets 安全連線至 Google Gemini API (`gemini-2.5-flash`)，自動生成具備 Markdown 排版的災防搶修建議與資源分配報告。

---

## 🛠️ AI 診斷日誌 (AI Diagnostic Log)
*記錄開發過程中遭遇之困難與解決方案，符合作業規範之除錯紀錄。*

### 1. 降雨資料對應錯誤 (JSON Node ID Mismatch vs Kriging Raster)
- **Issue**: 最初嘗試讀取 Week 5 的 JSON 降雨資料並對應到 OSM 路網時，發現所有路段的壅塞係數 (`cf`) 皆為 0。經診斷發現，JSON 的 Key 是「氣象站名稱」，而迴圈中的變數是「OSM Node ID」，兩者無法匹配。
- **Solution**: 捨棄 JSON，改用 Week 6 的 `kriging_rainfall.tif` (Option A)。透過提取所有 Node 的 `(X, Y)` 座標，並使用 `rasterio.sample(coords)` 直接從網格圖層中抽取降雨數值，完美解決了空間資料對應的問題。*(Matches homework requirement: "Kriging raster sampling")*

### 2. 道路速限屬性缺失與格式異常 (Missing Road Speed Attributes)
- **Issue**: 在計算基準 `travel_time` 時，發現 OSMnx 的 `maxspeed` 屬性時常缺失，甚至有時會以 List (如 `['40', '50']`) 或字串 (如 `'50 mph'`) 的形式存在，導致數學運算報錯。
- **Solution**: 實作了防呆函數 `get_speed(data)`。利用型別檢查 (`isinstance`) 剝離 List 並過濾非數字字元。若完全缺乏速限，則依據道路等級 (`highway`) 賦予預設值 (如 40 km/h)，確保所有路段都能順利算出基礎時間。

### 3. 等時線比較基準不一致 (Adaptive vs Fixed Thresholds)
- **Issue**: 系統最初採用「自適應門檻 (Adaptive Thresholds)」來繪製比較圖。這導致災前災後各自計算出了不同的時間標準（例如災前 15/30 分鐘，災後變成 25/46 分鐘），在視覺上多邊形大小相似，無法直觀看出「相同時間下的範圍縮減」。
- **Solution**: 嚴格遵守作業規範，將系統強制修改為**固定門檻 (Fixed 5-min & 10-min)**。並將計算邏輯拆分，先算出面積與 Shrinkage %，再傳入繪圖模組，使得左右對照圖極具說服力。

### 4. API 金鑰外洩與安全性封鎖 (API Key Leaked 403 Error)
- **Issue**: 嘗試呼叫 Gemini API 產製報告時，遭遇 `403 Your API key was reported as leaked` 錯誤。因初期將 `.env` 或金鑰不小心曝露，導致被 Google 安全機制阻擋。
- **Solution**: 廢棄舊金鑰並重新生成。為適應 Google Colab 環境，捨棄 `.env` 檔案，改用 Colab 內建的機密管理員 (`from google.colab import userdata`) 讀取金鑰，徹底解決資安風險。

### 5. 多邊形生成異常與除以零防護 (Polygon Anomalies & Zero Division)
- **Issue**: 當災情過於嚴重導致 5 分鐘內無節點可達時，多邊形面積為 0，會導致 Shrinkage 計算出現 `ZeroDivisionError`。
- **Solution**: 引入了 `if area_before > 0 else 0` 的三元運算子防護機制；並利用 `shapely` 的 `convex_hull` 確保算出的多邊形形狀穩定。

---

## 📊 核心結論摘要 (Core Findings)
依據本系統運算與 AI 戰略報告指出：
1. **最高脆弱度樞紐**：特定中心性極高（Centrality > 0.15）的節點在降雨後可達面積大幅縮水，是道路搶險的首要目標。
2. **長程運輸癱瘓**：部分設施的 10 分鐘可達面積縮水率高達 100%，顯示長距離的聯外道路已完全中斷，必須即刻啟動直升機或橡皮艇等替代救援方案。