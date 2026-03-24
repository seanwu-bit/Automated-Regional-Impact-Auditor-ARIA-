🌀 ARIA v3: 鳳凰颱風動態避難風險評估系統 (Fungwong)
本專案開發於 2026 年 3 月，旨在針對颱風期間的花蓮與宜蘭地區，整合 CWA 氣象即時數據、W4 地形風險圖資與 Gemini AI 戰術建議，建構一套自動化的動態災防儀表板。

🛠️ 技術工作流 (Workflow)
本程式依據以下五個核心階段進行自動化運算：

Step 1: 資料獲取與正規化 (Data Acquisition)

讀取 .env 配置（支援 LIVE 實時模式與 SIMULATION 模擬模式）。

透過 CWA API 抓取全台雨量站 JSON，並進行欄位正規化，統一提取 rain_1hr, rain_3hr, rain_24hr。

Step 2: 地理編碼與預處理 (Geoprocessing)

載入避難所 CSV 並轉換為 GeoDataFrame。

執行座標轉換，將原始經緯度 (EPSG:4326) 投影至 EPSG:3826 (TWD97) 以進行精確的公尺級空間運算。

Step 3: 空間分析與動態風險分級 (Spatial Analysis)

環域判定：以強降雨測站為中心建立 5 公里 Buffer。

精準配對：使用 sjoin_nearest 將每個避難所綁定地理距離最近的測站。

矩陣分級：結合「地形風險」與「即時降雨」判定四個風險等級：CRITICAL, URGENT, WARNING, SAFE。

Step 4: 地圖可視化繪製 (Folium Mapping)

建構互動式地圖，整合 HeatMap (降雨熱區)、雨量站點（半徑隨雨量動態變化）與避難所標記。

Step 5: AI 戰術顧問與最終輸出 (AI Tactical Advisor)

針對指揮官指定的避難所目標，將即時觀測數據餵給 Gemini 2.5 Flash。

生成具體的防災應變建議，並以「紫色星星」醒目提示於地圖 Popup 中。

📝 AI 診斷日誌：開發挑戰與解決方案
在開發過程中，我們遇到了數個關鍵技術障礙，並透過以下程式邏輯予以解決：

1. 數據「消失」與 0mm 顯示錯誤
問題：在 Spatial Join 之後，避難所的 Popup 顯示雨量為 0mm，但測站明明有數據。

成因：左側避難所資料表原先存在同名的空欄位，導致 gpd.sjoin 產生 rain_1hr_right 衝突，導致主邏輯讀取不到數值。

解決方案：在執行 Join 前，強制執行 drop(columns=...) 清除避難所所有舊有的雨量與測站欄位，確保數據「強制覆蓋」並維持欄位名稱純淨。

2. 最近測站配對不準確
問題：避難所顯示的不是地理上最近的測站。

成因：初版邏輯使用 sjoin (intersects) 判斷，若點落在多個環域重疊區，會隨機選取或選取雨量最大者，而非最近者。

解決方案：引進 gpd.sjoin_nearest。這保證了不論距離遠近，每個避難所都能精準鎖定絕對距離最短的氣象站，實現「一所一站」的精確觀測配對。

3. Gemini API 404/503 異常
問題：呼叫 AI 時出現 404 Not Found 或 503 Service Unavailable。

成因：Google 持續更新模型名稱（如從 1.5 升級至 2.5），且免費版 API 易受伺服器負載影響。

解決方案：

自動偵測：程式碼加入 genai.list_models()，自動搜尋當下環境中可用的最新 Flash 模型。

重試機制 (Retry Logic)：針對 503 錯誤加入 3 次自動重試（間隔 5 秒），確保在高負載時仍有機會取得建議。

4. 空間結合索引衝突 (index_right)
問題：連續執行兩次空間結合時報錯 ValueError: 'index_right' cannot be a column name。

解決方案：在第二次結合前手動偵測並刪除 index_right 欄位，確保空間運算的管道 (Pipeline) 暢通無阻。

🛡️ 預先部署的防範機制 (Hardening)
時雨量優先原則：若避難所同時受多個警戒區影響，系統自動以 rain_1hr (時雨量) 進行降冪排序並去重，優先呈現最具威脅性的即時雨勢。

資料正規化防呆：針對 CWA JSON 欄位（如 Past1hr 與 Past1Hr）的大小寫差異進行模糊匹配，防止因氣象署 API 更新欄位命名而導致系統當機。

Google Drive 自動備份：預設路徑指向 /content/drive/MyDrive/ARIA_outputs/，確保在 Colab 工作階段斷開後，產出的 .html 檔案仍妥善儲存於雲端。