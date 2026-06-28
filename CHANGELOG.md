# 版本更新日誌 (Changelog)

本專案的所有重大更新與版本變更都將記錄於此檔案中。

本更新日誌格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/)，
並嚴格遵循 [語義化版本 (Semantic Versioning)](https://semver.org/lang/zh-TW/) 規範。

---

## [1.1.0] - 2026-06-28

### 新增 (Added)
- **GPT-Realtime-Translate 主流程**：新增 `/api/realtime-translation-session`，由後端建立 OpenAI Realtime Translation 短效 `client_secret`。
- **Realtime 翻譯逐字稿**：`gpt-realtime-translate` 連線時同步接收翻譯 transcript delta，供投屏字幕使用。
- **WebRTC 語音到語音同譯**：前端 `GPT-Realtime 語音同譯` 模式改為 WebRTC 直連 OpenAI Realtime Translation Calls API，支援翻譯後語音播放。
- **輸出語言選擇器**：投屏控制列新增輸出語言選單，預設輸出英文。

### 改進 (Improved)
- **單模型主流程**：Web 產品移除舊片段上傳模式與 `/api/translate-audio`，現階段只使用 `gpt-realtime-translate`。
- **OpenAI 金鑰診斷更安全**：後端錯誤回傳改用遮罩提示，避免把 API Key 前後綴完整暴露在投屏畫面。
- **部署環境支援**：`.env.example` 新增 `OPENAI_API_KEY`，可由 Vercel 環境變數供後端換取 Realtime 短效憑證。

## [1.0.0] - 2026-06-28

### 新增 (Added)
- **核心網頁應用 (SPA)**：使用 **FastAPI** 和 **原生 HTML5/JS** 打造即時語音同譯與大會投屏網頁。
- **極速同譯引擎**：整合 **Groq Whisper API** (`whisper-large-v3-turbo`) 進行毫秒級語音轉譯，以及 **Llama 3** (`llama-3.3-70b-versatile`) 進行雙語對照翻譯。
- **微型語音分切流**：實作 HTML5 `MediaRecorder` 音訊分切上傳機制（5 秒自動切片），確保投屏字幕連續不斷。
- **自訂專用語字典安全護欄**：
  - 支援專有名詞對齊與替換（如 `Kavira` ➔ `n7 Kavira`）。
  - 實作 **「強制保留字模式 (Glossary Mode)」**：字典中右側「取代為」留空的項目，在翻譯和轉譯過程中將被強制原樣保留，不作翻譯。
  - 內置網頁端字典編輯器，支援即時新增、刪除與儲存。
- **大會演示投屏 UI**：
  - 採用暗黑科技風 Premium UI，帶有藍紫漸變效果。
  - 字體大、對比高，專為投影機與大螢幕投屏優化。
  - SVG 聲波錄音動態視覺反饋。
  - 增設 **「🧹 清除畫面」** 按鈕，便於一鍵清空字幕。
- **動態金鑰與去中心化安全**：
  - 增設網頁端「🔑 設定金鑰」彈窗，允許使用者在網頁上輸入自己的 Groq API Key，儲存於本地 `localStorage`，保障金鑰隱私。
  - 後端 API 支援 `X-Groq-API-Key` 請求 Header，每次翻譯時動態解析並實例化 Groq，優先使用前端傳入金鑰，伺服器環境變數為兜底。
- **OpenAI 與 Groq 雙引擎自適應切換**：
  - 增設網頁端「🔑 設定金鑰」彈窗中的 OpenAI API 金鑰設定，金鑰僅儲存於本地 `localStorage`，保護私隱。
  - 後端全面支援 `X-OpenAI-API-Key` 請求 Header。只要使用者輸入了 OpenAI Key，系統即會**全程切換至 OpenAI 頂級引擎**（`whisper-1` 語音轉文字 + `gpt-4o` 旗艦大語言模型翻譯），提供大會級極致翻譯精確度。
- **語言治理機制**：後端全面整合 `OpenCC` 簡轉繁轉換，保證所有輸出的中文原文與譯文皆為標準繁體中文，絕無簡體字溢出。
- **CLI 終端機工具**：新增 `cli.py` 獨立腳本，支援在 Command Line 介面下進行互動式翻譯及功能展示。

### 改進 (Improved)
- **固定底欄控制條 (Fixed-Bottom Control Bar)**：重構 CSS 佈局，將錄音按鈕與清除按鈕鎖定在螢幕最下方，防止按鈕被多行滾動字幕擠出螢幕。
- **端口衝突防範**：預設運行於 `8090` 端口，避開系統級 `omlx` 佔用的 `8000` 端口。
- **綠色解耦架構**：所有檔案路徑改為相對路徑，並整合 `python-dotenv` 配置，實現開箱即用、輕鬆部署。
- **Vercel Serverless 相容性優化**：將後端 Web 主程式、自訂字典與靜態網頁模板完全內聚於 `api/` 目錄下，解決 Vercel 雲端打包時無法存取根目錄資源及唯讀檔案系統寫入崩潰的環境限制。
- **補全上傳依賴**：於 `requirements.txt` 中補上 `python-multipart`，解決 Vercel 雲端因缺乏該依賴導致音訊上傳 API 啟動失敗的 Bug。
