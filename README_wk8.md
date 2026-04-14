# 🛰️ 遙測災損稽核：馬太鞍溪堰塞湖與土石流事件 (Sentinel-2 光學影像分析)

本專案利用 Microsoft Planetary Computer 串流 Sentinel-2 L2A 衛星影像，針對馬太鞍溪堰塞湖潰決事件進行「災前、災中、災後」的三幕劇 (Three-Act) 變遷偵測。透過結合光譜指標、空間型態學與 GIS 緩衝區分析，驗證並修補了災前 ARIA 防災節點的覆蓋缺口。

---

## 🚀 核心工作流與演算法優化 (Workflow & Optimizations)

在標準的變遷偵測 (Change Detection) 基礎上，本專案針對實際地理特徵進行了多項深度優化：

### 1. 影像視覺增強 (S5)
* **優化：** 實作「激進型直方圖拉伸 (Histogram Stretching)」，將百分位數限縮至 `5% ~ 92%` 並加入亮度增益 (`gain=1.2`)。
* **成效：** 消除大氣散射的霧感，使三幕劇面板 (Pre/Mid/Post) 中的崩塌地與堰塞湖在肉眼視覺上達到最佳對比度。

### 2. 堰塞湖高濁度孔洞修補 (S7)
* **優化：** 導入 `scipy.ndimage.binary_fill_holes` (空間形態學填補)。
* **成效：** 解決了因漂流木或極端高濁度泥漿導致的「瑞士起司效應 (Swiss Cheese Effect)」，在嚴格的光譜門檻下 (`th=0.195`) 仍能獲得平滑飽滿的水體遮罩，精準對位 NCDR 官方紀錄的 0.86 km²。

### 3. 三引擎土石流遮罩與縫合 (S9)
* **優化：** 放棄單一的破壞偵測，改用「三引擎邏輯 (Triple-Engine)」：
  1. 溢流破壞區 (NDVI 降 + BSI 升)
  2. 濕潤泥沙主體 (絕對 BSI 高 + 紅光亮)
  3. 乾燥邊緣/類崩塌 (借用 Landslide 的 NIR 降 + SWIR 升邏輯)
* **進階處理：** 加入去雲濾鏡 (`B02 > 0.20`)，並使用 `7x7` 結構核心進行形態學閉合 (`binary_closing`)。
* **成效：** 成功抓出傳統邏輯會漏判的「既有河道土石流主體」，並將破碎的像素縫合成一條完整的破壞足跡。

### 4. 功能性毀損鑑定與空間緩衝 (S12b)
* **優化：** 捨棄死板的點面交集 (`intersects`)，為防救災節點 (W3/W7/W8) 加上 `20m Spatial Buffer`。
* **成效：** 解決「空間交集盲點 (Spatial Intersection Fallacy)」。成功捕捉到未被土石流直接命中，但周圍聯外道路已被完全包圍、實質上已「功能性毀損」的關鍵節點 (如光復國小、馬太鞍溪橋)。

---

## ⚠️ 方法學限制：高估誤差與人機協作 (Limitations & HITL)

儘管導入了三引擎與空間形態學大幅提升了災害捕捉率，但本演算法仍存在固有缺陷：
* **面積高估 (Overestimation)：** 為了強制縫合斷裂的土石流足跡（使用 Dilation/Closing 膨脹運算），演算法必然會將部分安全的微小間隙吞沒，導致程式內部計算的「災害面積」大於實際絕對值。
* **人機協作 (Human-in-the-Loop) 的必要性：** 系統產出的遮罩與交集數字（如 Impact Table）僅為**「警示候選名單」**。實務上仍需依賴人類專家進行視覺驗證 (Visual Verification)，手動剔除因形態學膨脹而誤判的邊緣，或排除光譜特徵相似但顯然非災害區的正常裸地。

---

## 🤖 AI 診斷日誌與系統防呆機制 (Comprehensive Diagnostic Log)

本專案在開發與執行過程中，遭遇了雲端運算、遙測物理學與 GIS 空間分析等三大領域的典型挑戰。以下為完整的除錯紀錄與預先部署的防呆機制：

### 🛑 階段一：環境部署與基礎設施 (Infrastructure & Environment)
1. **GDAL/Rasterio 警告洗版干擾**
   * **問題：** 執行 `stackstac` 時，底層引擎不斷噴出 `CPLE_NotSupported in warp options` 警告，導致 Colab 畫面嚴重冗長。
   * **對策：** 於全域環境注入 `os.environ['GDAL_QUIET'] = 'YES'` 與 `CPL_LOG = /dev/null`，強制靜音底層 C++ 警告，維持版面整潔。
