# 🌊 ARIA Project: Automated Regional Impact Auditor
**全台河川避難所綜合風險評估與韌性稽核系統**

本專案結合地理空間分析 (GIS) 與數據科學，針對台灣各行政區進行河川洪災避難資源的「韌性稽核」。透過自動化腳本分析避難設施的空間分佈安全性與資源缺口，為防災決策提供科學化依據。

註：因檔案大小問題，Windsurf上傳專案有網路超時問題，故本次檔案係以手動方式上傳。

---

## 🤖 AI 協作診斷日誌 (AI Diagnostic Log)

本專案開發過程中，透過 AI 協作進行了深度的技術排除與邏輯預處理，確保大規模 GIS 運算既精確又具備決策意義。

### 🐛 關鍵錯誤排除 (Debugged Issues)

* **SSL 憑證與 API 連線錯誤 (`SSLCertVerificationError`)**
    * **現象**：直接讀取政府 Open Data API 時，因安全性憑證驗證失敗導致下載中斷。
    * **排除**：改採本機圖資管理，並使用原生字串處理路徑，確保讀取穩定。
* **核心運算卡死 (`Kernel Pending`)**
    * **現象**：河川圖資節點數過大，執行 `buffer` 與 `sjoin` 時耗盡記憶體。
    * **排除**：引入 `.simplify(50)` 幾何簡化技術，在不影響精度前提下降低 90% 運算負擔。
* **變數生存期遺失 (`NameError`)**
    * **現象**：重啟 Kernel 後導致分析結果遺失，視覺化階段報錯。
    * **排除**：實施數據持久化機制，將結果即時存入 `outputs/`，視覺化模組自動偵測並讀取緩存。
* **欄位名稱不匹配 (`KeyError`)**
    * **現象**：`reset_index()` 後標題因編碼問題無法被讀取。
    * **排除**：導入「強健索引技術」，改用 `iloc[:, 0]` 絕對位置抓取標籤。
* **圖表排版重疊 (`Layout Overlap`)**
    * **現象**：三 Y 軸圖表標題與圖例空間擠壓。
    * **排除**：調校 `subplots_adjust` 與 `bbox_to_anchor` 參數，預留頂部空間，確保報表規格。

---

### ⚙️ 系統預處理 (Preprocessing & Logic Optimizations)

在Gemini Prompt中預先植入以下邏輯處理：

* **空間坐標系標準化 (CRS Alignment)**：
    將所有圖資統一預處理為 **EPSG:3826** (TWD97 投影坐標)，確保緩衝區距離計算為精確的「公尺」。
    
* **幾何特徵預處理 (Geometry Simplification)**：
    在空間交集前簡化河道節點，大幅提升大規模地理資料之運算效率。
    [Image of GIS spatial join and buffer analysis]

* **多重依賴權重工程 (Weighted Feature Engineering)**：
    捨棄單一數量指標，改採 **「空間依賴權重 (Dependency Score)」** 指標：
    $$Dependency Score = \frac{(High \times 3 + Med \times 2 + Low \times 1)}{Total Count}$$
    
* **跨維度指標正規化 (Min-Max Normalization)**：
    將「空間依賴度」與「人數缺口」縮放至 $0 \sim 1$ 區間再進行加權排名，避免規模數據掩蓋脆弱性指標。
    [Image of normalization process in data analysis]

* **地方審計自動化模組 (Regional Audit Automation)**：
    預先撰寫名稱校正邏輯與篩選器，支援一鍵生成特定縣市的局部審計報告。

