# FFmpeg字幕工具箱 (FFmpeg Subtitle Toolkit)

FFmpeg字幕工具箱是一個使用Python和Tkinter開發的GUI應用程式，專門用於將SRT等格式的字幕檔案燒錄（硬字幕）到影片檔案中。該工具基於FFmpeg，提供了友善的使用者介面，讓您輕鬆自訂字幕樣式並處理影片。

## 功能特色

- 簡單直觀的圖形使用者介面
- 支援各種影片格式（MP4, AVI, MKV, MOV等）
- 支援主流字幕格式（SRT, ASS, SSA）
- 豐富的字幕樣式自訂：
  - 字幕字型選擇（支援系統已安裝的中文字型）
  - 字體大小調整（10-72）
  - 字體顏色自訂（預設色或自選）
  - 邊框樣式（無邊框、普通邊框、陰影、半透明背景）
  - 背景透明度調整（0-100%）
  - 精確位置調整（X/Y 座標微調）
  - 字幕邊距設定
- 支援 GPU 加速編碼（NVENC）並自動回退到 CPU 編碼
- 完整的記錄系統，方便排查問題
- 智慧處理含有中文和特殊字元的檔案路徑

## 系統需求

- Python 3.10 或更高版本（推薦使用 uv 管理）
- FFmpeg（需預先安裝並設置到系統環境變數）
- Windows, macOS 或 Linux 系統

## 安裝步驟

### 1. 安裝FFmpeg

在使用本工具前，請先安裝FFmpeg並確保它可以從命令列呼叫。

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
   - 從[FFmpeg官網](https://ffmpeg.org/download.html)或[gyan.dev](https://www.gyan.dev/ffmpeg/builds/)下載FFmpeg
   - 解壓縮到指定目錄
   - 將FFmpeg的bin目錄添加到系統環境變數PATH中

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
# 建立虛擬環境並安裝專案
uv venv
uv pip install -e .

# 執行應用程式（推薦方式）
uv run ffsubtool

# 或直接執行腳本
uv run python ffmpeg_subtitle_toolkit.py
```

## 使用方法

1. 執行程式：
   ```bash
   uv run ffsubtool
   ```

2. 在介面中選擇：
   - 影片檔案
   - 字幕檔案
   - 設定輸出檔案位置（如未指定，將自動產生）

3. 自訂參數：
   - **影片編碼**：
     - 編碼格式（H.264 或 H.265）
     - 編碼品質（從 ultrafast 到 veryslow）
   - **字幕樣式**：
     - 字幕字型（Arial、微軟正黑體、Noto Sans TC、思源黑體、Times New Roman，需系統已安裝對應字型）
     - 字體大小（10-72）
     - 字體顏色（預設色或自定義）
     - 邊框樣式（無邊框、普通邊框、陰影、半透明背景）
     - 背景透明度（0-100%）
   - **字幕位置**：
     - X 座標微調（-200 到 +200）
     - Y 座標微調（-200 到 +200）
     - 字幕邊距（0-100）

4. 點擊「開始處理」按鈕開始轉換

5. 等待處理完成，查看日誌了解處理詳情

## 疑難排解

- **FFmpeg未找到錯誤**：請確認FFmpeg已正確安裝並新增到系統環境變數中
- **NVENC不可用**：如果GPU不支援NVENC，程式會自動切換到CPU編碼
- **字幕路徑錯誤**：程式會自動處理含特殊字元的路徑問題
- **查看記錄**：程式會在使用者主目錄下的FFmpegGUI_Logs資料夾中儲存詳細記錄

## 常見問題

**Q: 處理大檔案時速度很慢怎麼辦？**  
A: 可以選擇更快的預設值（如 "fast" 或 "veryfast"）來加快處理速度，但會犧牲一些品質。

**Q: 支援哪些字幕格式？**  
A: 主要支援 SRT, ASS, SSA 格式的字幕檔案。

**Q: 字幕在影片中顯示不正確怎麼辦？**  
A: 可以調整字幕位置、邊距和透明度等設定。如果是字型問題，請確認系統已安裝所選字型。

## 授權

本項目採用 MIT 授權協議。

## 致謝

- 感謝 [FFmpeg](https://ffmpeg.org/) 提供強大的多媒體處理框架
- 感謝所有開源社群的貢獻者

---

如有問題或建議，歡迎提交 issue 或聯絡開發者。