2. **雲端硬碟掛載與檔案遺失 (`FileNotFoundError`)**
   * **問題：** Colab 預設路徑無 `output/` 資料夾，且重置後圖檔會蒸發。
   * **對策：** 建立絕對路徑變數 `OUTPUT_DIR = "/content/drive/MyDrive/ARIA_outputs"`，並加入 `os.makedirs(exist_ok=True)` 確保目錄自動生成，實現跨 Session 的檔案持久化。
3. **SAS Token 存取權限過期 (`CPLE_OpenFailedError`)**
   * **問題：** Planetary Computer 的 blob 儲存憑證僅有 1 小時壽命，導致放置一段時間後 Lazy Compute 觸發 403 錯誤或 IO 崩潰。
   * **對策：** 將 `pc.sign(item)` 寫入每次的 `stream_cube` 函式中，並建立除錯 SOP：遇到讀取錯誤時，退回 `[S5]` 重新執行刷新憑證即可。

### 🛑 階段二：演算法邏輯與遙測物理 (Remote Sensing Physics)
4. **影像顯示暗淡與對比度不足**
   * **問題：** 預設的 2%~98% 直方圖拉伸在山區帶有嚴重霧感，難以辨識災害邊緣。
   * **對策：** 開發「激進型拉伸濾鏡」，將百分位數限縮至 `5% ~ 92%` 並套用 `gain=1.2` 亮度增益，顯著強化視覺對比。
5. **堰塞湖遮罩的瑞士起司效應 (Swiss Cheese Effect)**
   * **問題：** 漂流木與高濁度泥漿導致湖中心出現極亮像素，被傳統水體門檻排除，造成多邊形佈滿孔洞。
   * **對策：** 導入空間形態學 `scipy.ndimage.binary_fill_holes`，以物理空間邏輯強制填補被水體包圍的內部空洞，精準吻合 NCDR 0.86 km² 之紀錄。
6. **土石流變遷盲點 (Change Detection Blind Spot)**
   * **問題：** Baseline 邏輯限制了「災前必須是茂密植被 (`nir_pre > 0.20`)」，導致演算法只抓到農田邊緣，卻完全忽略了既有河道上最厚實的灰色泥沙主體。
   * **對策：** 升級為**「三引擎土石流邏輯 (Triple-Engine)」**，除了破壞偵測外，新增「絕對裸土主體 (Absolute BSI)」與「乾燥礫石邊緣 (Landslide-like)」邏輯，完美縫合巨大泥流足跡。
7. **土石流足跡的異質性碎裂 (Heterogeneity Fragmentation)**
   * **問題：** 雲層干擾與地表複雜度讓土石流呈現斷裂的椒鹽雜訊。
   * **對策：** 結合藍光去雲濾鏡 (`B02 > 0.20`)，並套用 `7x7` 結構核心進行形態學閉合 (`binary_closing`)，將碎片融合成平滑連貫的流動實體。

### 🛑 階段三：GIS 空間交集與視覺化 (GIS Spatial Analysis)
8. **跨圖層交集判定全數歸零 (CRS Mismatch)**
   * **問題：** W3/W7/W8 節點與災害網格交集全數為 `False`。
   * **對策：** 抓出座標系統不匹配之致命傷。強制將外部輸入的 `EPSG:4326/3826` 向量資料，透過 `.to_crs()` 重新投影至與衛星影像一致的 `EPSG:32651`。
9. **空間交集盲點與漏判 (Near-Miss Fallacy)**
   * **問題：** 點位幾何剛好落於 10m 網格的縫隙中，造成視覺上已遭吞沒，運算卻判定安全的矛盾。
   * **對策：** 實作 `[S12b]` 功能性毀損鑑定，為所有節點加上 `20m Spatial Buffer`，成功校正了低估的交集命中率。
10. **局部放大地圖的「空包彈」 (Hardcoded Bounds Error)**
    * **問題：** 繪製驗證圖時使用寫死的座標中心，導致因範圍微調而輸出全白畫面。
    * **對策：** 撰寫「智慧同框導航」邏輯，動態讀取 W7 與 W8 幾何的 `total_bounds`，自動計算最大邊界框並外擴 `1000m padding`，實現完美的動態構圖。
