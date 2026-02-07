# FFmpeg 工具箱 (FFmpeg Toolkit)

FFmpeg 工具箱是一個使用 Python 和 Gradio 開發的網頁應用程式，提供常見的 FFmpeg 影音操作功能。透過統一的網頁介面，輕鬆完成影片轉檔、截圖、剪輯、字幕燒錄等多種任務。

## 功能特色

本工具箱提供 **7 大功能**，以分頁方式呈現：

| 分頁 | 功能 | 說明 |
|------|------|------|
| ℹ️ 媒體資訊 | 檢視媒體檔案詳細資訊 | 使用 ffprobe 讀取格式、串流、時長、位元率等 |
| 🔄 影片轉檔 | 影片格式與編碼轉換 | 支援多種格式（MP4, AVI, MKV, MOV 等），可調整編碼與 CRF 品質 |
| ✂️ 影片剪輯 | 依時間裁剪影片片段 | 支援快速複製模式與重新編碼模式 |
| 📸 影片截圖 | 單張與批次擷取影片畫面 | 指定時間點截圖或每 N 秒自動擷取，支援 PNG/JPG |
| 📐 解析度/旋轉 | 調整影片尺寸與旋轉角度 | 支援縮放與旋轉（90°/180°/270°） |
| 🔊 音訊擷取 | 從影片中提取音訊 | 支援 MP3、AAC、FLAC、WAV 格式 |
| 📝 字幕燒錄 | 將字幕檔燒錄至影片中 | 支援 SRT/ASS/SSA 格式，豐富的字幕樣式自訂 |

### 通用特性

- 簡潔直觀的網頁介面（自動開啟瀏覽器）
- 智慧型程式生命週期管理（關閉瀏覽器後自動退出，無需手動終止）
- 支援 GPU 加速編碼（NVENC）並自動回退到 CPU 編碼
- 電影級深色主題介面（毛玻璃效果、漸層動畫）
- 完整的即時日誌輸出，方便排查問題

## 系統需求

- Python 3.10 或更高版本（推薦使用 [uv](https://docs.astral.sh/uv/) 管理）
- FFmpeg / ffprobe（需預先安裝並設置到系統環境變數）
- 現代網頁瀏覽器（Chrome、Firefox、Safari、Edge 等）
- Windows, macOS 或 Linux 系統

## 安裝步驟

### 1. 安裝 FFmpeg

在使用本工具前，請先安裝 FFmpeg 並確保它可以從命令列呼叫。

**Windows:**

推薦使用以下方式安裝:

1. **使用 Chocolatey**:
   ```
   choco install ffmpeg
   ```

2. **使用 Scoop**:
   ```
   scoop install ffmpeg
   ```

3. **使用 winget**:
   ```
   winget install ffmpeg
   ```

4. **手動安裝**:
   - 從 [FFmpeg 官網](https://ffmpeg.org/download.html)或 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) 下載 FFmpeg
   - 解壓縮到指定目錄
   - 將 FFmpeg 的 bin 目錄添加到系統環境變數 PATH 中

**macOS:**
```bash
brew install ffmpeg
```

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. 安裝與執行

本專案使用 [uv](https://docs.astral.sh/uv/) 進行依賴管理。請先安裝 uv：

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安裝並執行專案：

```bash
# 同步依賴並安裝專案
uv sync

# 執行應用程式（會自動開啟瀏覽器）
uv run ffsubtool
```

## 使用方法

1. 執行程式：
   ```bash
   uv run ffsubtool
   ```
   程式會自動開啟瀏覽器並連接到 http://127.0.0.1:7860

2. 在網頁介面中選擇對應功能的分頁

3. 上傳檔案、調整參數，點擊處理按鈕即可

4. 完成後可直接關閉瀏覽器視窗，程式會自動退出

## 疑難排解

- **FFmpeg 未找到錯誤**：請確認 FFmpeg 已正確安裝並新增到系統環境變數中
- **NVENC 不可用**：如果 GPU 不支援 NVENC，程式會自動切換到 CPU 編碼
- **查看記錄**：處理日誌會即時顯示在網頁介面中

## 技術架構

專案採用模組化三層架構設計：

```
ffmpeg_toolkit/
├── core/           # 核心層：FFmpeg 執行器、編碼策略、路徑驗證
├── features/       # 功能層：每個功能一個模組（Config + Worker 模式）
├── ui/             # UI 層：Gradio 網頁介面（可替換）
└── main.py         # 進入點
```

- **Core 層**：FFmpeg 執行器（subprocess 管理、逾時保護）、編碼策略（GPU → CPU 回退）、路徑驗證
- **Features 層**：7 個獨立功能模組，各自包含設定資料類別與處理類別
- **UI 層**：7 分頁 Gradio 網頁介面，每個分頁對應一項功能

所有核心功能皆有完整的單元測試覆蓋。

## 開發

```bash
# 安裝開發依賴
uv sync --group dev

# 執行測試
uv run pytest

# 程式碼檢查與格式化
uv run ruff check ffmpeg_toolkit/
uv run ruff format ffmpeg_toolkit/
```

## 授權

本項目採用 MIT 授權協議。

## 致謝

- [FFmpeg](https://ffmpeg.org/) — 強大的多媒體處理框架
- [Gradio](https://gradio.app/) — 優秀的網頁介面框架

---

如有問題或建議，歡迎提交 issue 或聯絡開發者。
