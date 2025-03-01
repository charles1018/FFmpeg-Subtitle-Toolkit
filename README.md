# FFmpeg字幕工具箱 (FFmpeg Subtitle Toolkit)

FFmpeg字幕工具箱是一個使用Python和Tkinter開發的GUI應用程式，專門用於將SRT等格式的字幕檔案燒錄（硬字幕）到影片檔案中。該工具基於FFmpeg，提供了友善的使用者介面，讓您輕鬆自訂字幕樣式並處理影片。

## 功能特色

- 簡單直觀的圖形使用者介面
- 支援各種影片格式（MP4, AVI, MKV, MOV等）
- 支援主流字幕格式（SRT, ASS, SSA）
- 自訂字幕樣式（字型、顏色、背景透明度等）
- 自訂字幕位置（9個位置選項）
- 支援GPU加速編碼（NVENC）和CPU編碼
- 完整的記錄系統，方便排查問題
- 處理含有中文和特殊字元的檔案路徑

## 系統需求

- Python 3.6 或更高版本
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

### 2. 安裝Python依賴

```bash
pip install -r requirements.txt
```

## 使用方法

1. 執行程式：
   ```bash
   python ffmpeg_subtitle_toolkit.py
   ```

2. 在介面中選擇：
   - 影片檔案
   - 字幕檔案
   - 設定輸出檔案位置（如未指定，將自動產生）

3. 自訂參數：
   - 選擇編碼格式（H.264/H.265）
   - 設定編碼品質（從ultrafast到veryslow）
   - 選擇字幕字型
   - 調整背景透明度
   - 選擇字幕樣式（半透明背景或邊框加陰影）
   - 設定字幕位置
   - 調整字幕邊距

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
